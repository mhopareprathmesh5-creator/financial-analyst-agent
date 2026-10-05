"""Shared test setup (pytest loads this file automatically).

PURPOSE: fixtures that make tests offline, free and fast: fake embeddings
instead of the Gemini API, a temporary index folder instead of the real one,
and fake PDFs so tests don't need real PDF files.

These are ordinary software tests (does the code work?). The LLM evals in
evals/ are separate and test whether the agent gives good answers.

What's a fixture? A function marked @pytest.fixture that prepares something
a test needs. A test asks for it by name (as a parameter, or with
@pytest.mark.usefixtures) and pytest runs it before the test.
"""

import pytest
from langchain_core.documents import Document
from langchain_core.embeddings import DeterministicFakeEmbedding

import config
from rag import store


@pytest.fixture
def fake_embeddings():
    """Embeddings that turn text into vectors without calling any API.

    "Deterministic" means the same text always gives the same vector, so
    results are repeatable. The vectors carry no real meaning, which is fine:
    these tests check storage logic, not search quality.
    """
    return DeterministicFakeEmbedding(size=32)


@pytest.fixture
def index_dir(tmp_path, monkeypatch, fake_embeddings):
    """Isolated index folder and fake embeddings, so tests never touch real
    indexes or call the embeddings API.

    tmp_path     a fresh empty folder pytest creates for each test (built in)
    monkeypatch  temporarily replaces values; pytest undoes it after the test
    """
    # Point the app at a temporary folder instead of the real indexes/.
    monkeypatch.setattr(config, "INDEX_DIR", tmp_path / "indexes")
    # Make store.py use fake embeddings instead of Gemini.
    monkeypatch.setattr(store, "get_embeddings", lambda: fake_embeddings)
    # Start each test with an empty memory cache, so tests don't affect each other.
    store._STORE_CACHE.clear()
    yield tmp_path / "indexes"  # the test runs here
    store._STORE_CACHE.clear()  # clean up after the test


@pytest.fixture
def fake_pdf(monkeypatch):
    """Skip real PDF parsing: the bytes of a "PDF" are decoded as its page texts,
    one page per line.

    So in tests, b"Page one text\\nPage two text" acts like a 2-page PDF.
    This lets us test everything after PDF reading without real PDF files.
    """

    def load_pages(file_bytes, filename):
        texts = file_bytes.decode().splitlines()
        pages = [
            Document(page_content=text, metadata={"source": filename, "page": i + 1})
            for i, text in enumerate(texts)
        ]
        return pages, len(texts)

    # Replace the real _load_pages with the fake one for this test.
    monkeypatch.setattr(store, "_load_pages", load_pages)
