import logging
import requests
from abc import ABC, abstractmethod
from typing import List, Optional

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """
    Abstract Base Class for all verb scraping providers.

    Ensures a consistent interface across different web sources and
    manages shared configurations like network timeouts and headers.
    """

    def __init__(self) -> None:
        """
        Initialize the scraper with shared network settings.
        """
        self.timeout: int = 10
        # Use a Session object for performance (Keep-Alive)
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            }
        )
        logger.debug("%s initialized with persistent Session.", self.__class__.__name__)

    @abstractmethod
    def get_conjugations(self, verb: str, mode: str, tense: str) -> Optional[List[str]]:
        """
        Fetch and parse conjugations from the source.

        Args:
            verb: The infinitive form of the verb.
            mode: The grammatical mode.
            tense: The grammatical tense.

        Returns:
            Optional[List[str]]: A list of strings in 'pronoun verb' format,
                or None if the source fails or data is missing.
        """
        pass
