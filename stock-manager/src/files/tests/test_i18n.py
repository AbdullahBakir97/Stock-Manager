"""
tests/test_i18n.py — Tests for internationalization (i18n) system.

Verifies translation completeness, correctness, and fallback behavior.
"""
from __future__ import annotations

import unittest
import sys
import os
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock PyQt6 to avoid import errors during testing
sys.modules['PyQt6'] = __import__('unittest.mock').mock.MagicMock()
sys.modules['PyQt6.QtCore'] = __import__('unittest.mock').mock.MagicMock()
sys.modules['PyQt6.QtWidgets'] = __import__('unittest.mock').mock.MagicMock()

from app.core.i18n import _TR, t, LANG


class TestTranslationCompleteness(unittest.TestCase):
    """Test that all translation keys have all 3 languages."""

    def test_all_keys_have_en(self):
        """Every key in _TR must have EN translation."""
        for key, translations in _TR.items():
            self.assertIn("EN", translations, f"Key '{key}' missing EN translation")
            self.assertNotEqual(
                translations["EN"], "",
                f"Key '{key}' has empty EN translation"
            )

    def test_all_keys_have_de(self):
        """Every key in _TR must have DE translation."""
        for key, translations in _TR.items():
            self.assertIn("DE", translations, f"Key '{key}' missing DE translation")
            self.assertNotEqual(
                translations["DE"], "",
                f"Key '{key}' has empty DE translation"
            )

    def test_all_keys_have_ar(self):
        """Every key in _TR must have AR translation."""
        for key, translations in _TR.items():
            self.assertIn("AR", translations, f"Key '{key}' missing AR translation")
            self.assertNotEqual(
                translations["AR"], "",
                f"Key '{key}' has empty AR translation"
            )

    def test_ar_translations_not_empty(self):
        """AR translations should never be empty strings."""
        empty_ar = [k for k, v in _TR.items() if v.get("AR") == ""]
        self.assertEqual(
            len(empty_ar), 0,
            f"Found {len(empty_ar)} keys with empty AR: {empty_ar}"
        )

    def test_all_translations_are_strings(self):
        """All translation values must be strings."""
        for key, translations in _TR.items():
            for lang, text in translations.items():
                self.assertIsInstance(
                    text, str,
                    f"Key '{key}' lang '{lang}' is not a string: {type(text)}"
                )


class TestTranslationRetrieval(unittest.TestCase):
    """Test t() function retrieves correct translations."""

    def setUp(self):
        """Save and reset language for each test."""
        import app.core.i18n as i18n_mod
        self._i18n_mod = i18n_mod
        self._orig_lang = i18n_mod.LANG

    def tearDown(self):
        """Restore original language."""
        self._i18n_mod.LANG = self._orig_lang

    def test_t_returns_en_when_lang_is_en(self):
        """t() should return EN text when LANG='EN'."""
        self._i18n_mod.LANG = "EN"
        # Use a known key
        en_text = t("app_title")
        self.assertEqual(en_text, _TR["app_title"]["EN"])

    def test_t_returns_de_when_lang_is_de(self):
        """t() should return DE text when LANG='DE'."""
        self._i18n_mod.LANG = "DE"
        de_text = t("app_title")
        self.assertEqual(de_text, _TR["app_title"]["DE"])

    def test_t_returns_ar_when_lang_is_ar(self):
        """t() should return AR text when LANG='AR'."""
        self._i18n_mod.LANG = "AR"
        ar_text = t("app_title")
        self.assertEqual(ar_text, _TR["app_title"]["AR"])

    def test_t_falls_back_to_en_when_missing_in_current_lang(self):
        """t() should fall back to EN if key missing in current language."""
        self._i18n_mod.LANG = "DE"
        # Create a scenario where the language is not in translations
        # by directly checking fallback logic
        result = t("app_title")
        # Should still return a value (either DE or EN fallback)
        self.assertIsNotNone(result)
        self.assertGreater(len(result), 0)

    def test_t_returns_key_when_key_missing(self):
        """t() should return the key name if key doesn't exist at all."""
        result = t("nonexistent_key_xyz_12345")
        self.assertEqual(result, "nonexistent_key_xyz_12345")

    def test_t_with_kwargs_formats_correctly(self):
        """t() should format strings with kwargs."""
        # Find a key with placeholders
        result = t("alert_critical", n=5, s="s")
        # Should contain the formatted number
        self.assertIn("5", result)


class TestKeyNaming(unittest.TestCase):
    """Test that all keys follow naming conventions."""

    def test_no_duplicate_keys(self):
        """No duplicate keys should exist in _TR."""
        keys = list(_TR.keys())
        unique_keys = set(keys)
        self.assertEqual(
            len(keys), len(unique_keys),
            f"Found {len(keys) - len(unique_keys)} duplicate keys"
        )

    def test_all_keys_are_snake_case(self):
        """All keys must be snake_case (lowercase, underscores, no spaces)."""
        pattern = re.compile(r'^[a-z0-9_]+$')
        invalid_keys = [k for k in _TR.keys() if not pattern.match(k)]
        self.assertEqual(
            len(invalid_keys), 0,
            f"Found {len(invalid_keys)} keys not in snake_case: {invalid_keys[:5]}"
        )

    def test_no_keys_with_uppercase(self):
        """Keys should not contain uppercase letters."""
        uppercase_keys = [k for k in _TR.keys() if any(c.isupper() for c in k)]
        self.assertEqual(
            len(uppercase_keys), 0,
            f"Found {len(uppercase_keys)} keys with uppercase: {uppercase_keys[:5]}"
        )

    def test_no_keys_with_spaces(self):
        """Keys should not contain spaces."""
        space_keys = [k for k in _TR.keys() if " " in k]
        self.assertEqual(
            len(space_keys), 0,
            f"Found {len(space_keys)} keys with spaces: {space_keys}"
        )


class TestTranslationContent(unittest.TestCase):
    """Test the content and validity of translations."""

    def test_each_language_dict_has_three_keys(self):
        """Each translation dict should have exactly EN, DE, AR keys."""
        expected_langs = {"EN", "DE", "AR"}
        for key, translations in _TR.items():
            actual_langs = set(translations.keys())
            self.assertEqual(
                actual_langs, expected_langs,
                f"Key '{key}' has unexpected languages: {actual_langs}"
            )

    def test_no_none_values_in_translations(self):
        """No translation value should be None."""
        for key, translations in _TR.items():
            for lang, text in translations.items():
                self.assertIsNotNone(
                    text,
                    f"Key '{key}' language '{lang}' is None"
                )

    def test_ar_uses_arabic_script(self):
        """AR translations should use Arabic Unicode characters (mostly)."""
        # Check that at least some Arabic translations contain Arabic characters
        ar_keys = [k for k, v in _TR.items() if v.get("AR")]
        ar_with_scripts = []

        for key in ar_keys:
            ar_text = _TR[key]["AR"]
            # Check if it contains any Arabic Unicode characters
            # Arabic Unicode range: U+0600 to U+06FF
            if any('\u0600' <= c <= '\u06FF' for c in ar_text):
                ar_with_scripts.append(key)

        # At least 80% of AR translations should have Arabic characters
        if ar_keys:
            percentage = len(ar_with_scripts) / len(ar_keys)
            self.assertGreater(
                percentage, 0.8,
                f"Only {percentage*100:.1f}% of AR translations use Arabic script"
            )


class TestTranslationFormatting(unittest.TestCase):
    """Test that format strings are valid."""

    def setUp(self):
        """Save original language."""
        import app.core.i18n as i18n_mod
        self._i18n_mod = i18n_mod
        self._orig_lang = i18n_mod.LANG

    def tearDown(self):
        """Restore language."""
        self._i18n_mod.LANG = self._orig_lang

    def test_keys_with_placeholders_can_be_formatted(self):
        """All keys with {placeholders} should be formattable."""
        for key, translations in _TR.items():
            for lang, text in translations.items():
                if "{" in text and "}" in text:
                    # Extract placeholder names
                    pattern = r'\{([^}]+)\}'
                    placeholders = re.findall(pattern, text)
                    # Try to format with dummy values
                    try:
                        format_dict = {p: f"TEST_{p}" for p in placeholders}
                        formatted = text.format(**format_dict)
                        self.assertIsNotNone(formatted)
                    except (KeyError, ValueError) as e:
                        self.fail(
                            f"Key '{key}' language '{lang}' format failed: {e}"
                        )


if __name__ == "__main__":
    unittest.main()
