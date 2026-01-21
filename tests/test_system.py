"""
Tests for System Maintenance, Validation, and Health Monitoring.
"""

from typing import Dict, List, Any
from flask.testing import FlaskClient
from flask import Flask
from datetime import datetime, timedelta, UTC

from src.extensions import db
from src.models.verb import BatchJob
from src.services.validator import InputValidator


def test_batch_validation_logic() -> None:
    """
    Verify that the batch validator identifies malformed tasks.
    """
    valid_tasks = [{"verb": "falar", "mode": "Indicativo", "tense": "Presente"}]
    invalid_tasks = [
        {"verb": "falar; DROP TABLE", "mode": "Indicativo", "tense": "Presente"}
    ]

    assert InputValidator.validate_batch(valid_tasks) is True
    assert InputValidator.validate_batch(invalid_tasks) is False
    assert InputValidator.validate_batch([]) is False


def test_job_janitor_cleanup(app: Flask) -> None:
    """
    Verify that old BatchJob records are purged correctly.
    """
    with app.app_context():
        # 1. Create one fresh job and one old job (25 hours ago)
        fresh_job = BatchJob(status="completed")
        old_job = BatchJob(status="completed")

        db.session.add_all([fresh_job, old_job])
        db.session.commit()

        # Manually backdate the old job
        old_job.created_at = datetime.now(UTC) - timedelta(hours=25)
        db.session.commit()

        # 2. Run the cleanup
        deleted_count = BatchJob.cleanup_old_jobs(hours=24)

        # 3. Assertions
        assert deleted_count == 1
        assert db.session.get(BatchJob, fresh_job.id) is not None
        assert db.session.get(BatchJob, old_job.id) is None


def test_api_health_check_success(client: FlaskClient, app: Flask) -> None:
    """
    Verify the health check endpoint returns 200 and a full report.
    """
    api_key: str = app.config["API_KEY"]
    headers: Dict[str, str] = {"X-API-KEY": api_key}

    response = client.get("/api/v1/health", headers=headers)
    assert response.status_code == 200

    data = response.get_json()
    assert data["status"] == "healthy"
    assert data["checks"]["database"] == "ok"
    assert data["checks"]["storage"] == "ok"
    assert data["checks"]["readiness"] == "ok"
