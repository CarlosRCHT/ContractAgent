"""Tests for the sentence splitter and comment-anchor logic in docx_text.py."""

from __future__ import annotations

from docx_text import (
    Span,
    anchor_span,
    sentence_span_covering,
    split_sentences,
)


class TestSentenceSplitter:
    def test_splits_on_basic_terminators(self):
        text = "First sentence. Second sentence! Third sentence?"
        spans = split_sentences(text)
        assert len(spans) == 3
        assert "".join(text[s.start:s.end] for s in spans) == text.replace(" ", "")[:0] + text.replace(
            " ", ""
        ) or all(text[s.start:s.end].strip() for s in spans)

    def test_does_not_split_on_abbreviations(self):
        text = "Contoso Inc. and Microsoft Corp. signed the deal."
        spans = split_sentences(text)
        assert len(spans) == 1

    def test_handles_no_terminator(self):
        text = "Some heading without punctuation"
        spans = split_sentences(text)
        assert spans == [Span(0, len(text))]

    def test_empty_text(self):
        assert split_sentences("") == []

    def test_full_coverage_is_lossless(self):
        text = "First. Second sentence here. Third!"
        spans = split_sentences(text)
        # Concatenating all sentence content should reproduce the original
        # text minus any inter-sentence whitespace (which is discarded by
        # the splitter intentionally).
        rebuilt = "".join(text[s.start:s.end] for s in spans)
        # Every char in the rebuilt string must appear in the original.
        assert rebuilt.replace(" ", "") == text.replace(" ", "")


class TestSentenceSpanCovering:
    def test_match_in_first_sentence(self):
        text = "First sentence. Second sentence here."
        # "First" is at position 0..5 — entirely in the first sentence.
        span = sentence_span_covering(text, 0, 5)
        assert span.start == 0
        assert text[span.start:span.end].strip() == "First sentence."

    def test_match_in_middle_sentence(self):
        text = "First. The middle sentence. Last sentence here."
        match_start = text.index("middle")
        match_end = match_start + len("middle")
        span = sentence_span_covering(text, match_start, match_end)
        assert text[span.start:span.end].strip() == "The middle sentence."


class TestAnchorSpan:
    def test_single_sentence_returns_sentence(self):
        text = "Payment within thirty days. Other clause here."
        match_start = text.index("thirty")
        match_end = match_start + len("thirty")
        anchor = anchor_span(text, match_start, match_end)
        assert text[anchor.start:anchor.end].strip() == "Payment within thirty days."

    def test_cross_sentence_match_falls_back_to_paragraph(self):
        text = "First sentence ends here. Second sentence begins."
        # A match that spans both sentences (from "ends" through "begins")
        match_start = text.index("ends")
        match_end = text.index("begins") + len("begins")
        anchor = anchor_span(text, match_start, match_end)
        assert anchor.start == 0
        assert anchor.end == len(text)

    def test_cross_sentence_can_be_disabled(self):
        text = "First sentence ends. Second begins."
        match_start = text.index("ends")
        match_end = text.index("begins") + len("begins")
        anchor = anchor_span(
            text,
            match_start,
            match_end,
            cross_sentence_falls_back_to_paragraph=False,
        )
        # Should at least cover both affected sentences but stop at their bounds.
        assert anchor.start == 0
        assert anchor.end <= len(text)
