"""Compare PDF readers on the annual reports and pick the most accurate one.

PURPOSE: our original reader (pypdf) corrupts numbers in the TCS report (the
digit 4 comes out as "ϰ", and numbers get stray spaces like "2, 40, 893").
A financial assistant is useless if it can't read numbers, so before
building anything else we measure which reader extracts these reports
correctly, and choose by score instead of by guess.

Method (the same shape as an LLM eval):
    1. Answer key: ground_truth.json lists table rows (label + numbers) read
       from rendered images of 4 key pages, i.e. what a person actually sees.
    2. Run every reader on those pages, twice: raw, and with the broken-font
       repair from rag/text_repair.py applied.
    3. Score:
         number accuracy  share of the 168 numbers found exactly as printed
         row integrity    share of the 54 rows whose label AND all its numbers
                          land on one line (so the LLM can tell which number
                          belongs to which line item)
       and, on a sample of pages spread across each report:
         garbage glyphs   characters like "ϰ" that mean broken font decoding
         fragmented words share of words broken into pieces ("Co n s o lid ated")
         speed            seconds per page
    4. Write results.md (committed as evidence for the README).

Run from the project root:
    python experiments/pdf_readers/compare.py
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path
from typing import Callable

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent.parent
REPORTS = PROJECT_ROOT / "data" / "reports"

# Python only looks for imports next to the script being run. Add the project
# root so `from rag.text_repair import ...` works from this subfolder.
sys.path.insert(0, str(PROJECT_ROOT))

# Every SAMPLE_STEP-th page of each report is used for the whole-document
# metrics (garbage, fragmentation, speed). Reading all ~700 pages with the
# slow readers takes a long time; a spread-out sample gives the same picture.
SAMPLE_STEP = 8


# ============================== Readers ==============================
# Each reader takes (pdf path, list of 1-based page numbers) and returns
# {page number: extracted text}. Imports are inside each function so a
# missing library only breaks that one reader.

def read_pypdf(path: Path, pages: list[int]) -> dict[int, str]:
    """pypdf: what our app uses now (via LangChain's PyPDFLoader)."""
    from pypdf import PdfReader

    reader = PdfReader(path)
    return {p: reader.pages[p - 1].extract_text() or "" for p in pages}


def read_pymupdf(path: Path, pages: list[int]) -> dict[int, str]:
    """PyMuPDF: fast C library, plain text output."""
    import pymupdf

    with pymupdf.open(path) as doc:
        return {p: doc[p - 1].get_text() for p in pages}


def read_pdfplumber(path: Path, pages: list[int]) -> dict[int, str]:
    """pdfplumber: works from character positions; known for tables."""
    import pdfplumber

    with pdfplumber.open(path) as pdf:
        return {p: pdf.pages[p - 1].extract_text() or "" for p in pages}


def read_pymupdf4llm(path: Path, pages: list[int]) -> dict[int, str]:
    """pymupdf4llm: PyMuPDF plus layout analysis; outputs Markdown with tables
    as rows like "| Revenue from operations | 2,55,324 | 2,40,893 |"."""
    import pymupdf4llm

    chunks = pymupdf4llm.to_markdown(
        str(path),
        pages=[p - 1 for p in pages],  # this library counts pages from 0
        page_chunks=True,  # one result per page, so we can score per page
        use_ocr=False,  # these PDFs contain real text; OCR would only slow it down
    )
    return {p: chunk["text"] for p, chunk in zip(pages, chunks)}


def with_repair(read: Callable[[Path, list[int]], dict[int, str]]):
    """Wrap a reader so its output goes through rag/text_repair.py, which
    fixes the broken-font glyphs (ϰ -> 4, (cid:1008) -> 4, ...)."""
    from rag.text_repair import repair_text

    def read_and_repair(path: Path, pages: list[int]) -> dict[int, str]:
        return {p: repair_text(t) for p, t in read(path, pages).items()}

    return read_and_repair


BASE_READERS: dict[str, Callable[[Path, list[int]], dict[int, str]]] = {
    "pypdf (current)": read_pypdf,
    "PyMuPDF": read_pymupdf,
    "pdfplumber": read_pdfplumber,
    "pymupdf4llm": read_pymupdf4llm,
}

# Every reader is scored twice: raw, and with the glyph repair applied.
READERS = {}
for _name, _read in BASE_READERS.items():
    READERS[_name] = _read
    READERS[f"{_name} + repair"] = with_repair(_read)


# ============================== Scoring ==============================

def normalise(text: str) -> str:
    """Remove formatting that isn't content, so readers are compared on what
    they extracted rather than how they decorated it: Markdown table pipes and
    bold markers, and footnote asterisks like "Tax expense*"."""
    return text.replace("|", " ").replace("*", "")


def value_pattern(value: str) -> re.Pattern:
    """Regex that finds a number only as a whole token, so "4,422" does not
    count as found inside "14,422" or "4,4221"."""
    return re.compile(r"(?<![\d.,])" + re.escape(value) + r"(?![\d]|[.,]\d)")


def label_in(label: str, line: str) -> bool:
    """Case-insensitive label match with spaces collapsed, so "TOTAL  INCOME"
    and "Total income" both count."""
    squash = lambda s: " ".join(s.lower().split())
    return squash(label) in squash(line)


def score_page_rows(text: str, rows: list[dict]) -> tuple[int, int, int, int, list[str]]:
    """Score one page against its answer-key rows.

    Returns (numbers found, numbers total, rows intact, rows total, failures)
    where failures are short descriptions used in the report.
    """
    text = normalise(text)
    lines = text.splitlines()
    found = total = intact = 0
    failures = []

    for row in rows:
        patterns = [value_pattern(v) for v in row["values"]]

        # Number accuracy: is each number present anywhere on the page?
        hits = [bool(p.search(text)) for p in patterns]
        found += sum(hits)
        total += len(hits)
        missing = [v for v, hit in zip(row["values"], hits) if not hit]
        if missing:
            failures.append(f"p{row['page']} {row['label']}: missing {', '.join(missing)}")

        # Row integrity: is there one line holding the label and all numbers?
        if any(label_in(row["label"], line) and all(p.search(line) for p in patterns) for line in lines):
            intact += 1

    return found, total, intact, len(rows), failures


# Short words that are real words, not fragments. Anything else of 1-2
# letters (like "Co", "n", "ed" from "Co n s o lid ated") counts as a fragment.
REAL_SHORT_WORDS = {
    "a", "i", "an", "as", "at", "be", "by", "do", "if", "in", "is", "it", "no",
    "of", "on", "or", "so", "to", "up", "us", "we", "he", "my", "me", "go",
    "am", "vs", "mr", "ms", "dr", "us", "uk", "ai", "it", "hr", "fy", "rs",
    "st", "nd", "rd", "th", "eu", "pe", "ip", "id", "cf", "re", "ok",
}

# Signs of failed font decoding:
#   (cid:N)                  pdfplumber's raw code for a glyph it can't map
#   U+0300-U+04FF            combining marks, Greek and Cyrillic: the broken
#                            TCS font lands here ("ϰ", "й", "͘"); real English
#                            annual reports essentially never use them
#   U+0F00-U+0FFF            Tibetan block, where the broken rupee "༤" lands
#   private use, U+FFFD, control characters
GARBAGE = re.compile(r"\(cid:\d+\)|[̀-ӿༀ-࿿-�\u0000-\u0008]")


def text_quality(texts: list[str]) -> tuple[int, float]:
    """(garbage glyph count, % of words that are fragments) over many pages."""
    joined = "\n".join(texts)
    words = re.findall(r"[A-Za-z]+", joined)
    fragments = [w for w in words if len(w) <= 2 and w.lower() not in REAL_SHORT_WORDS]
    return len(GARBAGE.findall(joined)), 100 * len(fragments) / max(len(words), 1)


# ============================== Main ==============================

def page_count(path: Path) -> int:
    import pymupdf

    with pymupdf.open(path) as doc:
        return doc.page_count


def main():
    truth = json.loads((HERE / "ground_truth.json").read_text(encoding="utf-8"))["rows"]
    docs = sorted({row["doc"] for row in truth})

    results = {}
    for reader_name, read in READERS.items():
        print(f"Running {reader_name} ...", flush=True)
        found = total = intact = rows_total = 0
        failures: list[str] = []
        sample_texts: list[str] = []
        sample_pages = 0
        seconds = 0.0

        for doc in docs:
            path = REPORTS / doc
            doc_rows = [r for r in truth if r["doc"] == doc]
            key_pages = sorted({r["page"] for r in doc_rows})

            # Accuracy on the answer-key pages.
            texts = read(path, key_pages)
            for page in key_pages:
                f, t, i, n, fails = score_page_rows(texts[page], [r for r in doc_rows if r["page"] == page])
                found, total, intact, rows_total = found + f, total + t, intact + i, rows_total + n
                failures += [f"{doc.split('_')[0].upper()} {x}" for x in fails]

            # Quality and speed on a sample spread across the whole report.
            sample = list(range(1, page_count(path) + 1, SAMPLE_STEP))
            start = time.perf_counter()
            sample_texts += read(path, sample).values()
            seconds += time.perf_counter() - start
            sample_pages += len(sample)

        garbage, fragmented = text_quality(sample_texts)
        results[reader_name] = {
            "number_accuracy": 100 * found / total,
            "numbers_found": f"{found}/{total}",
            "row_integrity": 100 * intact / rows_total,
            "rows_intact": f"{intact}/{rows_total}",
            "garbage_glyphs": garbage,
            "fragmented_words_pct": fragmented,
            "seconds_per_page": seconds / sample_pages,
            "sample_pages": sample_pages,
            "failures": failures,
        }
        r = results[reader_name]
        print(
            f"  numbers {r['numbers_found']}  rows {r['rows_intact']}  garbage {garbage}  "
            f"fragmented {fragmented:.2f}%  {r['seconds_per_page']:.3f}s/page"
        )

    (HERE / "results.json").write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    write_markdown(results)
    print(f"\nWrote {HERE / 'results.md'}")


def write_markdown(results: dict):
    """Human-readable results table plus example failures per reader."""
    sample_pages = next(iter(results.values()))["sample_pages"]
    lines = [
        "# PDF reader comparison",
        "",
        "Generated by `compare.py`. Answer key: `ground_truth.json` "
        "(4 pages of TCS and Infosys FY25 annual reports, read from page images).",
        "",
        f"Garbage, fragmentation and speed are measured on {sample_pages} pages sampled across both reports.",
        "",
        "| Reader | Number accuracy | Row integrity | Garbage glyphs | Fragmented words | Seconds/page |",
        "|---|---|---|---|---|---|",
    ]
    for name, r in results.items():
        lines.append(
            f"| {name} | {r['number_accuracy']:.1f}% ({r['numbers_found']}) | "
            f"{r['row_integrity']:.1f}% ({r['rows_intact']}) | {r['garbage_glyphs']} | "
            f"{r['fragmented_words_pct']:.2f}% | {r['seconds_per_page']:.3f} |"
        )
    lines += ["", "## Example failures (first 8 per reader)", ""]
    for name, r in results.items():
        lines.append(f"**{name}**: {len(r['failures'])} rows with missing numbers")
        lines += [f"- {f}" for f in r["failures"][:8]]
        lines.append("")
    (HERE / "results.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
