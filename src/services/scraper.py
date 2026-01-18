"""
Web Scraper Service.

This module provides the ConjugacaoScraper class to extract verb
conjugations from the conjugacao.com.br website.
"""

import logging
import requests
from bs4 import BeautifulSoup, Tag
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

        # DEBUG: List all headers to see what we are working with
        all_modes = [h3.get_text(strip=True) for h3 in soup.find_all("h3")]
        logger.debug("Available Modes (h3) on page: %s", all_modes)

        try:
            # 1. Find the Mode Header (h3)
            # We look for all h3 tags and match the text
            mode_headers = [
                h3 for h3 in soup.find_all("h3") if h3.get_text(strip=True) == mode
            ]

            if not mode_headers:
                logger.warning("Mode '%s' NOT FOUND", mode)
                return None

            conjugation_p: Optional[Tag] = None

            # 2. Scope Search (Your Original Logic)
            # We look inside the PARENT of each mode_header for the correct tense
            for m_header in mode_headers:
                container = m_header.parent
                if not container or not isinstance(container, Tag):
                    continue

                # Search for the tense (h4) ONLY inside this container
                tense_header = container.find("h4", string=tense)
                if tense_header and isinstance(tense_header, Tag):
                    logger.info("Found '%s' inside '%s' container", tense, mode)

                    # Grab the paragraph following the tense header
                    # In this site, it's often a sibling of h4 OR inside the h4's parent
                    # To be safe, we look for the next <p> after the h4
                    conjugation_p = tense_header.find_next_sibling("p")
                    if conjugation_p:
                        break

            if not conjugation_p:
                logger.warning("Could not find data for %s %s", mode, tense)
                return None

            # 3. Clean the contents (keeping Pronoun + Verb together)
            clean_lines: List[str] = []
            p_html = conjugation_p.encode_contents().decode("utf-8")
            # Standardize line breaks
            parts = p_html.replace("<br/>", "<br>").split("<br>")

            for part in parts:
                temp_soup = BeautifulSoup(part, "html.parser")
                text = temp_soup.get_text(separator=" ").strip()
                if text:
                    clean_lines.append(text)

            logger.info("Extracted %d lines.", len(clean_lines))
            return clean_lines

        except Exception as e:
            logger.error("Scraping error for %s: %s", verb, e)
            return None
