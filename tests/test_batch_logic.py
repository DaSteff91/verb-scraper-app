"""
Unit tests for the Asynchronous Batch Orchestration.

This module verifies that the VerbManager correctly updates BatchJob records
and persists multiple verbs within a single batch execution context.
"""

from typing import TYPE_CHECKING, Dict, List

import pytest
import requests_mock
from flask import Flask

from src.extensions import db
from src.models.verb import BatchJob, Verb
from src.services.verb_manager import VerbManager

if TYPE_CHECKING:
    from collections.abc import Callable


def test_process_batch_lifecycle(
    app: Flask, requests_mock: requests_mock.Mocker, sample_html: "Callable[[str], str]"
) -> None:
    """
    Verify the full lifecycle of a BatchJob record during processing.

    This test simulates a batch of two verbs and ensures that the VerbManager:
    1. Transition the job status to 'completed'.
    2. Accurately records success counts.
    3. Persists all requested verbs to the database.

    Args:
        app: The Flask application fixture with a fresh database.
        requests_mock: The fixture used to intercept outgoing HTTP calls.
        sample_html: A helper fixture to load mock HTML files.
    """
    manager = VerbManager()

    # 1. Setup: Define the tasks and mock the external website responses
    verb_tasks: List[Dict[str, str]] = [
        {"verb": "falar", "mode": "Indicativo", "tense": "Presente"},
        {"verb": "comer", "mode": "Indicativo", "tense": "Presente"},
    ]

    # Mocking different responses (using falar.html for both for simplicity)
    falar_content: str = sample_html("falar.html")
    requests_mock.get(f"{manager.scraper.base_url}falar/", text=falar_content)
    requests_mock.get(f"{manager.scraper.base_url}comer/", text=falar_content)

    # 2. Create the initial BatchJob record
    with app.app_context():
        new_job = BatchJob(total_tasks=len(verb_tasks), status="pending")
        db.session.add(new_job)
        db.session.commit()
        job_id: str = str(new_job.id)

    # 3. Execution: Run the batch processing logic
    # We call process_batch directly. Even though it uses a ThreadPoolExecutor
    # internally, the test waits for the executor to complete its map.
    summary: Dict[str, int] = manager.process_batch(verb_tasks, job_id=job_id)

    # 4. Assertions: Verify data and job status
    with app.app_context():
        # A. Check Job record metadata
        job_record = db.session.get(BatchJob, job_id)
        assert job_record is not None
        assert job_record.status == "completed"
        assert job_record.success_count == 2
        assert job_record.failed_count == 0
        assert summary["success"] == 2

        # B. Check if Verbs were actually saved to the 5NF schema
        verb_falar = Verb.query.filter_by(infinitive="falar").first()
        verb_comer = Verb.query.filter_by(infinitive="comer").first()

        assert verb_falar is not None, "Verb 'falar' failed to persist in batch."
        assert verb_comer is not None, "Verb 'comer' failed to persist in batch."

        # Verify the relationship (6 conjugations per verb)
        assert len(verb_falar.conjugations) == 6
        assert len(verb_comer.conjugations) == 6
