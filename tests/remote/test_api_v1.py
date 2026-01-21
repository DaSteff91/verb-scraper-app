"""
Remote API Contract Tests.

These tests hit the live deployed API to verify security,
format integrity, and asynchronous job workflows.
"""

import requests
from typing import Dict
import time
import os
import pytest

REMOTE_TESTS_ENABLED = os.getenv("TEST_API_KEY") is not None


@pytest.mark.skipif(
    not REMOTE_TESTS_ENABLED,
    reason="Remote API tests require TEST_API_KEY environment variable",
)
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
    # Note: Verb "comer" is already seeded in the DB to verify against
    response_success = requests.get(url, headers=auth_header)
    assert response_success.status_code == 200
    assert "infinitive" in response_success.json()


@pytest.mark.skipif(
    not REMOTE_TESTS_ENABLED,
    reason="Remote API tests require TEST_API_KEY environment variable",
)
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


@pytest.mark.skipif(
    not REMOTE_TESTS_ENABLED,
    reason="Remote API tests require TEST_API_KEY environment variable",
)
def test_api_dialect_and_anki_snapshot(
    api_config: Dict[str, str], auth_header: Dict[str, str]
) -> None:
    """
    Verify that the API produces the correct dialect output and Anki CSV format.
    """
    base_url = f"{api_config['v1_prefix']}/verbs/comer"

    # 1. Test Brazilian Dialect (Default)
    resp_br = requests.get(base_url, headers=auth_header)
    data_br = resp_br.json()
    # Brazilian should have 4 persons for Indicativo Presente (excluding tu/vós)
    # Filter to check only Indicativo Presente if mixed data exists
    indicativo_pres = [
        c
        for c in data_br["conjugations"]
        if c["mode"] == "Indicativo" and c["tense"] == "Presente"
    ]
    assert len(indicativo_pres) == 4
    assert all(c["person"] not in ["tu", "vós"] for c in indicativo_pres)

    # 2. Test European Dialect (All 6)
    resp_pt = requests.get(f"{base_url}?dialect=pt", headers=auth_header)
    data_pt = resp_pt.json()
    indicativo_pres_pt = [
        c
        for c in data_pt["conjugations"]
        if c["mode"] == "Indicativo" and c["tense"] == "Presente"
    ]
    assert len(indicativo_pres_pt) == 6

    # 3. Snapshot Check: Anki CSV Representation
    # Indicativo Presente for Brazilian dialect to get a stable row
    url_anki = f"{base_url}?mode=Indicativo&tense=Presente&anki=true"
    resp_anki = requests.get(url_anki, headers=auth_header)
    anki_string = resp_anki.json()["anki_string"]

    # GOLD STANDARD: This is exactly what the exporter should output for comer/indicativo/presente/br
    expected_row = (
        '"comer","eu como\nele come\nnós comemos\neles comem","Indicativo Presente"'
    )

    assert anki_string == expected_row, (
        "The Anki CSV output does not match the Gold Standard!"
    )


@pytest.mark.skipif(
    not REMOTE_TESTS_ENABLED,
    reason="Remote API tests require TEST_API_KEY environment variable",
)
def test_api_batch_async_flow(
    api_config: Dict[str, str], auth_header: Dict[str, str]
) -> None:
    """
    Verify the full asynchronous lifecycle: POST -> 202 -> Polling -> Completed.
    """
    # 1. Trigger the Batch (We use two verbs to ensure concurrency happens)
    url_batch = f"{api_config['v1_prefix']}/batch"
    payload = {
        "tasks": [
            {"verb": "ir", "mode": "Subjuntivo", "tense": "Presente"},
            {"verb": "falar", "mode": "Indicativo", "tense": "Presente"},
        ]
    }

    response = requests.post(url_batch, json=payload, headers=auth_header)

    # Assert 'Accepted' status and receipt of Job ID
    assert response.status_code == 202
    data = response.json()
    job_id = data["job_id"]
    status_url = f"{api_config['base_url']}{data['check_status_url']}"

    # 2. Polling Loop
    max_attempts = 30
    job_finished = False

    for _ in range(max_attempts):
        status_resp = requests.get(status_url, headers=auth_header)
        assert status_resp.status_code == 200
        job_data = status_resp.json()

        if job_data["status"] == "completed":
            job_finished = True
            break

        if job_data["status"] == "failed":
            pytest.fail(f"Background Job {job_id} failed on the server.")

        time.sleep(1)  # Wait before checking again

    # 3. Final Assertions
    assert job_finished is True, f"Job {job_id} timed out after 30 seconds."
    assert job_data["progress"]["total"] == 2
    assert job_data["progress"]["success"] == 2
    assert job_data["completed_at"] is not None
