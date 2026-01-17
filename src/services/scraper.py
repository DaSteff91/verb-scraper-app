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

            # 4. Extract text carefully
            # The site often uses: <p><span>eu</span> <span>vou</span><br>...</p>
            # We want to keep "eu vou" as one string.

            clean_lines: List[str] = []

            # We iterate through each 'line' which is usually separated by <br> tags
            # but in BS4 it's easier to look at the strings within the p tag.

            # We'll use a more surgical approach:
            p_text = conjugation_p.encode_contents().decode("utf-8")
            # Split by <br> or <br/> to get each person's line
            parts = p_text.replace("<br/>", "<br>").split("<br>")

            for part in parts:
                # Strip any remaining HTML tags from the part (like the spans)
                temp_soup = BeautifulSoup(part, "html.parser")
                text = temp_soup.get_text(separator=" ").strip()
                if text:
                    clean_lines.append(text)

            # 5. Apply your custom logic (Removing tu and vós)
            # Now clean_lines looks like: ["eu vou", "tu vais", "ele vai", ...]
            if len(clean_lines) >= 6:
                return [
                    clean_lines[0],  # eu vou
                    clean_lines[2],  # ele vai
                    clean_lines[3],  # nós vamos
                    clean_lines[5],  # eles vão
                ]

            return clean_lines

        except Exception as e:
            logger.error("Error parsing HTML for %s: %s", verb, e)
            return None
