"""
Security and Resilience Hardening Tests.

This module verifies that the application correctly handles unauthorized
access attempts, malformed external HTML, and invalid API payloads.
"""

from typing import Any, Dict
import requests_mock
from flask.testing import FlaskClient
from flask import Flask

from src.services.scraper import ConjugacaoScraper


def test_api_auth_unauthorized_attempts(client: FlaskClient) -> None:
    """
    Verify the API decorator blocks requests with missing or invalid keys.
    """
    url = "/api/v1/verbs/comer"

    # 1. Attempt: Missing Header (Expected 401)
    resp_missing = client.get(url)
    assert resp_missing.status_code == 401
    assert (
        resp_missing.get_json()["error"] == "Unauthorized: Invalid or missing API Key"
    )

    # 2. Attempt: Invalid Key (Expected 401)
    resp_invalid = client.get(url, headers={"X-API-KEY": "wrong-token"})
    assert resp_invalid.status_code == 401


def test_scraper_handling_incomplete_html(requests_mock: requests_mock.Mocker) -> None:
    """
    Verify the scraper returns None gracefully when external HTML is malformed.
    """
    scraper = ConjugacaoScraper()
    verb = "broken"
    url = f"{scraper.base_url}{verb}/"

    # 1. Mock HTML that has the mode header (h3) but no data paragraph (p)
    broken_html = "<h3>Indicativo</h3><div>No paragraph here</div>"
    requests_mock.get(url, text=broken_html)

    results = scraper.get_conjugations(verb, "Indicativo", "Presente")

    # Scraper should return None instead of raising an AttributeError
    assert results is None


def test_api_batch_invalid_payloads(client: FlaskClient, app: Flask) -> None:
    """
    Verify the batch endpoint rejects empty or malformed JSON payloads.
    """
    api_key: str = app.config["API_KEY"]
    headers: Dict[str, str] = {"X-API-KEY": api_key, "Content-Type": "application/json"}

    # 1. Attempt: Empty tasks list
    resp_empty = client.post("/api/v1/batch", json={"tasks": []}, headers=headers)
    assert resp_empty.status_code == 400
    assert "invalid data" in resp_empty.get_json()["error"]

    # 2. Attempt: Malformed JSON structure
    resp_malformed = client.post("/api/v1/batch", data="not-json", headers=headers)
    assert resp_malformed.status_code == 400


def test_api_global_error_handler_json(client: FlaskClient, app: Flask) -> None:
    """
    Verify the global error handler returns JSON for 404 routes, not HTML.
    """
    api_key: str = app.config["API_KEY"]
    headers: Dict[str, str] = {"X-API-KEY": api_key}

    # Request a non-existent API route
    response = client.get("/api/v1/non-existent-endpoint", headers=headers)

    assert response.status_code == 404
    assert response.is_json
    data = response.get_json()
    assert "error" in data
    assert data["status_code"] == 404
