"""
Input Validation Service.

Provides robust sanitization and validation for user-provided data
to prevent SSRF, Injection, and Resource Exhaustion attacks.
"""

import re
import logging
from typing import Set

logger = logging.getLogger(__name__)


class InputValidator:
    """
    Service to validate and sanitize incoming web requests.
    """

    # Portuguese verbs use standard letters, cedilha (ç), accents, and hyphens
    # This regex prevents characters like '.', '/', '?', '&', etc.
    VERB_PATTERN: str = r"^[a-zA-Záàâãéèêíïóôõöúçñ\s-]+$"

    # Limits to prevent Denial of Service (DoS) attacks
    MAX_VERB_LENGTH: int = 35

    # Whitelist for Grammatical Modes and Tenses
    ALLOWED_MODES: Set[str] = {"Indicativo", "Subjuntivo", "Imperativo"}
    ALLOWED_TENSES: Set[str] = {
        "Presente",
        "Pretérito Imperfeito",
        "Pretérito Perfeito",
        "Pretérito Mais-que-perfeito",
        "Futuro do Presente",
        "Futuro do Pretérito",
        "Futuro",
        "Afirmativo",
        "Negativo",
    }

    @classmethod
    def is_valid_verb(cls, verb: str) -> bool:
        """
        Check if a verb is string-safe and within length limits.

        Args:
            verb: The raw verb input from the user.

        Returns:
            bool: True if valid, False otherwise.
        """
        if not verb or len(verb) > cls.MAX_VERB_LENGTH:
            logger.warning("Validation Failed: Verb length/presence. Got: %s", verb)
            return False

        if not re.match(cls.VERB_PATTERN, verb):
            logger.warning(
                "Validation Failed: Malicious characters detected in: %s", verb
            )
            return False

        return True

    @classmethod
    def is_valid_grammar(cls, mode: str, tense: str) -> bool:
        """
        Check if the mode and tense match our supported whitelist.

        Args:
            mode: The grammatical mode.
            tense: The grammatical tense.

        Returns:
            bool: True if both exist in whitelist, False otherwise.
        """
        if mode not in cls.ALLOWED_MODES:
            logger.warning("Validation Failed: Unauthorized Mode: %s", mode)
            return False

        if tense not in cls.ALLOWED_TENSES:
            logger.warning("Validation Failed: Unauthorized Tense: %s", tense)
            return False

        return True
