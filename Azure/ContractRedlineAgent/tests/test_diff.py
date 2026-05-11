"""Tests for the word-level diff and tokenizer."""

from __future__ import annotations

import pytest

from redline_core import tokenize, word_diff


class TestTokenizer:
    def test_round_trip_preserves_text(self):
        text = "Hello, world!  This\tis a   test."
        assert "".join(tokenize(text)) == text

    def test_round_trip_with_unicode(self):
        text = "Contoso–Vendor Agreement (€500)."
        assert "".join(tokenize(text)) == text

    def test_separates_words_whitespace_punctuation(self):
        toks = tokenize("Hello, world!")
        assert toks == ["Hello", ",", " ", "world", "!"]


class TestWordDiff:
    def test_no_change_yields_only_equal(self):
        diff = word_diff("Payment within thirty days.", "Payment within thirty days.")
        kinds = [s.kind for s in diff]
        assert kinds == ["equal"]

    def test_simple_word_replace(self):
        diff = word_diff("Payment within thirty days.", "Payment within sixty days.")
        kinds = [s.kind for s in diff]
        assert "replace" in kinds
        replaces = [s for s in diff if s.kind == "replace"]
        assert any("thirty" in s.del_text and "sixty" in s.ins_text for s in replaces)

    def test_pure_insertion(self):
        diff = word_diff("Payment within thirty days.", "Net payment within thirty days.")
        # SequenceMatcher may model a leading prefix-add as an insert OR as a
        # case-shift-driven replace (Payment -> Net payment); accept either.
        ins_or_replace = [s for s in diff if s.kind in ("insert", "replace")]
        assert any("Net" in s.ins_text for s in ins_or_replace)

    def test_pure_deletion(self):
        diff = word_diff(
            "The Vendor's liability shall not exceed the fees paid.",
            "The Vendor's liability shall not exceed the fees.",
        )
        deletes = [s for s in diff if s.kind == "delete"]
        assert any("paid" in s.del_text for s in deletes)

    def test_unchanged_words_are_preserved(self):
        diff = word_diff(
            "Either party may terminate for convenience upon ninety days notice.",
            "Either party may terminate for convenience upon thirty days notice.",
        )
        equals = [s for s in diff if s.kind == "equal"]
        equal_text = " ".join(s.ins_text for s in equals)
        assert "Either party may terminate" in equal_text
        assert "days notice" in equal_text

    def test_whitespace_only_diff_is_collapsed(self):
        # Adding extra space should not produce noisy delete/insert segments.
        diff = word_diff("Payment within  thirty days.", "Payment within thirty days.")
        # The diff should contain at most one non-equal segment (the
        # collapsed extra space) — not a delete + insert pair.
        non_equal = [s for s in diff if s.kind != "equal"]
        assert len(non_equal) <= 1

    def test_diff_segments_are_lossless_for_replacement(self):
        original = "Payment within thirty (30) days of invoice receipt."
        replacement = "Payment within sixty (60) days of invoice issuance."
        diff = word_diff(original, replacement)

        del_text = "".join(
            s.del_text for s in diff if s.kind in ("equal", "delete", "replace")
        )
        ins_text = "".join(
            s.ins_text for s in diff if s.kind in ("equal", "insert", "replace")
        )
        assert del_text == original
        assert ins_text == replacement
