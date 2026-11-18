"""Tests for the golden dataset (evals/datasets/golden.jsonl).

PURPOSE: catch broken dataset entries the moment they're written, before
they can produce wrong eval scores. Checks structure only (fields, page
ranges, unique ids, splits); answer correctness is verified by hand.
"""

from pathlib import Path

import pytest

from evals.datasets import schema

REPORTS = Path(__file__).resolve().parent.parent / "data" / "reports"


def test_golden_dataset_is_valid():
    """load() raises with a list of every problem if any entry is broken."""
    entries = schema.load()
    assert entries, "golden.jsonl is empty"


def test_both_splits_are_used():
    """A dev split for tuning and a held-out test split must both exist."""
    splits = {e["split"] for e in schema.load()}
    assert splits == {"dev", "test"}


@pytest.mark.parametrize("doc, pages", schema.DOC_PAGES.items())
def test_page_counts_match_the_real_pdfs(doc, pages):
    """The page counts used for range checks must match the actual PDFs.
    Skipped when the PDFs aren't present (they're gitignored)."""
    path = REPORTS / doc
    if not path.exists():
        pytest.skip(f"{doc} not downloaded")
    import pdfplumber

    with pdfplumber.open(path) as pdf:
        assert len(pdf.pages) == pages


# ---------- The validator itself catches the mistakes it's meant to ----------

GOOD = {
    "id": "x", "doc": "tcs_ar_fy25.pdf", "question": "q?", "expected_answer": "a",
    "expected_values": ["1,234"], "expected_pages": [181], "page_match": "any",
    "statement": "consolidated", "category": "fact", "split": "dev", "verified": "claude",
}


def test_validator_accepts_a_good_entry():
    assert schema.validate(GOOD) == []


@pytest.mark.parametrize(
    "change, expected_problem",
    [
        ({"expected_page": [181]}, "unknown field"),         # typo'd field name
        ({"expected_pages": [999]}, "outside"),              # page past the end of the PDF
        ({"split": "train"}, "'split'"),                     # invalid split
        ({"category": "not_in_report"}, "no expected pages"),  # contradictory
        ({"expected_values": ["n/a"]}, "containing a number"),
        ({"expected_pages": []}, "at least one expected page"),
    ],
)
def test_validator_catches_mistakes(change, expected_problem):
    entry = {**GOOD, **change}
    assert any(expected_problem in p for p in schema.validate(entry))
