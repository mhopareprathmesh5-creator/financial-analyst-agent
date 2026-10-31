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
    assert [p.metadata for p in pages] == [
        {"source": "report.pdf", "page": 1},
        {"source": "report.pdf", "page": 2},
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


@pytest.mark.usefixtures("index_dir")
def test_non_pdf_upload_gives_clear_error():
    with pytest.raises(ValueError, match="valid PDF"):
        store.ingest_pdf(b"this is not a pdf", "thread-a", "notes.pdf")


@pytest.mark.usefixtures("index_dir")
def test_ingest_reads_a_real_pdf_end_to_end():
    store.ingest_pdf(make_pdf(["Revenue from operations 2,55,324"]), "thread-a", "report.pdf")

    results = store.search("thread-a", "revenue")
    assert results[0].metadata == {"source": "report.pdf", "page": 1}
    assert "2,55,324" in results[0].page_content
