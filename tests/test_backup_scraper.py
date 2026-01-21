import pytest
import requests_mock
from typing import Callable, List, Optional
from src.services.backup_scraper import CooljugatorScraper


def test_cooljugator_parsing_logic(
    requests_mock: requests_mock.Mocker, sample_html: Callable[[str], str]
) -> None:
    """
    Verify that CooljugatorScraper correctly combines pronouns and verbs
    from separate DOM elements into the standard 'pronoun verb' format.
    """
    # 1. Setup
    verb = "ir"
    mode = "Indicativo"
    tense = "Presente"

    scraper = CooljugatorScraper()
    mock_content = sample_html("ir_cooljugator.html")
    requests_mock.get(f"{scraper.base_url}{verb}", text=mock_content)

    # 2. Execute
    results: Optional[List[str]] = scraper.get_conjugations(verb, mode, tense)

    # 3. Assert
    assert results is not None
    assert len(results) == 6
    # Verify the combined normalization (e.g., "eu" + "vou")
    assert results[0] == "eu vou"
    assert results[1] == "tu vais"
    assert results[2] == "ele/ela/você vai"
    assert results[3] == "nós vamos"
    assert results[4] == "vós ides"
    assert results[5] == "eles/elas/vocês vão"


def test_cooljugator_missing_mapping(requests_mock: requests_mock.Mocker) -> None:
    """
    Verify the scraper returns None gracefully when an unsupported
    mode/tense pair is requested.
    """
    scraper = CooljugatorScraper()
    # Attempt a mapping that isn't in self.map_ids
    results = scraper.get_conjugations("ir", "NonExistentMode", "Presente")

    assert results is None
