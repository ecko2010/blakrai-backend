"""
Test localization — every key has all 3 languages, t() works with formatting.
"""

import pytest
from app.localization.texts import t, _TEXTS


class TestLocalizationCompleteness:
    """Every key in _TEXTS must have uk, en, ru."""

    def test_all_keys_have_three_languages(self):
        missing = []
        for key, translations in _TEXTS.items():
            for lang in ("uk", "en", "ru"):
                if lang not in translations:
                    missing.append(f"{key} missing '{lang}'")
        assert missing == [], f"Missing translations:\n" + "\n".join(missing)

    def test_no_empty_translations(self):
        empty = []
        for key, translations in _TEXTS.items():
            for lang, text in translations.items():
                if not text or not text.strip():
                    empty.append(f"{key}[{lang}] is empty")
        assert empty == [], f"Empty translations:\n" + "\n".join(empty)


class TestTFunction:
    """Test the t() lookup function."""

    def test_basic_lookup(self):
        for lang in ("uk", "en", "ru"):
            result = t("start.language_set", lang)
            assert isinstance(result, str)
            assert len(result) > 0

    def test_missing_key_returns_fallback(self):
        result = t("nonexistent.key.xyz", "en")
        # Should not crash — returns key name or fallback
        assert isinstance(result, str)

    def test_formatting_works(self):
        # start.main_menu has {tier} and {active_signals}
        result = t("start.main_menu", "en", tier="PRO", active_signals=5)
        assert "PRO" in result
        assert "5" in result

    def test_all_languages_return_different_content(self):
        """At least some keys should differ between languages."""
        uk = t("start.language_set", "uk")
        en = t("start.language_set", "en")
        ru = t("start.language_set", "ru")
        # All should be non-empty and at least 2 should differ
        assert uk and en and ru
        assert uk != en or en != ru
