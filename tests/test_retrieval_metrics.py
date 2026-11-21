"""Tests for evals/graders/retrieval_metrics.py.

PURPOSE: a wrong metric produces confident wrong scores (Finding F5), so each
metric is checked on small hand-worked examples before it's trusted.
"""

from decimal import Decimal

from evals.graders.retrieval_metrics import (
    hit_at_k,
    numbers_in,
    page_recall_at_k,
    reciprocal_rank,
    to_decimal,
    value_hit_at_k,
)

# Search results, best first.
RETRIEVED = [
    {"page": 88, "text": "Revenue overview FY 2025 255,324"},
    {"page": 253, "text": "Standalone EPS 132.83"},
    {"page": 181, "text": "Revenue from operations 12 2,55,324 2,40,893 EPS 134.19"},
    {"page": 23, "text": "Dividend of ₹126 per share"},
    {"page": 95, "text": "Headcount 607,979"},
]


def test_number_parsing_ignores_format():
    # Indian and international grouping are the same number (Finding F4).
    assert to_decimal("2,55,324") == to_decimal("255,324") == Decimal(255324)
    assert to_decimal("43.00") == to_decimal("43")
    assert to_decimal("(1,272)") == Decimal(-1272)  # accounting negative
    assert to_decimal("n/a") is None


def test_numbers_in_text():
    found = numbers_in("Europe (2) 79,487 and loss (1,272)")
    assert {Decimal(2), Decimal(79487), Decimal(-1272), Decimal(1272)} <= found


def test_hit_at_k_any():
    assert hit_at_k(RETRIEVED, [181], "any", k=4) == 1.0  # page 181 is rank 3
    assert hit_at_k(RETRIEVED, [181], "any", k=2) == 0.0  # not in the top 2
    assert hit_at_k(RETRIEVED, [181, 95], "any", k=4) == 1.0  # one of them is enough


def test_hit_at_k_all():
    assert hit_at_k(RETRIEVED, [181, 95], "all", k=5) == 1.0
    assert hit_at_k(RETRIEVED, [181, 95], "all", k=4) == 0.0  # 95 is rank 5


def test_reciprocal_rank():
    assert reciprocal_rank(RETRIEVED, [88]) == 1.0
    assert reciprocal_rank(RETRIEVED, [181]) == 1 / 3
    assert reciprocal_rank(RETRIEVED, [181, 253]) == 0.5  # first expected page wins
    assert reciprocal_rank(RETRIEVED, [999]) == 0.0


def test_page_recall_at_k():
    assert page_recall_at_k(RETRIEVED, [181, 95], k=4) == 0.5
    assert page_recall_at_k(RETRIEVED, [181, 95], k=5) == 1.0


def test_value_hit_is_format_insensitive():
    # "2,55,324" expected; page 88 chunk prints "255,324" -> still a hit at k=1.
    assert value_hit_at_k(RETRIEVED, ["2,55,324"], k=1) == 1.0
    assert value_hit_at_k(RETRIEVED, ["134.19"], k=2) == 0.0  # only 132.83 so far
    assert value_hit_at_k(RETRIEVED, ["134.19"], k=3) == 1.0
    assert value_hit_at_k(RETRIEVED, ["126", "607,979"], k=5) == 1.0  # all values needed
    assert value_hit_at_k(RETRIEVED, ["126", "607,979"], k=4) == 0.0


def test_value_hit_does_not_match_inside_bigger_numbers():
    # 4,422 must not count as found inside 14,422.
    assert value_hit_at_k([{"page": 1, "text": "Total 14,422"}], ["4,422"], k=1) == 0.0


def test_value_hit_without_values_is_not_counted():
    assert value_hit_at_k(RETRIEVED, [], k=4) is None
