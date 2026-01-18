"""
Live Contract Tests.

These tests perform real network requests to verify that the external
website (conjugacao.com.br) has not changed its HTML structure.
"""

import pytest
import requests
from bs4 import BeautifulSoup, Tag
from src.services.scraper import ConjugacaoScraper


@pytest.mark.online
def test_external_website_html_structure_contract() -> None:
    """
    Verify the 'Contract' between our scraper and the real website.

    This checks if 'h3' and 'h4' headers still exist in the expected hierarchy
    for a known stable verb ('ser').
    """
    url = "https://www.conjugacao.com.br/verbo-ser/"

    # 1. Perform a real request
    response = requests.get(url, timeout=10)
    assert response.status_code == 200, "Website is down or URL changed!"

    soup = BeautifulSoup(response.text, "html.parser")

    # 2. Verify Mode (h3) exists
    # We look for the most common mode 'Indicativo'
    mode_header = None
    for h3 in soup.find_all("h3"):
        if h3.get_text(strip=True) == "Indicativo":
            mode_header = h3
            break

    assert mode_header is not None, "Structure Change: <h3>Indicativo</h3> not found!"

    # 3. Verify Tense (h4) exists within that Mode's parent container
    container = mode_header.parent
    assert isinstance(container, Tag), "Structure Change: <h3> parent is not a Tag!"

    tense_header = container.find("h4", string="Presente")
    assert tense_header is not None, (
        "Structure Change: <h4>Presente</h4> not found inside Indicativo scope!"
    )

    # 4. Verify data exists (p tag following h4)
    conjugation_p = tense_header.find_next_sibling("p")
    assert conjugation_p is not None, (
        "Structure Change: Conjugation <p> not found after <h4>!"
    )
    assert len(conjugation_p.get_text()) > 10, (
        "Structure Change: Conjugation <p> is empty!"
    )


@pytest.mark.online
def test_external_website_data_format_contract() -> None:
    """
    Verify the data format returned by the live website.

    This ensures that:
    1. The scraper successfully returns a list (not None).
    2. The list contains exactly 6 strings (The full persona set).
    3. Each string contains at least two words (Pronoun + Verb).
    """
    # 1. Setup with a known stable verb
    scraper = ConjugacaoScraper()
    verb = "ser"
    mode = "Indicativo"
    tense = "Presente"

    # 2. Execute (Actual network request)
    results = scraper.get_conjugations(verb, mode, tense)

    # 3. Assert Structural Contract
    assert results is not None, (
        "Contract Failed: Scraper returned None for a valid verb."
    )
    assert isinstance(results, list), "Contract Failed: Scraper did not return a list."

    # We expect exactly 6 persons for Indicativo Presente
    assert len(results) == 6, (
        f"Contract Failed: Expected 6 persons, got {len(results)}."
    )

    # 4. Assert Content Format Contract
    # We expect strings like "eu sou", "tu és", etc.
    # At the very least, they should have a space between pronoun and verb.
    for i, form in enumerate(results):
        assert isinstance(form, str), f"Contract Failed: Item {i} is not a string."
        assert " " in form, f"Contract Failed: Item '{form}' lacks a space separator."
        assert len(form.split()) >= 2, (
            f"Contract Failed: Item '{form}' does not contain at least 2 words."
        )

    # 5. Spot Check specific data
    # This ensures our whitespace cleaning isn't accidentally gluing words together
    assert results[0] == "eu sou", (
        f"Contract Failed: First person should be 'eu sou', got '{results[0]}'."
    )
