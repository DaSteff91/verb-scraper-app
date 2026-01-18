"""
Unit tests for the InputValidator service.
"""

from src.services.validator import InputValidator


def test_verb_validator_valid() -> None:
    assert InputValidator.is_valid_verb("comer") is True
    assert InputValidator.is_valid_verb("pôr-se") is True  # Hyphens allowed


def test_verb_validator_too_long() -> None:
    long_input = "a" * 100
    assert InputValidator.is_valid_verb(long_input) is False


def test_verb_validator_malicious_chars() -> None:
    assert InputValidator.is_valid_verb("comer; DROP TABLE") is False
    assert InputValidator.is_valid_verb("../etc/passwd") is False
    assert InputValidator.is_valid_verb("<script>") is False


def test_grammar_validator_whitelist() -> None:
    assert InputValidator.is_valid_grammar("Indicativo", "Presente") is True
    assert InputValidator.is_valid_grammar("Subjuntivo", "NonExistent") is False
