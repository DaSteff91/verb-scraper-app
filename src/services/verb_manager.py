"""
Verb Manager Service.

This module orchestrates the scraping and persistence of verb data
into the database.
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
        self.scraper = ConjugacaoScraper()
        # The persons we keep based on your requirement (excluding tu/vós)
        self.person_names = ["eu", "ele/ela", "nós", "eles/elas"]

    def get_or_create_verb_data(
        self, verb_infinitive: str, mode_name: str, tense_name: str
    ) -> bool:
        """
        Coordinates scraping a verb and saving it to the 5NF database.

        Returns:
            bool: True if successful, False otherwise.
        """
        # 1. Scrape the data
        forms = self.scraper.get_conjugations(verb_infinitive, mode_name, tense_name)

        if not forms:
            logger.error(
                "No data found for %s (%s %s)", verb_infinitive, mode_name, tense_name
            )
            return False

        try:
            # 2. Get or Create Verb
            verb = Verb.query.filter_by(infinitive=verb_infinitive).first()
            if not verb:
                verb = Verb(infinitive=verb_infinitive)
                db.session.add(verb)

            # 3. Get or Create Mode
            mode = Mode.query.filter_by(name=mode_name).first()
            if not mode:
                mode = Mode(name=mode_name)
                db.session.add(mode)

            # 4. Get or Create Tense (linked to Mode)
            tense = Tense.query.filter_by(name=tense_name, mode=mode).first()
            if not tense:
                tense = Tense(name=tense_name, mode=mode)
                db.session.add(tense)

            # 5. Process the 4 forms and map to Persons
            db.session.flush()  # Ensures IDs are generated for verb/tense

            for i, form_value in enumerate(forms):
                # Get or Create Person
                p_name = self.person_names[i]
                person = Person.query.filter_by(name=p_name).first()
                if not person:
                    person = Person(name=p_name, sort_order=i)
                    db.session.add(person)
                    db.session.flush()

                # Check if this specific conjugation already exists to avoid duplicates
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
