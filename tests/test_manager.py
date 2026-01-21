"""
Integration tests for the VerbManager and Database Models.

This module verifies that the orchestration between scraping and 5NF persistence
works as expected.
"""

from typing import Callable
import requests_mock
from flask import Flask

from src.services.verb_manager import VerbManager
from src.models.verb import Verb, Mode, Tense, Person, Conjugation


def test_get_or_create_verb_data_success(
    app: Flask, requests_mock: requests_mock.Mocker, sample_html: Callable[[str], str]
) -> None:
    """
    Test that VerbManager correctly populates all 5 tables from a single scrape.
    """
    # 1. Setup Mock
    verb_infinitive = "falar"
    mode_name = "Indicativo"
    tense_name = "Presente"

    manager = VerbManager()
    mock_content = sample_html("falar.html")
    requests_mock.get(
        f"{manager.scraper.base_url}{verb_infinitive}/", text=mock_content
    )

    # 2. Execute
    success = manager.get_or_create_verb_data(verb_infinitive, mode_name, tense_name)

    # 3. Assert Overall Success
    assert success is True

    # 4. Assert 5NF Integrity
    # Use the app context (provided by the fixture) to query the DB
    verb = Verb.query.filter_by(infinitive=verb_infinitive).first()  # type: ignore
    assert verb is not None
    assert verb.infinitive == "falar"

    # Check that Mode and Tense were created
    mode = Mode.query.filter_by(name=mode_name).first()  # type: ignore
    assert mode is not None

    tense = Tense.query.filter_by(name=tense_name, mode=mode).first()  # type: ignore
    assert tense is not None

    # Check that all 6 persons exist in the DB
    persons = Person.query.all()  # type: ignore
    assert len(persons) == 6

    # Verify relationships: 6 conjugations should exist for this verb/tense
    assert len(verb.conjugations) == 6
    assert verb.conjugations[0].value == "eu falo"
    assert verb.conjugations[0].person.name == "eu"


def test_no_duplicate_entities_on_second_scrape(
    app: Flask, requests_mock: requests_mock.Mocker, sample_html: Callable[[str], str]
) -> None:
    """
    Test that scraping a second verb reuses existing Mode, Tense, and Person records.
    (Ensuring 5NF prevents bloat).
    """
    # Setup
    manager = VerbManager()
    falar_html = sample_html("falar.html")
    ir_html = sample_html("ir.html")

    # 1. Scrape 'falar' first
    requests_mock.get(f"{manager.scraper.base_url}falar/", text=falar_html)
    manager.get_or_create_verb_data("falar", "Indicativo", "Presente")

    # 2. Scrape 'ir' (same mode/tense)
    requests_mock.get(f"{manager.scraper.base_url}ir/", text=ir_html)
    manager.get_or_create_verb_data("ir", "Indicativo", "Presente")

    # 3. Assertions
    # We should have 2 verbs but still only 1 Mode, 1 Tense, and 6 Persons as well as one additional (comer) from the DB seeding
    assert Verb.query.count() == 3  # type: ignore
    assert Mode.query.count() == 1  # type: ignore
    assert Tense.query.count() == 1  # type: ignore
    assert Person.query.count() == 6  # type: ignore

    # Total conjugations should be 12 (6 per verb)
    assert Conjugation.query.count() == 12  # type: ignore
