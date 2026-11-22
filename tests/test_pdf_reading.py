"""Tests for the real PDF reading path in rag/store.py (pdfplumber + repair).

PURPOSE: the other store tests use fake PDFs; these feed real PDF bytes
(built by pdf_factory.py) through pdfplumber to prove that pages are read
with correct page numbers, blank pages are skipped, progress is reported,
and a file that isn't a PDF gives a clear error instead of a crash.
"""

import pytest

from rag import store
from tests.pdf_factory import make_pdf


def test_pages_are_read_with_one_based_numbers():
    pdf = make_pdf(["Revenue from operations 2,55,324", "Net profit 48,797"])

    pages, total = store._load_pages(pdf, "report.pdf")

    assert total == 2
    # Pages also carry a "heading" (tested separately), so compare source + page only.
    assert [(p.metadata["source"], p.metadata["page"]) for p in pages] == [
        ("report.pdf", 1),
        ("report.pdf", 2),
    ]
    assert "2,55,324" in pages[0].page_content


def test_blank_pages_are_skipped_but_counted():
    pdf = make_pdf(["Page one", "", "Page three"])

    pages, total = store._load_pages(pdf, "report.pdf")

    assert total == 3  # the PDF has 3 pages...
    assert [p.metadata["page"] for p in pages] == [1, 3]  # ...but only 2 have text


def test_progress_is_reported_for_every_page():
    updates = []

    store._load_pages(make_pdf(["a", "b", "c"]), "report.pdf", on_progress=lambda f, m: updates.append((f, m)))

    assert [round(f, 2) for f, _ in updates] == [0.33, 0.67, 1.0]
    assert updates[-1][1] == "Reading page 3 of 3"


def test_page_heading_takes_first_two_real_lines():
    text = "Consolidated Financial Statements 2024-25 178\nConsolidated Balance Sheet\n(₹ crore)\nAssets 1,59,629"
    assert store.page_heading(text) == "Consolidated Financial Statements 2024-25 178 | Consolidated Balance Sheet"


def test_page_heading_skips_one_word_lines_from_rotated_pages():
    # Landscape pages: the vertical margin text comes out one word per line.
    text = "Infosys\nIntegrated\nAnnual\nTurnover rate for permanent employees\nMale Female Total"
    assert store.page_heading(text) == "Turnover rate for permanent employees | Male Female Total"


def test_pages_carry_their_heading():
    pages, _ = store._load_pages(make_pdf(["Consolidated Balance Sheet"]), "report.pdf")
    assert pages[0].metadata["heading"] == "Consolidated Balance Sheet"


@pytest.mark.usefixtures("index_dir")
def test_chunk_headings_switch(monkeypatch):
    """With CHUNK_HEADINGS on, every chunk starts with its page heading, so a
    chunk from the middle of a table still says which table it's from."""
    import config

    monkeypatch.setattr(config, "CHUNK_HEADINGS", True)
    monkeypatch.setattr(config, "CHUNK_SIZE", 40)  # force several chunks per page
    monkeypatch.setattr(config, "CHUNK_OVERLAP", 0)
    store.ingest_pdf(make_pdf(["Consolidated Balance Sheet Total assets 1,59,629 Equity 95,771"]), "t-a", "r.pdf")

    chunks = store.search("t-a", "assets", k=10)
    assert len(chunks) > 1
    assert all(c.page_content.startswith("[Consolidated Balance Sheet") for c in chunks)


@pytest.mark.usefixtures("index_dir")
def test_non_pdf_upload_gives_clear_error():
    with pytest.raises(ValueError, match="valid PDF"):
        store.ingest_pdf(b"this is not a pdf", "thread-a", "notes.pdf")


@pytest.mark.usefixtures("index_dir")
def test_ingest_reads_a_real_pdf_end_to_end():
    store.ingest_pdf(make_pdf(["Revenue from operations 2,55,324"]), "thread-a", "report.pdf")

    results = store.search("thread-a", "revenue")
    assert (results[0].metadata["source"], results[0].metadata["page"]) == ("report.pdf", 1)
    assert "2,55,324" in results[0].page_content
