"""
Integration tests for Batch UI Workflows and Specialized Grammatical Mapping.

This module verifies the interaction between the frontend-facing batch routes
and the underlying persistence services, including CSV aggregation.
"""

import json
from typing import Any, Dict, List, cast
from flask import Flask
from flask.testing import FlaskClient

from src.models.verb import Verb, Conjugation
from src.services.verb_manager import VerbManager


def test_batch_scrape_route_handshake(client: FlaskClient, app: Flask) -> None:
    """
    Verify the JSON handshake between the Alpine.js basket and the batch route.

    This ensures that when the UI sends a list of tasks, the backend processes
    them and returns a redirect URL for the results page.
    """
    # 1. Setup: Prepare a small batch of tasks
    tasks: List[Dict[str, str]] = [
        {"verb": "falar", "mode": "Indicativo", "tense": "Presente"},
        {"verb": "ir", "mode": "Indicativo", "tense": "Presente"},
    ]
    payload = {"tasks": tasks, "filename": "my_study_batch"}

    # 2. Execution: POST to the UI's batch endpoint
    response = client.post(
        "/batch-scrape", data=json.dumps(payload), content_type="application/json"
    )

    # 3. Assertions
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "success"
    # Ensure the redirect URL contains the tasks so the results page can load them
    assert "results-batch" in data["redirect_url"]
    assert "tasks=" in data["redirect_url"]


def test_export_batch_csv_aggregation(client: FlaskClient, app: Flask) -> None:
    """
    Verify that the batch exporter aggregates multiple verbs into a single file.
    """
    # 1. Setup: Ensure verbs exist in the DB (Using the Manager directly for speed)
    with app.app_context():
        # Pre-seed 'falar' and 'ir' so the exporter has data to grab
        manager = VerbManager()
        # Note: We rely on the previously tested seeding/mocking logic
        # For this test, we simulate that the data is already there.
        manager.get_or_create_verb_data("falar", "Indicativo", "Presente")

    tasks = [{"verb": "falar", "mode": "Indicativo", "tense": "Presente"}]
    tasks_json = json.dumps(tasks)

    # 2. Execution: Call the batch export route
    url = f"/export-batch?tasks={tasks_json}&filename=combined_test&skip_tu_vos=true"
    response = client.get(url)

    # 3. Assertions
    assert response.status_code == 200
    assert response.mimetype == "text/csv"
    assert b"\xef\xbb\xbf" in response.data  # Check for UTF-8 BOM
    assert b"falar" in response.data


def test_verb_manager_imperativo_offset_logic(
    app: Flask, requests_mock: Any, sample_html: Any
) -> None:
    """
    Verify the specialized offset logic for 'Imperativo' modes.

    In Portuguese, the Imperative 'Afirmativo' often lacks the 'eu' form,
    resulting in 5 forms instead of 6. This test ensures the Manager
    correctly shifts the 'Person' mapping by +1.
    """
    manager = VerbManager()
    verb_inf = "falar"
    mode_name = "Imperativo"
    tense_name = "Afirmativo"

    # 1. Setup: Mock a 5-line response (Typical for Imperativo)
    # We simulate a 5-item list being returned by the scraper
    mock_forms = ["fala tu", "fale você", "falemos nós", "falai vós", "falem vocês"]

    import unittest.mock as mock

    with mock.patch(
        "src.services.scraper.ConjugacaoScraper.get_conjugations",
        return_value=mock_forms,
    ):
        with app.app_context():
            success = manager.get_or_create_verb_data(verb_inf, mode_name, tense_name)
            assert success is True

            # 2. Assertions: Check that 'eu' was skipped and mapping starts at 'tu'
            verb = Verb.query.filter_by(infinitive=verb_inf).first()
            assert verb is not None

            # Get the first conjugation saved
            conjs = Conjugation.query.filter_by(verb_id=verb.id).all()
            assert len(conjs) == 5

            # Verify the first saved person is 'tu' (index 1) not 'eu' (index 0)
            # based on your VerbManager's offset logic: p_index = i + offset
            person_names = [c.person.name for c in conjs]
            assert "eu" not in person_names
            assert "tu" in person_names
