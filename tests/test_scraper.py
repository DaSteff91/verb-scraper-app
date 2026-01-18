"""
Unit tests for the ConjugacaoScraper service.

This module verifies that the scraper correctly parses HTML for both
regular and irregular verbs using local mock data.
"""

from typing import Callable, List, Optional

import requests_mock
from src.services.scraper import ConjugacaoScraper


def test_get_conjugations_regular_verb(
    requests_mock: requests_mock.Mocker, sample_html: Callable[[str], str]
) -> None:
    """
    Test that a regular verb (falar) is parsed correctly from mock HTML.

    Args:
        requests_mock: The pytest fixture to intercept HTTP requests.
        sample_html: Our custom fixture to load hablar.html.
    """
    # 1. Setup
    verb = "falar"
    mode = "Indicativo"
    tense = "Presente"

    # Load the local HTML file content
    mock_content = sample_html("falar.html")

    # Configure requests_mock to return our file content when this URL is called
    scraper = ConjugacaoScraper()
    target_url = f"{scraper.base_url}{verb}/"
    requests_mock.get(target_url, text=mock_content)

    # 2. Execute
    results: Optional[List[str]] = scraper.get_conjugations(verb, mode, tense)

    # 3. Assert (Verify the results)
    assert results is not None
    assert len(results) == 6
    assert results[0] == "eu falo"
    assert results[2] == "ele fala"
    assert results[5] == "eles falam"


def test_get_conjugations_irregular_verb(
    requests_mock: requests_mock.Mocker, sample_html: Callable[[str], str]
) -> None:
    """
    Test that an irregular verb (ir) with potentially messy HTML is parsed correctly.
    """
    # 1. Setup
    verb = "ir"
    mode = "Indicativo"
    tense = "Presente"

    mock_content = sample_html("ir.html")

    scraper = ConjugacaoScraper()
    requests_mock.get(f"{scraper.base_url}{verb}/", text=mock_content)

    # 2. Execute
    results = scraper.get_conjugations(verb, mode, tense)

    # 3. Assert
    assert results is not None
    assert len(results) == 6
    assert results[0] == "eu vou"
    assert results[1] == "tu vais"
    assert results[5] == "eles vão"


def test_get_conjugations_mode_not_found(
    requests_mock: requests_mock.Mocker, sample_html: Callable[[str], str]
) -> None:
    """
    Test that the scraper returns None gracefully if the mode doesn't exist.
    """
    scraper = ConjugacaoScraper()
    mock_content = sample_html("falar.html")
    requests_mock.get(f"{scraper.base_url}falar/", text=mock_content)

    # Try to find a mode that doesn't exist in the HTML
    results = scraper.get_conjugations("falar", "NonExistentMode", "Presente")

    assert results is None
