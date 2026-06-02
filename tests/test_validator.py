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


def test_parse_verbs_single_valid() -> None:
    assert InputValidator.parse_verbs(" Comer ") == ["comer"]


def test_parse_verbs_multi_dedupes_and_preserves_order() -> None:
    assert InputValidator.parse_verbs("falar, ir, ir, comer") == [
        "falar",
        "ir",
        "comer",
    ]


def test_parse_verbs_rejects_invalid_token() -> None:
    assert InputValidator.parse_verbs("falar, bad_verb; DROP TABLE") is None


def test_parse_verbs_rejects_empty_input() -> None:
    assert InputValidator.parse_verbs("   ") is None


def test_parse_verbs_rejects_too_many_verbs() -> None:
    # parse_verbs MAX_VERBS_PER_INPUT is 25 -> provide 26 unique (all match the regex).
    raw = ",".join(list("abcdefghijklmnopqrstuvwxyz"))
    assert InputValidator.parse_verbs(raw) is None
