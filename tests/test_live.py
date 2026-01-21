"""
Live Contract Tests.

These tests perform real network requests to verify that the external
website (conjugacao.com.br) has not changed its HTML structure.
"""

import pytest
import requests
from bs4 import BeautifulSoup, Tag
from src.services.scraper import ConjugacaoScraper
from src.services.backup_scraper import CooljugatorScraper


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


@pytest.mark.online
def test_cooljugator_external_website_contract() -> None:
    """
    Verify the 'Contract' between our scraper and the live Cooljugator website.
    Ensures that IDs like 'present1' and class 'meta-form' still exist.
    """
    url = "https://cooljugator.com/pt/ir"

    # 1. Perform a real request
    response = requests.get(url, timeout=10)
    assert response.status_code == 200, "Cooljugator is down or URL changed!"

    soup = BeautifulSoup(response.text, "html.parser")

    # 2. Verify the ID-based structure (Present 1st person)
    first_person_cell = soup.find(id="present1")
    assert first_person_cell is not None, "Structure Change: id='present1' not found!"
    assert isinstance(first_person_cell, Tag)

    # 3. Verify the Verb data (meta-form class)
    verb_elem = first_person_cell.find(class_="meta-form")
    assert verb_elem is not None, (
        "Structure Change: class='meta-form' not found inside cell!"
    )

    verb_val = verb_elem.get_text(strip=True)
    assert verb_val == "vou", f"Data Change: Expected 'vou', got '{verb_val}'"


@pytest.mark.online
def test_cooljugator_full_scrape_contract() -> None:
    """
    Perform a live end-to-end scrape test for the backup source.
    """
    scraper = CooljugatorScraper()
    results = scraper.get_conjugations("ir", "Indicativo", "Presente")

    assert results is not None
    assert len(results) == 6
    assert results[0] == "eu vou"
    assert results[5] == "eles/elas/vocês vão"


@pytest.mark.online
def test_cooljugator_data_format_contract() -> None:
    """
    Verify the data format returned by the live Cooljugator website.

    This ensures that the backup source matches the 'Gold Standard'
    established for the primary source:
    1. The scraper returns a list (not None).
    2. The list contains exactly 6 strings.
    3. Each string contains at least two words (Pronoun + Verb).
    4. Spot-check specific data for accuracy.
    """
    # 1. Setup with a known stable verb
    scraper = CooljugatorScraper()
    verb = "ser"
    mode = "Indicativo"
    tense = "Presente"

    # 2. Execute (Actual network request)
    results = scraper.get_conjugations(verb, mode, tense)

    # 3. Assert Structural Contract
    assert results is not None, (
        "Contract Failed: Backup scraper returned None for a valid verb."
    )
    assert isinstance(results, list), "Contract Failed: Scraper did not return a list."

    # Exactly 6 persons for Indicativo Presente
    assert len(results) == 6, (
        f"Contract Failed: Expected 6 persons, got {len(results)}."
    )

    # 4. Assert Content Format Contract
    for i, form in enumerate(results):
        assert isinstance(form, str), f"Contract Failed: Item {i} is not a string."
        assert " " in form, f"Contract Failed: Item '{form}' lacks a space separator."
        assert len(form.split()) >= 2, (
            f"Contract Failed: Item '{form}' does not contain at least 2 words."
        )

    # 5. Gold Standard Spot Check
    # Ensures the backup source uses the same pronoun-verb normalization
    assert results[0] == "eu sou", (
        f"Contract Failed: First person should be 'eu sou', got '{results[0]}'."
    )
    assert results[3] == "nós somos", (
        f"Contract Failed: Fourth person should be 'nós somos', got '{results[3]}'."
    )
