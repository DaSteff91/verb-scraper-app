"""
Tests for API v1 Parameter Logic.

This module verifies that dialect filtering and Anki-specific formatting
parameters work correctly on the retrieval endpoint.
"""

from typing import Any, Dict, List
from flask.testing import FlaskClient
from flask import Flask


def test_api_get_verb_dialect_br(client: FlaskClient, app: Flask) -> None:
    """
    Verify that the 'br' dialect (default) filters out 2nd person forms.
    """
    # 1. Setup: Auth and endpoint
    api_key: str = app.config["API_KEY"]
    headers: Dict[str, str] = {"X-API-KEY": api_key}

    # 2. Execution: Request 'comer' with default dialect
    response = client.get(
        "/api/v1/verbs/comer?mode=Indicativo&tense=Presente", headers=headers
    )
    assert response.status_code == 200

    data = response.get_json()
    conjugations: List[Dict[str, str]] = data["conjugations"]

    # 3. Assertions: Brazilian dialect should have exactly 4 forms (no tu/vós)
    assert len(conjugations) == 4
    for conj in conjugations:
        assert conj["person"] not in ["tu", "vós"]
    assert data["dialect"] == "Brazilian (no tu/vós)"


def test_api_get_verb_dialect_pt(client: FlaskClient, app: Flask) -> None:
    """
    Verify that the 'pt' dialect includes all 6 person forms.
    """
    api_key: str = app.config["API_KEY"]
    headers: Dict[str, str] = {"X-API-KEY": api_key}

    # Request 'comer' with European dialect
    response = client.get(
        "/api/v1/verbs/comer?dialect=pt&mode=Indicativo&tense=Presente", headers=headers
    )
    assert response.status_code == 200

    data = response.get_json()
    conjugations: List[Dict[str, str]] = data["conjugations"]

    # European dialect should have all 6 forms
    assert len(conjugations) == 6
    person_names = [c["person"] for c in conjugations]
    assert "tu" in person_names
    assert "vós" in person_names
    assert data["dialect"] == "European (standard)"


def test_api_get_verb_anki_format(client: FlaskClient, app: Flask) -> None:
    """
    Verify that anki=true returns the expected CSV snapshot string.
    """
    api_key: str = app.config["API_KEY"]
    headers: Dict[str, str] = {"X-API-KEY": api_key}

    # Request 'comer' with anki formatting enabled
    url = "/api/v1/verbs/comer?mode=Indicativo&tense=Presente&anki=true"
    response = client.get(url, headers=headers)
    assert response.status_code == 200

    data = response.get_json()
    assert "anki_string" in data

    # Check that the anki_string follows the expected CSV structure
    # Expected: "comer","eu como\nele come\nnós comemos\neles comem","Indicativo Presente"
    anki_str: str = data["anki_string"]
    assert anki_str.startswith('"comer"')
    assert "Indicativo Presente" in anki_str
    # Verify newlines exist within the middle column
    assert "\n" in anki_str
