import logging
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup, Tag

from src.services.base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class CooljugatorScraper(BaseScraper):
    """
    Backup scraper implementation for cooljugator.com.

    This scraper reconstructs the 'pronoun + verb' format by pairing
    separate DOM elements, ensuring consistency with the primary source.
    """

    def __init__(self) -> None:
        """
        Initialize the backup scraper with its specific base URL and tense mapping.
        """
        super().__init__()
        self.base_url: str = "https://cooljugator.com/pt/"

        # Maps internal (Mode, Tense) pairs to Cooljugator's HTML ID prefixes
        self.map_ids: Dict[tuple[str, str], str] = {
            ("Indicativo", "Presente"): "present",
            ("Indicativo", "Pretérito Imperfeito"): "imperfect",
            ("Indicativo", "Pretérito Perfeito"): "preterite",
            ("Indicativo", "Pretérito Mais-que-perfeito"): "past_perfect",
            ("Indicativo", "Futuro do Presente"): "future",
            ("Indicativo", "Futuro do Pretérito"): "conditional",
            ("Subjuntivo", "Presente"): "subj_present",
            ("Subjuntivo", "Futuro"): "subj_future",
        }

    def get_conjugations(self, verb: str, mode: str, tense: str) -> Optional[List[str]]:
        """
        Fetch and parse conjugations from Cooljugator.

        Args:
            verb: The infinitive form of the verb.
            mode: The grammatical mode.
            tense: The grammatical tense.

        Returns:
            Optional[List[str]]: List of combined 'pronoun verb' strings.
        """
        url = f"{self.base_url}{verb.lower().strip()}"
        logger.info("Backup Source: Scraping URL: %s", url)

        id_prefix: Optional[str] = self.map_ids.get((mode, tense))
        if not id_prefix:
            logger.warning("Backup Source: No ID mapping for %s %s", mode, tense)
            return None

        try:
            response = requests.get(url, timeout=self.timeout, headers=self.headers)
            response.raise_for_status()
        except requests.RequestException as e:
            logger.error("Backup Source connection failure for %s: %s", url, e)
            return None

        soup = BeautifulSoup(response.text, "html.parser")
        clean_lines: List[str] = []

        try:
            # Cooljugator uses IDs like 'present1', 'present2', etc. (1-6)
            for i in range(1, 7):
                cell_id: str = f"{id_prefix}{i}"
                cell: Optional[Tag] = soup.find(id=cell_id)  # type: ignore

                if not cell:
                    continue

                # 1. Extract the Verb form (usually in .meta-form)
                verb_elem: Optional[Tag] = cell.find(class_="meta-form")  # type: ignore
                if not verb_elem:
                    continue
                verb_val: str = verb_elem.get_text(strip=True)

                # 2. Extract the Pronoun

                pronouns = ["eu", "tu", "ele/ela/você", "nós", "vós", "eles/elas/vocês"]
                p_val: str = pronouns[i - 1]

                # 3. Combine to match "Gold Standard" format: "pronoun verb"
                clean_lines.append(f"{p_val} {verb_val}")

            if not clean_lines:
                logger.warning("Backup Source: Found 0 forms for %s", cell_id)
                return None

            logger.info(
                "Backup Source: Successfully extracted %d forms.", len(clean_lines)
            )
            return clean_lines

        except Exception as e:
            logger.error("Unexpected parsing error in Backup Source: %s", e)
            return None
