"""Deterministic retrieval metrics: did search return the evidence?

PURPOSE: score one search result list against a golden-dataset entry using
only page numbers and numbers in the text. No LLM is involved, so these
metrics are free, instant and exactly repeatable. They are the backbone of
the retrieval eval; LLM-judged metrics (DeepEval) are added on top.

Terms used below:
    retrieved   the ranked list of chunks search returned, best first; each
                has a page number and text
    k           how many of the top results we look at (k=4 is what the app
                uses today)

Metrics (all between 0 and 1, higher is better):
    hit_at_k          1 if the top k results include an expected page
                      (for page_match "all": include EVERY expected page)
    reciprocal_rank   1 / rank of the first result from an expected page
                      (rank 1 -> 1.0, rank 2 -> 0.5, rank 4 -> 0.25, none -> 0)
    page_recall_at_k  fraction of expected pages found in the top k
    value_hit_at_k    1 if every expected number appears in the top k chunks'
                      text (format-insensitive: 2,55,324 == 255,324)
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

# A number as printed in the reports: 2,55,324 | 255,324 | 134.19 | (1,272)
_NUMBER = re.compile(r"\(?\d[\d,]*(?:\.\d+)?\)?")


def to_decimal(text: str) -> Decimal | None:
    """Parse a printed number into an exact value, ignoring formatting.

    "2,55,324" and "255,324" (Indian vs international grouping, F4) both
    become 255324; "43.00" equals "43"; "(1,272)" is the accounting way of
    writing -1272. Returns None if it isn't a number.
    """
    negative = text.startswith("(") and text.endswith(")")
    digits = text.strip("()").replace(",", "")
    try:
        value = Decimal(digits)
    except InvalidOperation:
        return None
    return -value if negative else value


def numbers_in(text: str) -> set[Decimal]:
    """Every number that appears in a piece of text, as exact values."""
    values = set()
    for match in _NUMBER.findall(text):
        value = to_decimal(match.rstrip(","))
        if value is not None:
            values.add(value)
            # A number written in brackets may be a negative amount OR just a
            # number in parentheses, like "Europe (2)"; keep both readings.
            values.add(abs(value))
    return values


def _top_pages(retrieved: list[dict], k: int) -> list[int]:
    return [chunk["page"] for chunk in retrieved[:k]]


def hit_at_k(retrieved: list[dict], expected_pages: list[int], page_match: str, k: int) -> float:
    """1.0 if the top k contain an expected page ("any") or all of them ("all")."""
    found = set(_top_pages(retrieved, k)) & set(expected_pages)
    if page_match == "all":
        return float(found == set(expected_pages))
    return float(bool(found))


def reciprocal_rank(retrieved: list[dict], expected_pages: list[int]) -> float:
    """1 / position of the first chunk from an expected page; 0 if none."""
    for rank, chunk in enumerate(retrieved, start=1):
        if chunk["page"] in expected_pages:
            return 1.0 / rank
    return 0.0


def page_recall_at_k(retrieved: list[dict], expected_pages: list[int], k: int) -> float:
    """Fraction of the expected pages that appear in the top k."""
    if not expected_pages:
        return 0.0
    found = set(_top_pages(retrieved, k)) & set(expected_pages)
    return len(found) / len(set(expected_pages))


def value_hit_at_k(retrieved: list[dict], expected_values: list[str], k: int) -> float | None:
    """1.0 if every expected number appears in the top k chunks' text.

    Returns None when there is nothing to check (no expected values), so the
    caller can leave that question out of the average instead of counting it.
    """
    targets = [to_decimal(v) for v in expected_values]
    if not targets:
        return None
    found = set()
    for chunk in retrieved[:k]:
        found |= numbers_in(chunk["text"])
    return float(all(t in found for t in targets))
