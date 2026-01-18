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


# ... (existing imports and tests) ...


def test_get_conjugations_network_error(requests_mock: requests_mock.Mocker) -> None:
    """
    Test that the scraper returns None when a 404 or network error occurs.
    """
    scraper = ConjugacaoScraper()
    # Mock a 404 Not Found error
    requests_mock.get(f"{scraper.base_url}missing/", status_code=404)

    results = scraper.get_conjugations("missing", "Indicativo", "Presente")

    assert results is None


def test_get_conjugations_missing_tense(
    requests_mock: requests_mock.Mocker, sample_html: Callable[[str], str]
) -> None:
    """
    Test that the scraper returns None if the Mode exists but the Tense doesn't.
    """
    scraper = ConjugacaoScraper()
    mock_content = sample_html("falar.html")
    requests_mock.get(f"{scraper.base_url}falar/", text=mock_content)

    # Search for a tense that doesn't exist under Indicativo
    results = scraper.get_conjugations("falar", "Indicativo", "TenseFromMars")

    assert results is None


def test_get_conjugations_corrupt_html(requests_mock: requests_mock.Mocker) -> None:
    """
    Test that the scraper handles completely malformed or unexpected HTML.
    """
    scraper = ConjugacaoScraper()
    # Mock a page that only has the mode header but no content
    broken_html = "<h3>Indicativo</h3><p>Empty content</p>"
    requests_mock.get(f"{scraper.base_url}broken/", text=broken_html)

    # Search for a tense that is definitely not there
    results = scraper.get_conjugations("broken", "Indicativo", "Presente")

    assert results is None
