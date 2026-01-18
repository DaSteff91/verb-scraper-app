"""
CSV Exporter Service.

Handles the transformation of 5NF database records into Anki-ready CSV strings
using in-memory buffers for Docker compatibility.
"""

import io
import logging
from typing import List

import pandas as pd

from src.models.verb import Conjugation

logger = logging.getLogger(__name__)


class AnkiExporter:
    """Service to handle Anki-specific data exports."""

    @staticmethod
    def generate_verb_csv(
        conjugations: List[Conjugation],
        verb_infinitive: str,
        mode_name: str,
        tense_name: str,
        skip_tu_vos: bool = False,
    ) -> str:
        """
        Format conjugations into a 3-column CSV string.

        Args:
            conjugations: List of Conjugation objects from the DB.
            verb_infinitive: The infinitive of the verb.
            mode_name: Name of the grammatical mode.
            tense_name: Name of the grammatical tense.
            skip_tu_vos: If True, filters out 2nd person sing/plural.

        Returns:
            str: The CSV content as a string.
        """
        logger.info(
            "Generating CSV for %s (%s %s)", verb_infinitive, mode_name, tense_name
        )

        # 1. Filter logic
        filtered_list: List[str] = []
        for conj in conjugations:
            if skip_tu_vos and conj.person.name in ["tu", "vós"]:
                continue
            filtered_list.append(conj.value)

        # 2. Replicate your original format logic
        # Column B: Conjugations joined by newline
        formatted_conjugations: str = "\n".join(filtered_list)

        # Column C: Tags
        tag: str = f"{mode_name} {tense_name}"

        # 3. Use Pandas for clean CSV generation
        data = {"A": [verb_infinitive], "B": [formatted_conjugations], "C": [tag]}

        df = pd.DataFrame(data)

        # 4. Export to string buffer (In-memory)
        # We use no header and no index to match your original Anki import style
        output = io.StringIO()
        df.to_csv(
            output, header=False, index=False, quoting=1
        )  # quoting=1 ensures strings are quoted if they contain newlines

        return output.getvalue()
