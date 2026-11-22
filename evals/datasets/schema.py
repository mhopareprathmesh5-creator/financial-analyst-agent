"""Rules for a valid golden-dataset entry, and a loader that enforces them.

PURPOSE: every eval stage (retrieval, generation, agent) is graded against
golden.jsonl, so a broken entry silently produces wrong scores: a typo'd field
name, a page number past the end of the PDF, a duplicate id, or a missing
split that leaks test questions into tuning. This file defines the rules;
tests/test_golden_dataset.py runs them on every pytest run.

It checks STRUCTURE only. Whether an answer is actually correct can only be
checked by reading the PDF, which is why a sample is verified by hand.

One entry (one line of golden.jsonl):
    {
      "id": "tcs-eps-cons-01",                 unique
      "doc": "tcs_ar_fy25.pdf",                which report the question is about
      "question": "...",
      "expected_answer": "...",                reference answer text (DeepEval
                                               contextual recall/precision use it)
      "expected_values": ["134.19"],           numbers the answer must contain,
                                               written exactly as printed
      "expected_pages": [181],                 PDF pages holding the evidence
      "page_match": "any",                     "any": one of the pages is enough
                                               (fact printed in several places);
                                               "all": every page is needed
                                               (e.g. two facts on two pages)
      "statement": "consolidated",             consolidated | standalone | n/a
      "category": "consolidated_vs_standalone",
      "split": "dev",                          dev (for tuning) | test (held out)
      "verified": "owner",                     claude | owner (who checked it
                                               against the PDF)
      "paraphrase_of": "tcs-eps-cons-01",      optional: this entry asks the
                                               same thing as another entry in a
                                               user's own words (same answer,
                                               values and pages, same split)
      "notes": "..."                           optional
    }

Why paraphrases: the original questions use the report's own terms
("revenue from operations"), which favours keyword search (Finding F12).
Users say "sales". Paraphrases measure how search copes with real wording.
"""

from __future__ import annotations

import json
from pathlib import Path

DATASET_PATH = Path(__file__).resolve().parent / "golden.jsonl"

# Page counts of the reports, so page numbers can be range-checked without
# needing the (gitignored) PDFs. tests/test_golden_dataset.py confirms these
# against the real files when they are present.
DOC_PAGES = {
    "tcs_ar_fy25.pdf": 336,
    "infosys_ar_fy25.pdf": 369,
}

CATEGORIES = {
    "fact",                        # a figure from a financial table
    "consolidated_vs_standalone",  # the same figure differs between the two statements (F8)
    "narrative",                   # facts stated in prose: people, strategy, risks
    "calculation",                 # needs two or more facts combined (e.g. a margin)
    "multi_location",              # the fact is printed on several pages; any one counts
    "not_in_report",               # the report doesn't contain the answer: must not invent one
}
STATEMENTS = {"consolidated", "standalone", "n/a"}
SPLITS = {"dev", "test"}
VERIFIERS = {"claude", "owner"}
PAGE_MATCH = {"any", "all"}

REQUIRED = {
    "id": str,
    "doc": str,
    "question": str,
    "expected_answer": str,
    "expected_values": list,
    "expected_pages": list,
    "page_match": str,
    "statement": str,
    "category": str,
    "split": str,
    "verified": str,
}
OPTIONAL = {"notes": str, "paraphrase_of": str}

# A paraphrase must match its original on everything except id, question,
# notes and verified: it's the same question in different words.
PARAPHRASE_SAME_FIELDS = (
    "doc", "expected_answer", "expected_values", "expected_pages",
    "page_match", "statement", "category", "split",
)


def validate(entry: dict) -> list[str]:
    """Return a list of problems with one entry ([] means it's valid)."""
    problems = []

    # Every required field present with the right type; no unknown fields
    # (an unknown field is usually a typo of a real one).
    for field, kind in REQUIRED.items():
        if field not in entry:
            problems.append(f"missing field '{field}'")
        elif not isinstance(entry[field], kind):
            problems.append(f"'{field}' should be {kind.__name__}")
    for field in entry:
        if field not in REQUIRED and field not in OPTIONAL:
            problems.append(f"unknown field '{field}' (typo?)")
    if problems:
        return problems

    # Allowed values.
    checks = [
        ("doc", DOC_PAGES), ("category", CATEGORIES), ("statement", STATEMENTS),
        ("split", SPLITS), ("verified", VERIFIERS), ("page_match", PAGE_MATCH),
    ]
    for field, allowed in checks:
        if entry[field] not in allowed:
            problems.append(f"'{field}' is {entry[field]!r}; allowed: {sorted(allowed)}")
    for field in ("question", "expected_answer"):
        if not entry[field].strip():
            problems.append(f"'{field}' is empty")

    # Pages: whole numbers inside the PDF.
    pages = entry["expected_pages"]
    last_page = DOC_PAGES.get(entry["doc"])
    for page in pages:
        if not isinstance(page, int) or isinstance(page, bool):
            problems.append(f"page {page!r} is not a whole number")
        elif last_page and not 1 <= page <= last_page:
            problems.append(f"page {page} is outside 1..{last_page}")
    if len(set(pages)) != len(pages):
        problems.append("duplicate page numbers")

    # Values: non-empty strings containing a digit, written as printed.
    for value in entry["expected_values"]:
        if not isinstance(value, str) or not any(ch.isdigit() for ch in value):
            problems.append(f"expected value {value!r} should be a string containing a number")

    # Category-specific consistency.
    if entry["category"] == "not_in_report":
        if pages or entry["expected_values"]:
            problems.append("not_in_report entries must have no expected pages or values")
    elif not pages:
        problems.append("needs at least one expected page (only not_in_report has none)")
    if entry["category"] == "multi_location" and (len(pages) < 2 or entry["page_match"] != "any"):
        problems.append("multi_location needs 2+ pages and page_match 'any'")
    if entry["category"] == "consolidated_vs_standalone" and entry["statement"] == "n/a":
        problems.append("consolidated_vs_standalone must say which statement it asks about")

    return problems


def load(path: Path = DATASET_PATH) -> list[dict]:
    """Load golden.jsonl, raising ValueError listing every problem found.

    Eval scripts call this instead of reading the file directly, so they can
    never run on a broken dataset.
    """
    entries, problems, seen = [], [], set()
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue  # allow blank lines between groups of entries
        try:
            entry = json.loads(line)
        except json.JSONDecodeError as e:
            problems.append(f"line {line_no}: not valid JSON ({e})")
            continue
        label = f"line {line_no} ({entry.get('id', 'no id')})"
        problems += [f"{label}: {p}" for p in validate(entry)]
        if entry.get("id") in seen:
            problems.append(f"{label}: duplicate id")
        seen.add(entry.get("id"))
        entries.append(entry)

    # Paraphrases: the original must exist, not be a paraphrase itself, and
    # match on answer, pages and SPLIT (a paraphrase of a held-out test
    # question in the dev split would leak the test set into tuning).
    by_id = {e.get("id"): e for e in entries}
    for entry in entries:
        original_id = entry.get("paraphrase_of")
        if original_id is None:
            continue
        original = by_id.get(original_id)
        if original is None:
            problems.append(f"{entry['id']}: paraphrase_of '{original_id}' does not exist")
        elif "paraphrase_of" in original:
            problems.append(f"{entry['id']}: paraphrase_of points to another paraphrase")
        else:
            for field in PARAPHRASE_SAME_FIELDS:
                if entry.get(field) != original.get(field):
                    problems.append(f"{entry['id']}: '{field}' differs from its original {original_id}")

    if problems:
        raise ValueError("golden dataset has problems:\n" + "\n".join(problems))
    return entries
