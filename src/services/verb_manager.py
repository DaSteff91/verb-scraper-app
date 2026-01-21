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
        """
        logger.debug(
            "Starting persistence for %s (%s %s)",
            verb_infinitive,
            mode_name,
            tense_name,
        )

        forms: Optional[List[str]] = self.scraper.get_conjugations(
            verb_infinitive, mode_name, tense_name
        )

        if not forms:
            logger.error(
                "No data found for %s (%s %s)", verb_infinitive, mode_name, tense_name
            )
            return False

        try:
            verb = Verb.query.filter_by(infinitive=verb_infinitive).first()
            if not verb:
                try:
                    verb = Verb(infinitive=verb_infinitive)
                    db.session.add(verb)
                    db.session.flush()
                except Exception:
                    db.session.rollback()
                    verb = Verb.query.filter_by(infinitive=verb_infinitive).first()

            mode = Mode.query.filter_by(name=mode_name).first()
            if not mode:
                mode = Mode(name=mode_name)
                db.session.add(mode)
                db.session.flush()

            tense = Tense.query.filter_by(name=tense_name, mode_id=mode.id).first()
            if not tense:
                tense = Tense(name=tense_name, mode=mode)
                db.session.add(tense)
                db.session.flush()

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

                exists = Conjugation.query.filter_by(
                    verb_id=verb.id, tense_id=tense.id, person_id=person.id
                ).first()

                if not exists:
                    conj = Conjugation(
                        value=form_value, verb=verb, tense=tense, person=person
                    )
                    db.session.add(conj)

            db.session.commit()
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
        """
        results = {"total": len(tasks), "success": 0, "failed": 0}
        app_instance = current_app._get_current_object()

        if job_id:
            with app_instance.app_context():
                job = db.session.get(BatchJob, job_id)
                if job:
                    job.status = "processing"
                    db.session.commit()

        def threaded_task(task: Dict[str, str]) -> bool:
            time.sleep(random.uniform(0.1, 0.5))
            with app_instance.app_context():
                return self.get_or_create_verb_data(
                    task["verb"], task["mode"], task["tense"]
                )

        with ThreadPoolExecutor(max_workers=3) as executor:
            outcomes = list(executor.map(threaded_task, tasks))

        results["success"] = outcomes.count(True)
        results["failed"] = outcomes.count(False)

        if job_id:
            with app_instance.app_context():
                job = db.session.get(BatchJob, job_id)
                if job:
                    job.status = "completed"
                    job.success_count = results["success"]
                    job.failed_count = results["failed"]
                    job.completed_at = datetime.now(UTC)
                    db.session.commit()

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

            mode = Mode.query.filter_by(name="Indicativo").first()
            if not mode:
                mode = Mode(name="Indicativo")
                db.session.add(mode)
                # CRITICAL: Flush so mode.id is available for the next step
                db.session.flush()

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
