"""
Verb Manager Service.

This module orchestrates the scraping and persistence of verb data
into the database using a 5th Normal Form approach, supporting both
single-task and concurrent batch processing.
"""

import logging
import random
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from typing import Dict, List, Optional

from flask import current_app

from src.extensions import db
from src.models.verb import BatchJob, Conjugation, Mode, Person, Tense, Verb
from src.services.scraper import ConjugacaoScraper

# Initialize logger
logger = logging.getLogger(__name__)


class VerbManager:
    """
    Manages the lifecycle of verb data (Scrape -> Process -> Save).
    """

    def __init__(self) -> None:
        """Initialize the service with its scraper and person mappings."""
        self.scraper: ConjugacaoScraper = ConjugacaoScraper()
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
        Coordinates scraping a verb and saving it to the 5NF database.

        Args:
            verb_infinitive: The infinitive form of the verb.
            mode_name: The grammatical mode to scrape.
            tense_name: The grammatical tense to scrape.

        Returns:
            bool: True if persistence was successful, False otherwise.
        """
        logger.debug(
            "Starting persistence for %s (%s %s)",
            verb_infinitive,
            mode_name,
            tense_name,
        )

        # 1. Scrape the raw data
        forms: Optional[List[str]] = self.scraper.get_conjugations(
            verb_infinitive, mode_name, tense_name
        )

        if not forms:
            logger.error(
                "No data found for %s (%s %s)", verb_infinitive, mode_name, tense_name
            )
            return False

        try:
            # 2. Get or Create Verb (with extra safety for multi-threading)
            verb = Verb.query.filter_by(infinitive=verb_infinitive).first()  # type: ignore
            if not verb:
                try:
                    verb = Verb(infinitive=verb_infinitive)
                    db.session.add(verb)
                    db.session.flush()  # Try to push to DB immediately
                    logger.debug("Created new verb entry: %s", verb_infinitive)
                except Exception:
                    # If another thread beat us to it, rollback the flush and fetch it
                    db.session.rollback()
                    verb = Verb.query.filter_by(infinitive=verb_infinitive).first()
                    logger.debug(
                        "Verb %s was created by another thread.", verb_infinitive
                    )

            # 3. Get or Create Mode
            mode = Mode.query.filter_by(name=mode_name).first()  # type: ignore
            if not mode:
                mode = Mode(name=mode_name)
                db.session.add(mode)
                db.session.flush()

            # 4. Get or Create Tense (linked to Mode)
            tense = Tense.query.filter_by(name=tense_name, mode=mode).first()  # type: ignore
            if not tense:
                tense = Tense(name=tense_name, mode=mode)
                db.session.add(tense)

            db.session.flush()

            # 5. Handle person mapping and offsets
            offset: int = 0
            if len(forms) == 5 and mode_name == "Imperativo":
                offset = 1

            for i, form_value in enumerate(forms):
                p_index: int = i + offset
                if p_index >= len(self.person_names):
                    break

                p_name: str = self.person_names[p_index]
                person = Person.query.filter_by(name=p_name).first()  # type: ignore
                if not person:
                    person = Person(name=p_name, sort_order=p_index)
                    db.session.add(person)
                    db.session.flush()

                exists = Conjugation.query.filter_by(  # type: ignore
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
                job = BatchJob.query.get(job_id)
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

        # We use max_workers=3 to keep it fast but respectful to the source site
        with ThreadPoolExecutor(max_workers=3) as executor:
            outcomes = list(executor.map(threaded_task, tasks))

        results["success"] = outcomes.count(True)
        results["failed"] = outcomes.count(False)

        # --- Job Status Update: COMPLETED ---
        if job_id:
            with app_instance.app_context():
                job = BatchJob.query.get(job_id)
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
