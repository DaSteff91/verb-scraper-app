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
from typing import Dict, List, Optional

from flask import Flask, current_app

from src.extensions import db
from src.models.verb import Conjugation, Mode, Person, Tense, Verb
from src.services.scraper import ConjugacaoScraper

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
            # 2. Get or Create Verb
            verb = Verb.query.filter_by(infinitive=verb_infinitive).first()  # type: ignore
            if not verb:
                verb = Verb(infinitive=verb_infinitive)
                db.session.add(verb)

            # 3. Get or Create Mode
            mode = Mode.query.filter_by(name=mode_name).first()  # type: ignore
            if not mode:
                mode = Mode(name=mode_name)
                db.session.add(mode)

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
            return True

        except Exception as e:
            db.session.rollback()
            logger.error("Database error while saving %s: %s", verb_infinitive, e)
            return False

    def process_batch(self, tasks: List[Dict[str, str]]) -> Dict[str, int]:
        """
        Orchestrates a batch of scraping tasks using a thread pool.

        Args:
            tasks: A list of dictionaries containing 'verb', 'mode', and 'tense'.

        Returns:
            Dict[str, int]: A summary of the batch execution (total, success, failed).
        """
        results = {"total": len(tasks), "success": 0, "failed": 0}

        # We grab the actual app object to pass to threads
        app_instance = current_app._get_current_object()  # type: ignore

        def threaded_task(task: Dict[str, str]) -> bool:
            """Internal worker to handle a single scrape within an app context."""
            # Give the website some breathing room (Good Citizen Jitter)
            time.sleep(random.uniform(0.3, 1.0))

            with app_instance.app_context():
                return self.get_or_create_verb_data(
                    task["verb"], task["mode"], task["tense"]
                )

        logger.info("Starting batch process for %d tasks...", len(tasks))

        # We use max_workers=3 to keep it fast but respectful to the source site
        with ThreadPoolExecutor(max_workers=3) as executor:
            outcomes = list(executor.map(threaded_task, tasks))

        results["success"] = outcomes.count(True)
        results["failed"] = outcomes.count(False)

        logger.info(
            "Batch finished. Success: %d, Failed: %d",
            results["success"],
            results["failed"],
        )
        return results
