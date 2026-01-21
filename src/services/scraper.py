"""
Web Scraper Service.

This module provides the ConjugacaoScraper class to extract verb
conjugations from the conjugacao.com.br website.
"""

import logging
import re
import requests
from bs4 import BeautifulSoup, Tag
from typing import List, Optional

from src.services.base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class ConjugacaoScraper(BaseScraper):
    """
    A service class to scrape verb conjugations.

    Attributes:
        base_url (str): The target website base URL.
        timeout (int): Request timeout in seconds.
    """

    def __init__(self) -> None:
        super().__init__()
        self.base_url: str = "https://www.conjugacao.com.br/verbo-"

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
        logger.info("Primary Source: Scraping URL: %s", url)

        try:
            response = requests.get(url, timeout=self.timeout, headers=self.headers)
            response.raise_for_status()
        except requests.RequestException as e:
            logger.error("Primary Source connection failure for %s: %s", url, e)
            return None

        soup = BeautifulSoup(response.text, "html.parser")

        all_modes = [h3.get_text(strip=True) for h3 in soup.find_all("h3")]
        logger.debug("Available Modes (h3) on page: %s", all_modes)

        try:
            # 1. Locate the Mode (h3)
            mode_headers = [
                h3 for h3 in soup.find_all("h3") if h3.get_text(strip=True) == mode
            ]

            if not mode_headers:
                logger.warning("Mode '%s' NOT FOUND in Primary Source", mode)
                return None

            conjugation_p: Optional[Tag] = None

            # 2. Locate the Tense (h4) within the Mode's container
            for m_header in mode_headers:
                container = m_header.parent
                if not container or not isinstance(container, Tag):
                    continue

                tense_header = container.find("h4", string=tense)
                if tense_header and isinstance(tense_header, Tag):
                    conjugation_p = tense_header.find_next_sibling("p")
                    if conjugation_p:
                        break

            if not conjugation_p:
                return None

            # 3. Clean and parse HTML line breaks into a string list
            clean_lines: List[str] = []
            p_html = conjugation_p.encode_contents().decode("utf-8")
            parts = re.split(r"<br\s*/?>", p_html)

            for part in parts:
                temp_soup = BeautifulSoup(part, "html.parser")
                raw_text: str = temp_soup.get_text(separator=" ").strip()
                text: str = " ".join(raw_text.split())
                if text:
                    clean_lines.append(text)

            return clean_lines

        except Exception as e:
            logger.error("Unexpected parsing error in Primary Source: %s", e)
            return None
