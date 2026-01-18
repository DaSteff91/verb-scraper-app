"""
Verb Manager Service.

This module orchestrates the scraping and persistence of verb data
into the database using a 5th Normal Form approach.
"""

import logging
from typing import List, Optional

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

            # Ensure IDs are generated before proceeding to children
            db.session.flush()

            # 5. Determine if we need an offset (e.g., Imperativo starts at 'tu')
            offset: int = 0
            if len(forms) == 5 and mode_name == "Imperativo":
                offset = 1

            # 6. Process and map forms to Persons
            for i, form_value in enumerate(forms):
                p_index: int = i + offset

                # Safety break if scraper returns more than 6 persons
                if p_index >= len(self.person_names):
                    break

                p_name: str = self.person_names[p_index]

                # Get or Create Person
                person = Person.query.filter_by(name=p_name).first()  # type: ignore
                if not person:
                    person = Person(name=p_name, sort_order=p_index)
                    db.session.add(person)
                    db.session.flush()

                # Avoid duplicates: check if this specific conjugation exists
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
