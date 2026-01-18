"""
CSV Exporter Service.

Handles the transformation of 5NF database records into Anki-ready CSV strings
using in-memory buffers for Docker compatibility.
"""

import csv
import io
import logging
from typing import List

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
            skip_tu_vos: If True, filters out 2nd person sing/plural (tu/vós).

        Returns:
            str: The CSV content as a formatted string.
        """
        logger.info(
            "Generating CSV for %s (%s %s). Filter tu/vós: %s",
            verb_infinitive,
            mode_name,
            tense_name,
            skip_tu_vos,
        )

        # 1. Filter logic
        filtered_list: List[str] = [
            conj.value
            for conj in conjugations
            if not (skip_tu_vos and conj.person.name in ["tu", "vós"])
        ]

        # 2. Replicate original format logic
        formatted_conjugations: str = "\n".join(filtered_list)
        tag: str = f"{mode_name} {tense_name}"

        # 3. Export to string buffer (In-memory) using standard csv module
        output: io.StringIO = io.StringIO()

        # lineterminator='\n' matches Pandas default to_csv behavior on Linux
        # quoting=csv.QUOTE_ALL matches Pandas quoting=1
        writer = csv.writer(output, quoting=csv.QUOTE_ALL, lineterminator="\n")

        # 4. Write the single row (Column A, B, C)
        writer.writerow([verb_infinitive, formatted_conjugations, tag])

        return output.getvalue()
