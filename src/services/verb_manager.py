"""
Verb Manager Service.

This module orchestrates the scraping and persistence of verb data
into the database using a 5th Normal Form approach, supporting both
single-task and concurrent batch processing.
"""

import logging
import random
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from typing import Dict, List, Optional

from flask import current_app

from src.extensions import db
from src.models.verb import BatchJob, Conjugation, Mode, Person, Tense, Verb
from src.services.scraper import ConjugacaoScraper
from src.services.backup_scraper import CooljugatorScraper

logger = logging.getLogger(__name__)

# Serialize heavy scrape batches so overlapping UI/API jobs cannot stack
# ThreadPoolExecutors on top of the limited gunicorn gthread pool.
_BATCH_EXECUTION_LOCK = threading.BoundedSemaphore(1)
_BATCH_POOL_WORKERS = 2


class VerbManager:
    """
    Manages the lifecycle of verb data (Scrape -> Process -> Save).
    """

    def __init__(self) -> None:
        """Initialize the service with its scraper and person mappings."""
        self.primary_scraper: ConjugacaoScraper = ConjugacaoScraper()
        self.backup_scraper: CooljugatorScraper = CooljugatorScraper()
        self.person_names: List[str] = [
            "eu",
            "tu",
            "ele/ela/você",
            "nós",
            "vós",
            "eles/elas/vocês",
        ]

    def get_or_create_verb_data(
        self, verb_infinitive: str, mode_name: str, tense_name: str
    ) -> bool:
        """
        Coordinates scraping from multiple sources and saves to the database.

        Checks the DB first. If the specific verb/mode/tense
        combination already exists, it skips the network call entirely.

        Args:
            verb_infinitive: The infinitive form of the verb.
            mode_name: The grammatical mode to scrape.
            tense_name: The grammatical tense to scrape.

        Returns:
            bool: True if data is in DB (either existed or was scraped), False otherwise.
        """
        logger.debug(
            "Starting persistence check for %s (%s %s)",
            verb_infinitive,
            mode_name,
            tense_name,
        )

        # 1. DB CHECK (The Short-Circuit)
        existing_data = (
            db.session.query(Conjugation)
            .join(Verb)
            .join(Tense)
            .join(Mode)
            .filter(
                Verb.infinitive == verb_infinitive,
                Mode.name == mode_name,
                Tense.name == tense_name,
            )
            .first()
        )

        if existing_data:
            logger.info(
                "Data already exists for %s (%s %s). Skipping scrape.",
                verb_infinitive,
                mode_name,
                tense_name,
            )
            return True

        # 2. Attempt Primary Source
        forms: Optional[List[str]] = self.primary_scraper.get_conjugations(
            verb_infinitive, mode_name, tense_name
        )

        # 3. Failover to Backup Source
        if not forms:
            logger.warning(
                "Primary source failed for %s. Attempting backup source...",
                verb_infinitive,
            )
            forms = self.backup_scraper.get_conjugations(
                verb_infinitive, mode_name, tense_name
            )

        if not forms:
            logger.error(
                "All sources failed for %s (%s %s)",
                verb_infinitive,
                mode_name,
                tense_name,
            )
            return False

        # 4. Persistence Logic
        try:
            # Get or Create Verb
            verb = Verb.query.filter_by(infinitive=verb_infinitive).first()
            if not verb:
                try:
                    verb = Verb(infinitive=verb_infinitive)
                    db.session.add(verb)
                    db.session.flush()
                    logger.debug("Created new verb entry: %s", verb_infinitive)
                except Exception:
                    db.session.rollback()
                    verb = Verb.query.filter_by(infinitive=verb_infinitive).first()
                    logger.debug(
                        "Verb %s was created by another thread.", verb_infinitive
                    )

            # Get or Create Mode
            mode = Mode.query.filter_by(name=mode_name).first()
            if not mode:
                mode = Mode(name=mode_name)
                db.session.add(mode)
                db.session.flush()

            # Get or Create Tense
            tense = Tense.query.filter_by(name=tense_name, mode=mode).first()
            if not tense:
                tense = Tense(name=tense_name, mode=mode)
                db.session.add(tense)
            db.session.flush()

            # Handle person mapping and offsets
            offset: int = 0
            if len(forms) == 5 and mode_name == "Imperativo":
                offset = 1

            for i, form_value in enumerate(forms):
                p_index: int = i + offset
                if p_index >= len(self.person_names):
                    break

                p_name: str = self.person_names[p_index]
                person = Person.query.filter_by(name=p_name).first()
                if not person:
                    person = Person(name=p_name, sort_order=p_index)
                    db.session.add(person)
                    db.session.flush()

                # Re-check specifically for this person (extra safety for threading)
                exists = Conjugation.query.filter_by(
                    verb=verb, tense=tense, person=person
                ).first()

                if not exists:
                    conj = Conjugation(
                        value=form_value, verb=verb, tense=tense, person=person
                    )
                    db.session.add(conj)

            db.session.commit()
            logger.info(
                "Successfully persisted %s (%s %s)",
                verb_infinitive,
                mode_name,
                tense_name,
            )
            return True

        except Exception as e:
            db.session.rollback()
            logger.error("Database error while saving %s: %s", verb_infinitive, e)
            return False

    def process_batch(
        self, tasks: List[Dict[str, str]], job_id: Optional[str] = None
    ) -> Dict[str, int]:
        """
        Orchestrates a batch of scraping tasks using a thread pool.

        Args:
            tasks: A list of dictionaries containing 'verb', 'mode', and 'tense'.
            job_id: Optional ID of a BatchJob record to update during execution.

        Returns:
            Dict[str, int]: A summary of the batch execution (total, success, failed).
        """
        results = {"total": len(tasks), "success": 0, "failed": 0}
        app_instance = current_app._get_current_object()  # type: ignore

        # --- Job Status Update: PROCESSING ---
        if job_id:
            with app_instance.app_context():
                job = db.session.get(BatchJob, job_id)
                if job:
                    job.status = "processing"
                    db.session.commit()
                    logger.info("Job [%s] status updated to PROCESSING", job_id)

        def threaded_task(task: Dict[str, str]) -> bool:
            """Internal worker to handle a single scrape within an app context."""
            # Give the website some breathing room (Good Citizen Jitter)
            time.sleep(random.uniform(0.3, 1.0))

            with app_instance.app_context():
                return self.get_or_create_verb_data(
                    task["verb"], task["mode"], task["tense"]
                )

        logger.info("Starting batch execution for %d tasks...", len(tasks))

        acquired = _BATCH_EXECUTION_LOCK.acquire(blocking=False)
        if not acquired:
            logger.info(
                "Batch execution waiting for in-flight scrape work to finish (%d tasks).",
                len(tasks),
            )
            _BATCH_EXECUTION_LOCK.acquire()
            logger.info("Batch execution lock acquired; starting %d tasks.", len(tasks))

        try:
            with ThreadPoolExecutor(max_workers=_BATCH_POOL_WORKERS) as executor:
                outcomes = list(executor.map(threaded_task, tasks))
        finally:
            _BATCH_EXECUTION_LOCK.release()

        results["success"] = outcomes.count(True)
        results["failed"] = outcomes.count(False)

        # --- Job Status Update: COMPLETED ---
        if job_id:
            with app_instance.app_context():
                job = db.session.get(BatchJob, job_id)
                if job:
                    job.status = "completed"
                    job.success_count = results["success"]
                    job.failed_count = results["failed"]
                    job.completed_at = datetime.now(UTC)
                    db.session.commit()
                    logger.info(
                        "Job [%s] completed. Success: %d, Failed: %d",
                        job_id,
                        results["success"],
                        results["failed"],
                    )

        return results

    def seed_default_data(self) -> None:
        """
        Seeds the database with a 'Gold Standard' verb (comer) if it
        doesn't already exist. Used for system health checks and testing.
        """
        verb_inf = "comer"
        # Check if already seeded to avoid redundant logic
        if Verb.query.filter_by(infinitive=verb_inf).first():
            logger.debug("Database already seeded with '%s'.", verb_inf)
            return

        logger.info("Seeding default data: %s", verb_inf)
        try:
            # 1. Create Core Entities
            verb = Verb(infinitive=verb_inf)
            db.session.add(verb)

            # Handle Mode
            mode = Mode.query.filter_by(name="Indicativo").first()
            if not mode:
                mode = Mode(name="Indicativo")
                db.session.add(mode)

            # Flush so mode.id is generated
            db.session.flush()

            # Handle Tense (Now mode.id is guaranteed to exist)
            tense = Tense.query.filter_by(name="Presente", mode_id=mode.id).first()
            if not tense:
                tense = Tense(name="Presente", mode=mode)
                db.session.add(tense)

            db.session.flush()

            # 2. Add 'Gold Standard' Conjugations
            seed_data = [
                ("eu", "eu como"),
                ("tu", "tu comes"),
                ("ele/ela/você", "ele come"),
                ("nós", "nós comemos"),
                ("vós", "vós comeis"),
                ("eles/elas/vocês", "eles comem"),
            ]

            for p_name, val in seed_data:
                person = Person.query.filter_by(name=p_name).first()
                if not person:
                    person = Person(name=p_name, sort_order=0)
                    db.session.add(person)
                    db.session.flush()

                conj = Conjugation(verb=verb, tense=tense, person=person, value=val)
                db.session.add(conj)

            db.session.commit()
            logger.info("Default data seeded successfully.")
        except Exception as e:
            db.session.rollback()
            logger.error("Failed to seed default data: %s", e)
