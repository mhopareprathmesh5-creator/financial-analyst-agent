"""Tests for rag/keyword_search.py and the search modes in rag/store.py.

PURPOSE: prove BM25 finds chunks by exact words, that Reciprocal Rank Fusion
merges two ranked lists correctly, and that RETRIEVAL_MODE switches search.
"""

import pytest
from langchain_core.documents import Document

import config
from rag import store
from rag.keyword_search import BM25Index, rrf_merge, tokenize


def doc(text: str, page: int) -> Document:
    return Document(page_content=text, metadata={"source": "r.pdf", "page": page})


def test_tokenize_keeps_numbers_whole_and_drops_stopwords():
    assert tokenize("What was the Revenue from operations? 2,55,324 and 134.19") == [
        "revenue", "operations", "2,55,324", "134.19",
    ]


def test_bm25_ranks_the_chunk_with_the_rare_exact_term_first():
    docs = [
        doc("The company had a strong year with growth across markets.", 1),
        doc("Employee attrition in IT services was 13.3% for the year.", 2),
        doc("The company invested in growth and talent.", 3),
    ]
    results = BM25Index(docs).search("What was the attrition rate?", k=3)
    assert results[0].metadata["page"] == 2


def test_bm25_leaves_out_chunks_sharing_no_words():
    docs = [doc("Revenue from operations 2,55,324", 1), doc("Board of Directors", 2)]
    assert [d.metadata["page"] for d in BM25Index(docs).search("revenue", k=5)] == [1]


def test_rrf_rewards_chunks_ranked_high_by_both_lists():
    a, b, c = doc("a", 1), doc("b", 2), doc("c", 3)
    vector = [a, b, c]      # b is 2nd here...
    keyword = [b, c, a]     # ...and 1st here, so b wins overall
    merged = rrf_merge([vector, keyword], k=3, rrf_k=60)
    assert [d.page_content for d in merged] == ["b", "a", "c"]


def test_rrf_matches_the_same_chunk_from_different_lists():
    # Same text and page but separate objects (as FAISS and BM25 return them):
    # they must be merged into one result, not listed twice.
    merged = rrf_merge([[doc("x", 1)], [doc("x", 1)]], k=5)
    assert len(merged) == 1


@pytest.mark.usefixtures("index_dir", "fake_pdf")
@pytest.mark.parametrize("mode", ["vector", "bm25", "hybrid"])
def test_every_search_mode_returns_this_chats_chunks(monkeypatch, mode):
    monkeypatch.setattr(config, "RETRIEVAL_MODE", mode)
    store.ingest_pdf(b"Revenue was 100 crore.\nStatutory auditors are B S R & Co.", "t-a", "r.pdf")

    results = store.search("t-a", "statutory auditors", k=2)

    assert results and all(d.metadata["source"] == "r.pdf" for d in results)
    if mode != "vector":  # fake embeddings carry no meaning, so only keyword modes can be checked
        assert results[0].metadata["page"] == 2


@pytest.mark.usefixtures("index_dir", "fake_pdf")
def test_unknown_mode_is_rejected(monkeypatch):
    monkeypatch.setattr(config, "RETRIEVAL_MODE", "magic")
    store.ingest_pdf(b"Revenue was 100 crore.", "t-a", "r.pdf")
    with pytest.raises(ValueError, match="RETRIEVAL_MODE"):
        store.search("t-a", "revenue")


@pytest.mark.usefixtures("index_dir", "fake_pdf")
def test_keyword_index_is_rebuilt_after_a_new_upload(monkeypatch):
    monkeypatch.setattr(config, "RETRIEVAL_MODE", "bm25")
    store.ingest_pdf(b"Revenue was 100 crore.", "t-a", "a.pdf")
    store.search("t-a", "revenue")  # builds and caches the keyword index
    store.ingest_pdf(b"Attrition was 13.3%.", "t-a", "b.pdf")

    assert store.search("t-a", "attrition")[0].metadata["source"] == "b.pdf"
