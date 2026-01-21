"""
Functional tests for the Flask Routes (Controllers).

This module simulates user interaction with the web interface to verify
routing and template rendering.
"""

import time
from flask.testing import FlaskClient
from typing import Dict, Any
import requests_mock
from src.models.verb import BatchJob
from src.extensions import db


def test_index_route_get(client: FlaskClient) -> None:
    """Verify the home page loads correctly."""
    response = client.get("/")
    assert response.status_code == 200
    assert b"Portuguese Infinitive" in response.data


def test_scrape_form_submission_success(
    client: FlaskClient, requests_mock: requests_mock.Mocker, sample_html
) -> None:
    """Verify that submitting the form redirects to the results page."""
    # Mock the website response
    mock_content = sample_html("falar.html")
    requests_mock.get("https://www.conjugacao.com.br/verbo-falar/", text=mock_content)

    # Simulate form POST
    response = client.post(
        "/",
        data={"verb": "falar", "mode": "Indicativo", "tense": "Presente"},
        follow_redirects=True,
    )

    # Check that we landed on the results page
    assert response.status_code == 200
    assert b"Conjugation Results" in response.data
    assert b"falar" in response.data
    assert b"eu falo" in response.data


def test_export_csv_route_success(
    client: FlaskClient, requests_mock: requests_mock.Mocker, sample_html
) -> None:
    """
    Verify the /export route returns a valid downloadable CSV.
    """
    # 1. Scrape 'ir' first so it exists in the in-memory DB
    mock_content = sample_html("ir.html")
    requests_mock.get("https://www.conjugacao.com.br/verbo-ir/", text=mock_content)
    client.post("/", data={"verb": "ir", "mode": "Indicativo", "tense": "Presente"})

    # 2. Call the export route
    response = client.get("/export/ir?mode=Indicativo&tense=Presente")

    # 3. Assertions
    assert response.status_code == 200
    assert response.mimetype == "text/csv"
    # Check headers for attachment flag and filename
    content_disposition = response.headers.get("Content-Disposition", "")
    assert "attachment" in content_disposition
    assert "ir_indicativo_presente.csv" in content_disposition

    # 4. Check binary content for UTF-8-SIG BOM ( \xef\xbb\xbf )
    assert response.data.startswith(b"\xef\xbb\xbf")


def test_export_csv_route_no_data(client: FlaskClient) -> None:
    """
    Verify that exporting a non-existent verb returns a 404.
    """
    # Attempt to export 'comer' before scraping it.
    # The route uses first_or_404(), so we expect a 404.
    response = client.get("/export/nonexistentverb?mode=Indicativo&tense=Presente")
    assert response.status_code == 404


def test_scrape_form_failure_handling(
    client: FlaskClient, requests_mock: requests_mock.Mocker
) -> None:
    """
    Verify the UI correctly displays an error when the scraper fails.
    """
    # Mock a website failure
    requests_mock.get("https://www.conjugacao.com.br/verbo-badverb/", status_code=404)

    # Submit the form
    response = client.post(
        "/",
        data={"verb": "badverb", "mode": "Indicativo", "tense": "Presente"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    # FIX: We look for the partial string to avoid HTML entity escaping issues (&#39;)
    assert b"Could not find the verb" in response.data
    assert b"badverb" in response.data


def test_results_page_404(client: FlaskClient) -> None:
    """Verify that looking for a non-existent verb returns 404."""
    response = client.get("/results/nonexistentverb")
    assert response.status_code == 404


def test_scrape_form_validation_error_feedback(client: FlaskClient) -> None:
    """
    Verify that invalid input shows a red error message to the user.
    """
    # 1. Simulate a malicious POST request
    response = client.post(
        "/",
        data={
            "verb": "bad_verb; DROP TABLE",
            "mode": "Indicativo",
            "tense": "Presente",
        },
        follow_redirects=True,
    )

    # 2. Check that we didn't redirect to results
    assert response.status_code == 200

    # 3. Check for the specific Flash Message in the HTML
    assert b"Invalid verb format" in response.data

    # 4. Verify it has the Bootstrap 'alert-dark' class
    assert b"alert-dark" in response.data


def test_api_batch_full_lifecycle(
    client: FlaskClient, app: Any, requests_mock: Any, sample_html: Any
) -> None:
    """
    Verify the complete asynchronous lifecycle: Trigger -> Poll -> Complete.

    This test ensures:
    1. The POST request starts the job (202).
    2. The GET request returns the current progress (200).
    3. The background thread completes even in a test environment.
    """
    # 1. Setup Mocks and Payload
    api_key: str = app.config["API_KEY"]
    headers: Dict[str, str] = {"X-API-KEY": api_key}

    # We use a real scraper URL mock to ensure the thread has work to do
    mock_url = "https://www.conjugacao.com.br/verbo-falar/"
    requests_mock.get(mock_url, text=sample_html("falar.html"))

    payload = {"tasks": [{"verb": "falar", "mode": "Indicativo", "tense": "Presente"}]}

    # 2. Execution: Start the Job
    post_resp = client.post("/api/v1/batch", json=payload, headers=headers)
    assert post_resp.status_code == 202
    job_id: str = post_resp.get_json()["job_id"]

    # 3. Execution: Poll the status until completed
    # This loop prevents the "no such table" error by keeping the test
    # (and the :memory: database) alive until the thread finishes.
    max_retries = 10
    finished = False

    for _ in range(max_retries):
        get_resp = client.get(f"/api/v1/batch/{job_id}", headers=headers)
        assert get_resp.status_code == 200

        data = get_resp.get_json()
        if data["status"] == "completed":
            finished = True
            break

        time.sleep(0.5)  # Wait for the thread to process

    # 4. Final Assertions
    assert finished is True
    assert data["progress"]["success"] == 1

    # Verify persistence check
    with app.app_context():
        from src.models.verb import Verb

        assert Verb.query.filter_by(infinitive="falar").first() is not None


def test_api_batch_status_not_found(client: FlaskClient, app: Any) -> None:
    """Verify that polling a non-existent UUID returns a 404."""
    api_key: str = app.config["API_KEY"]
    headers: Dict[str, str] = {"X-API-KEY": api_key}

    response = client.get("/api/v1/batch/invalid-uuid", headers=headers)
    assert response.status_code == 404
    assert response.get_json()["error"] == "Job not found"
