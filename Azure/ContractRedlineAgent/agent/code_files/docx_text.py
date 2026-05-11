"""Plain-text helpers over a python-docx ``Document``.

Used for two purposes:

1. **Context extraction** for the LLM coherence check — given a paragraph
   index, return the surrounding ±N paragraphs as plain text.
2. **Sentence-aware comment anchoring** — given the character span of a
   matched recommendation, return the start/end character offsets of the
   sentence(s) containing it (or the whole paragraph when the match crosses
   sentence boundaries).

Deterministic, no NLP dependencies.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Optional

# A small abbreviation list so the splitter doesn't break on common
# contract-relevant tokens (e.g. "Inc.", "Ltd.", "Co."). The trailing period
# of an abbreviation is *kept inside* the same sentence.
_ABBREVIATIONS = frozenset(
    {
        "inc", "ltd", "co", "corp", "llc", "llp", "plc",
        "no", "vs", "etc", "e.g", "i.e", "cf", "viz",
        "mr", "mrs", "ms", "dr", "jr", "sr", "st",
        "u.s", "u.s.a", "u.k", "fig", "para", "sec",
    }
)

# Match a sentence terminator (.?!) followed by whitespace and a likely
# sentence start (capital letter, digit, or opening quote/bracket).
_SENTENCE_END = re.compile(r"([.!?])(\s+)(?=[\"'(\[A-Z0-9])")


@dataclass(frozen=True)
class Span:
    start: int
    end: int

    def __post_init__(self):
        if self.end < self.start:
            raise ValueError(f"Invalid span: {self.start}..{self.end}")

    def __contains__(self, idx: int) -> bool:
        return self.start <= idx < self.end


# ---------------------------------------------------------------------------
# Document helpers
# ---------------------------------------------------------------------------


def paragraph_texts(doc) -> list[str]:
    """Return the plain text of every paragraph in document order."""
    return [p.text for p in doc.paragraphs]


def context_window(doc, paragraph_index: int, radius: int = 2) -> str:
    """Return ±*radius* paragraphs around *paragraph_index* as one string.

    Used to give the LLM enough surrounding text to evaluate whether a
    proposed change still makes sense in context.
    """
    texts = paragraph_texts(doc)
    if not texts:
        return ""
    lo = max(0, paragraph_index - radius)
    hi = min(len(texts), paragraph_index + radius + 1)
    return "\n\n".join(t for t in texts[lo:hi] if t)


def find_paragraph_index(doc, search_text: str) -> Optional[int]:
    """Return the index of the first paragraph containing *search_text*.

    Search is case-insensitive and whitespace-insensitive (tabs/newlines
    inside *search_text* are collapsed to single spaces before matching).
    """
    needle = _normalize_whitespace(search_text).lower()
    if not needle:
        return None
    for i, para in enumerate(doc.paragraphs):
        haystack = _normalize_whitespace(para.text).lower()
        if needle in haystack:
            return i
    return None


# ---------------------------------------------------------------------------
# Sentence-level comment anchoring
# ---------------------------------------------------------------------------


def split_sentences(text: str) -> list[Span]:
    """Return character spans for each sentence in *text*.

    Spans cover the full text exactly: ``"".join(text[s.start:s.end] for s
    in split_sentences(text)) == text``.
    """
    if not text:
        return []

    spans: list[Span] = []
    cursor = 0
    for match in _SENTENCE_END.finditer(text):
        end_punct = match.start() + 1  # include the . ? !
        # Reject the split if the token preceding the period is a known abbr.
        preceding = text[cursor:match.start()].rstrip().lower()
        last_token = re.split(r"\s+", preceding)[-1] if preceding else ""
        if last_token.rstrip(".") in _ABBREVIATIONS:
            continue
        spans.append(Span(cursor, end_punct))
        cursor = end_punct  # whitespace after the punctuation belongs to the next sentence
        # Skip the whitespace captured by group(2) — start of next sentence is the char after it.
        cursor = match.end()

    if cursor < len(text):
        spans.append(Span(cursor, len(text)))

    # Edge case: no terminator anywhere.
    if not spans:
        spans.append(Span(0, len(text)))

    return spans


def sentence_span_covering(
    paragraph_text: str, match_start: int, match_end: int
) -> Span:
    """Return the span of the sentence(s) containing the matched range.

    If the match falls inside a single sentence, returns that sentence's
    span. If it crosses sentence boundaries, returns the union from the
    first to the last affected sentence. Falls back to the whole paragraph
    when sentences cannot be determined.
    """
    if match_end <= match_start:
        return Span(0, len(paragraph_text))

    sentences = split_sentences(paragraph_text)
    if not sentences:
        return Span(0, len(paragraph_text))

    first_idx: Optional[int] = None
    last_idx: Optional[int] = None
    for i, s in enumerate(sentences):
        # A sentence is "affected" if [match_start, match_end) overlaps it.
        if s.start < match_end and s.end > match_start:
            if first_idx is None:
                first_idx = i
            last_idx = i

    if first_idx is None or last_idx is None:
        return Span(0, len(paragraph_text))

    return Span(sentences[first_idx].start, sentences[last_idx].end)


def anchor_span(
    paragraph_text: str,
    match_start: int,
    match_end: int,
    *,
    cross_sentence_falls_back_to_paragraph: bool = True,
) -> Span:
    """Return the comment-anchor span for a match.

    Defaults to the smallest covering sentence span. When the match
    crosses more than one sentence boundary and *cross_sentence_falls_back_to_paragraph*
    is true (the default), expands to the whole paragraph.
    """
    sentences = split_sentences(paragraph_text)
    affected = [
        i
        for i, s in enumerate(sentences)
        if s.start < match_end and s.end > match_start
    ]
    if cross_sentence_falls_back_to_paragraph and len(affected) > 1:
        return Span(0, len(paragraph_text))
    return sentence_span_covering(paragraph_text, match_start, match_end)


# ---------------------------------------------------------------------------
# Internal utilities
# ---------------------------------------------------------------------------


def _normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def iter_paragraph_runs(paragraph) -> Iterable[tuple[int, str]]:
    """Yield ``(run_index, run_text)`` for every run in a paragraph."""
    for i, run in enumerate(paragraph.runs):
        yield i, run.text or ""
