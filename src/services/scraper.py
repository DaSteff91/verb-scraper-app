"""
Web Scraper Service.

This module provides the ConjugacaoScraper class to extract verb
conjugations from the conjugacao.com.br website.
"""

import logging
import requests
from bs4 import BeautifulSoup
from typing import Dict, List, Optional

# Setup logger for this service
logger = logging.getLogger(__name__)


class ConjugacaoScraper:
    """
    A service class to scrape verb conjugations.

    Attributes:
        base_url (str): The target website base URL.
        timeout (int): Request timeout in seconds.
    """

    def __init__(self) -> None:
        self.base_url: str = "https://www.conjugacao.com.br/verbo-"
        self.timeout: int = 10

    def get_conjugations(self, verb: str, mode: str, tense: str) -> Optional[List[str]]:
        """
        Fetch and parse conjugations for a specific verb, mode, and tense.

        Args:
            verb: The infinitive form of the verb (e.g., 'ir').
            mode: The grammatical mode (e.g., 'Indicativo').
            tense: The grammatical tense (e.g., 'Presente').

        Returns:
            Optional[List[str]]: A list of conjugated forms or None if not found.
        """
        url = f"{self.base_url}{verb.lower().strip()}/"
        logger.info("Scraping URL: %s", url)

        try:
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
        except requests.RequestException as e:
            logger.error("Failed to fetch %s: %s", url, e)
            return None

        soup = BeautifulSoup(response.text, "html.parser")

        try:
            # 1. Find the Mode (h3)
            mode_header = soup.find("h3", string=mode)
            if not mode_header:
                logger.warning("Mode '%s' not found for verb '%s'", mode, verb)
                return None

            mode_section = mode_header.parent

            # 2. Find the Tense (h4) inside that mode
            tense_header = mode_section.find("h4", string=tense)
            if not tense_header:
                logger.warning("Tense '%s' not found in mode '%s'", tense, mode)
                return None

            tense_section = tense_header.parent

            # 3. Get the paragraph containing the spans
            conjugation_p = tense_section.find("p")
            if not conjugation_p:
                return None

            # 4. Extract text, cleaning it as we go
            # This replicates your original logic but uses BS4's cleaner methods
            raw_lines = conjugation_p.get_text(separator="\n").split("\n")

            # Filter out empty strings and whitespace
            clean_lines = [line.strip() for line in raw_lines if line.strip()]

            # 5. Apply your custom logic (Removing tu and vós)
            # Standard Portuguese has 6 persons. Indices: 0(eu), 1(tu), 2(ele), 3(nós), 4(vós), 5(eles)
            if len(clean_lines) >= 6:
                # We create a new list excluding 2nd person singular and plural
                # eu, ele/ela, nós, eles/elas
                filtered_lines = [
                    clean_lines[0],  # eu
                    clean_lines[2],  # ele
                    clean_lines[3],  # nós
                    clean_lines[5],  # eles
                ]
                return filtered_lines

            return clean_lines

        except Exception as e:
            logger.error("Error parsing HTML for %s: %s", verb, e)
            return None
