"""Tests for rag/store.py.

PURPOSE: prove the PDF storage fixes work: indexes survive a restart, a
second PDF is added rather than replacing the first, duplicates are skipped,
chats cannot see each other's documents, and unsafe chat ids are rejected.

Run with:  python -m pytest tests/test_store.py -v
"""

import pytest

from rag import store

# Apply these fixtures (from conftest.py) to every test in this file:
# a temporary index folder + fake embeddings, and fake PDFs.
pytestmark = pytest.mark.usefixtures("index_dir", "fake_pdf")

# Fake PDFs (see fake_pdf in conftest.py): each line is one page.
REPORT = b"Revenue was 100 crore.\nNet profit was 20 crore."  # 2 pages
OTHER = b"Employees: 5000."  # 1 page


def test_index_survives_restart():
    """Bug fixed: PDFs used to be lost when the app restarted, because the
    index only lived in memory."""
    store.ingest_pdf(REPORT, "thread-a", "report.pdf")
    store._STORE_CACHE.clear()  # simulate an app restart: memory is wiped

    # The search must still work, which means it was reloaded from disk.
    results = store.search("thread-a", "revenue")
    assert results
    assert store.list_documents("thread-a")[0]["filename"] == "report.pdf"


def test_second_pdf_is_added_not_replaced():
    """Bug fixed: uploading a second PDF used to replace the first one."""
    store.ingest_pdf(REPORT, "thread-a", "report.pdf")
    store.ingest_pdf(OTHER, "thread-a", "hr.pdf")

    # Both PDFs are listed...
    files = {doc["filename"] for doc in store.list_documents("thread-a")}
    assert files == {"report.pdf", "hr.pdf"}
    # ...and both are searchable (k=10 returns all 3 chunks).
    found = {doc.metadata["source"] for doc in store.search("thread-a", "x", k=10)}
    assert found == {"report.pdf", "hr.pdf"}


def test_same_pdf_twice_is_not_reindexed():
    """Uploading the same file again must not embed it twice (wasted API
    calls and duplicate search results)."""
    first = store.ingest_pdf(REPORT, "thread-a", "report.pdf")
    second = store.ingest_pdf(REPORT, "thread-a", "report.pdf")

    assert first["already_indexed"] is False
    assert second["already_indexed"] is True
    assert len(store.list_documents("thread-a")) == 1


def test_chats_cannot_see_each_others_documents():
    """Security: a PDF uploaded in one chat must not be searchable from another."""
    store.ingest_pdf(REPORT, "thread-a", "report.pdf")

    assert store.search("thread-b", "revenue") == []


def test_page_numbers_are_one_based():
    """Citations must use page numbers a reader sees (1, 2, ...), not 0, 1, ..."""
    store.ingest_pdf(REPORT, "thread-a", "report.pdf")

    pages = sorted(doc.metadata["page"] for doc in store.search("thread-a", "x", k=10))
    assert pages == [1, 2]


# parametrize runs this one test 4 times, once with each bad id.
@pytest.mark.parametrize("bad_id", ["../escape", "a/b", "", "a\\b"])
def test_unsafe_thread_ids_are_rejected(bad_id):
    """Security: a thread id like "../escape" must not be able to write
    files outside the indexes folder (path traversal)."""
    with pytest.raises(ValueError):
        store.ingest_pdf(REPORT, bad_id, "report.pdf")


def test_empty_file_is_rejected():
    """An empty upload gives a clear error instead of crashing later."""
    with pytest.raises(ValueError):
        store.ingest_pdf(b"", "thread-a", "report.pdf")
