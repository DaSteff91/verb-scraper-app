"""
Remote API Contract Tests.

These tests hit the live deployed API to verify security,
format integrity, and asynchronous job workflows.
"""

import requests
from typing import Dict


def test_api_security_gatekeeper(
    api_config: Dict[str, str], auth_header: Dict[str, str]
) -> None:
    """
    Verify that the API correctly enforces authentication.
    """
    url = f"{api_config['v1_prefix']}/verbs/comer"

    # 1. Test: Missing Key (Expected 401)
    response_fail = requests.get(url)
    assert response_fail.status_code == 401
    assert response_fail.json()["error"] == "Unauthorized: Invalid or missing API Key"

    # 2. Test: Correct Key (Expected 200)
    # Note: Assumes 'comer' has been scraped at least once on the server
    response_success = requests.get(url, headers=auth_header)
    assert response_success.status_code == 200
    assert "infinitive" in response_success.json()


def test_api_error_handler_safety_net(
    api_config: Dict[str, str], auth_header: Dict[str, str]
) -> None:
    """
    Verify that the Global Error Handler returns JSON even for missing routes.
    """
    url = f"{api_config['v1_prefix']}/non-existent-route"

    response = requests.get(url, headers=auth_header)

    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert "status_code" in data
    assert data["status_code"] == 404
