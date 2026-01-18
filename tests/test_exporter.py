"""
Unit tests for the AnkiExporter service.

Verifies structural integrity, column counts, and line counts of the
Anki-ready CSV output.
"""

import csv
import io
from src.models.verb import Conjugation, Person
from src.services.exporter import AnkiExporter


def test_generate_verb_csv_all_persons(app) -> None:
    """
    Test that all 6 persons are exported when skip_tu_vos is False.
    """
    # 1. Setup mock data (simulating DB objects)
    p1 = Person(name="eu", sort_order=0)
    p2 = Person(name="tu", sort_order=1)

    # We create mock conjugation objects
    c1 = Conjugation(value="falo", person=p1)
    c2 = Conjugation(value="falas", person=p2)

    # 2. Execute
    csv_output = AnkiExporter.generate_verb_csv(
        conjugations=[c1, c2],
        verb_infinitive="falar",
        mode_name="Indicativo",
        tense_name="Presente",
        skip_tu_vos=False,
    )

    # 3. Assert
    # Column A: Verb
    assert "falar" in csv_output
    # Column B: Both forms separated by newline
    # Note: Pandas adds quotes when it sees a newline
    assert '"falo\nfalas"' in csv_output
    # Column C: Tags
    assert "Indicativo Presente" in csv_output


def test_generate_verb_csv_skip_tu_vos(app) -> None:
    """
    Test that tu and vós are correctly excluded when skip_tu_vos is True.
    """
    p1 = Person(name="eu", sort_order=0)
    p2 = Person(name="tu", sort_order=1)  # Should be skipped
    p3 = Person(name="ele/ela/você", sort_order=2)

    conjugations = [
        Conjugation(value="falo", person=p1),
        Conjugation(value="falas", person=p2),
        Conjugation(value="fala", person=p3),
    ]

    csv_output = AnkiExporter.generate_verb_csv(
        conjugations=conjugations,
        verb_infinitive="falar",
        mode_name="Indicativo",
        tense_name="Presente",
        skip_tu_vos=True,
    )

    # Assert 'falas' (tu) is NOT in the output
    assert "falo" in csv_output
    assert "fala" in csv_output
    assert "falas" not in csv_output


def test_generate_verb_csv_structural_integrity(app) -> None:
    """
    Verify the CSV has exactly 1 row, 3 columns, and 6 lines in the second column.
    """
    # 1. Setup: Create 6 mock conjugations (The full set)
    persons = [
        Person(name=n, sort_order=i)
        for i, n in enumerate(["eu", "tu", "ele", "nós", "vós", "eles"])
    ]
    conjugations = [
        Conjugation(value=f"form_{i}", person=p) for i, p in enumerate(persons)
    ]

    # 2. Execute
    csv_output = AnkiExporter.generate_verb_csv(
        conjugations=conjugations,
        verb_infinitive="test-verb",
        mode_name="Indicativo",
        tense_name="Presente",
        skip_tu_vos=False,
    )

    # 3. Structural Analysis
    # Use the csv module to parse the string buffer
    reader = csv.reader(io.StringIO(csv_output))
    rows = list(reader)

    # A. Verify Row Count: Should be exactly 1 (for one verb search)
    assert len(rows) == 1

    # B. Verify Column Count: Should be exactly 3 (Verb, Conjugations, Tag)
    row = rows[0]
    assert len(row) == 3

    # C. Verify Column B Content (The multiline field):
    # Split by newline and count the forms
    forms = row[1].split("\n")
    assert len(forms) == 6
    assert forms[0] == "form_0"
    assert forms[5] == "form_5"

    # D. Verify Column C (The Tag):
    assert row[2] == "Indicativo Presente"


def test_generate_verb_csv_skip_tu_vos_structural(app) -> None:
    """
    Verify that when skipping tu/vós, the second column contains exactly 4 lines.
    """
    # 1. Setup: 6 persons
    person_names = ["eu", "tu", "ele", "nós", "vós", "eles"]
    conjugations = [
        Conjugation(value=f"val_{i}", person=Person(name=n))
        for i, n in enumerate(person_names)
    ]

    # 2. Execute with skip_tu_vos=True
    csv_output = AnkiExporter.generate_verb_csv(
        conjugations=conjugations,
        verb_infinitive="falar",
        mode_name="Indicativo",
        tense_name="Presente",
        skip_tu_vos=True,
    )

    # 3. Analysis
    reader = csv.reader(io.StringIO(csv_output))
    rows = list(reader)
    conjugation_field = rows[0][1]

    # Split the field and verify the count
    forms = [f for f in conjugation_field.split("\n") if f]

    # EXACT count check: 6 total - 2 (tu/vós) = 4
    assert len(forms) == 4
    # Ensure specific forms are absent
    assert "val_1" not in forms  # tu
    assert "val_4" not in forms  # vós
