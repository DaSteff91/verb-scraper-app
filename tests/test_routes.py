"""
Functional tests for the Flask Routes (Controllers).

This module simulates user interaction with the web interface to verify
routing and template rendering.
"""

import time
from flask.testing import FlaskClient
from typing import Dict, Any
import requests_mock
from src.services.verb_manager import VerbManager


def test_index_route_get(client: FlaskClient) -> None:
    """Verify the home page loads correctly."""
    response = client.get("/")
    assert response.status_code == 200
    assert b"Portuguese Infinitive" in response.data
    assert b"Scrape" in response.data
    assert b"Add to Cart" not in response.data
    assert b"Scrape Summary" in response.data


def test_scrape_form_submission_success(
    client: FlaskClient, requests_mock: requests_mock.Mocker, sample_html
) -> None:
    """Verify the async scrape endpoint returns summary payload for in-page UX."""
    # Mock the website response
    mock_content = sample_html("falar.html")
    requests_mock.get("https://www.conjugacao.com.br/verbo-falar/", text=mock_content)

    response = client.post(
        "/scrape-summary",
        json={
            "verb": "falar",
            "modes": ["Indicativo"],
            "tenses": ["Presente"],
            "filename": "verbs_export",
        },
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "success"
    assert data["summary"][0]["verb"] == "falar"
    assert data["summary"][0]["mode"] == "Indicativo"
    assert data["summary"][0]["tense"] == "Presente"
    assert len(data["summary"][0]["conjugations"]) == 6


def test_scrape_form_submission_dedupes_duplicate_tenses(
    client: FlaskClient, requests_mock: requests_mock.Mocker, sample_html
) -> None:
    """Verify duplicate tense entries in payload are deduped server-side."""
    mock_content = sample_html("falar.html")
    requests_mock.get("https://www.conjugacao.com.br/verbo-falar/", text=mock_content)

    response = client.post(
        "/scrape-summary",
        json={
            "verb": "falar",
            "modes": ["Indicativo"],
            "tenses": ["Presente", "Presente"],
        },
    )

    assert response.status_code == 200
    data = response.get_json()
    assert len(data["tasks"]) == 1
    assert len(data["summary"]) == 1


def test_scrape_form_submission_multiple_verbs(
    client: FlaskClient, requests_mock: requests_mock.Mocker, sample_html
) -> None:
    """Verify the scrape summary endpoint supports comma-separated infinitives."""
    requests_mock.get(
        "https://www.conjugacao.com.br/verbo-falar/",
        text=sample_html("falar.html"),
    )
    requests_mock.get(
        "https://www.conjugacao.com.br/verbo-ir/",
        text=sample_html("ir.html"),
    )

    response = client.post(
        "/scrape-summary",
        json={
            "verb": "falar, ir",
            "modes": ["Indicativo"],
            "tenses": ["Presente"],
        },
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "success"

    # One (verb × mode × tense) task per verb
    assert len(data["tasks"]) == 2
    assert len(data["summary"]) == 2
    assert data["summary"][0]["verb"] == "falar"
    assert data["summary"][1]["verb"] == "ir"


def test_scrape_form_submission_rejects_invalid_multi_verb(
    client: FlaskClient,
) -> None:
    """Verify a single invalid token in a multi-verb input is rejected."""
    response = client.post(
        "/scrape-summary",
        json={
            "verb": "falar, bad_verb; DROP TABLE",
            "modes": ["Indicativo"],
            "tenses": ["Presente"],
        },
    )
    assert response.status_code == 400
    assert "Invalid verb format" in response.get_json()["error"]


def test_scrape_summary_rejects_invalid_payload(client: FlaskClient) -> None:
    """Verify scrape summary endpoint validates JSON shape."""
    response = client.post(
        "/scrape-summary",
        json={"verb": "falar", "modes": "Indicativo", "tenses": ["Presente"]},
    )
    assert response.status_code == 400
    assert response.get_json()["error"] == "Modes and tenses must be lists."


def test_export_csv_route_success(
    client: FlaskClient, requests_mock: requests_mock.Mocker, sample_html
) -> None:
    """
    Verify the /export route returns a valid downloadable CSV.
    """
    # 1. Scrape 'ir' first so it exists in the in-memory DB
    mock_content = sample_html("ir.html")
    requests_mock.get("https://www.conjugacao.com.br/verbo-ir/", text=mock_content)
    client.post(
        "/scrape-summary",
        json={"verb": "ir", "modes": ["Indicativo"], "tenses": ["Presente"]},
    )

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

    manager = VerbManager()

    # Mock a website failure
    primary_url = f"{manager.primary_scraper.base_url}badverb/"
    requests_mock.get(primary_url, status_code=404)

    backup_url = f"{manager.backup_scraper.base_url}badverb"
    requests_mock.get(backup_url, status_code=404)

    # Submit scrape summary request
    response = client.post(
        "/scrape-summary",
        json={"verb": "badverb", "modes": ["Indicativo"], "tenses": ["Presente"]},
    )

    assert response.status_code == 404
    assert "Could not find the verb" in response.get_json()["error"]


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
