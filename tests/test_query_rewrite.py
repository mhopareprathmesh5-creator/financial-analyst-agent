"""Tests for rag/query_rewrite.py and rewriting inside rag/store.search.

PURPOSE: prove the LLM reply is parsed into clean queries, that rewrites are
cached (so eval reruns never call Gemini twice), and that search really uses
the rewrites. A fake LLM stands in for Gemini: no API calls.
"""

import pytest
from langchain_core.language_models import FakeListChatModel

import config
from rag import query_rewrite, store


def fake_llm(reply: str):
    return FakeListChatModel(responses=[reply])


def test_reply_is_parsed_into_clean_queries():
    reply = "1. consolidated revenue from operations\n- statement of profit and loss\n\n\"revenue FY2025\"\nextra line"
    queries = query_rewrite.rewrite("total sales?", 3, llm=fake_llm(reply))
    assert queries == ["consolidated revenue from operations", "statement of profit and loss", "revenue FY2025"]


def test_zero_rewrites_never_calls_the_llm():
    class Exploding:
        def invoke(self, *_):
            raise AssertionError("LLM must not be called")

    assert query_rewrite.rewrite("q?", 0, llm=Exploding()) == []


def test_cache_means_the_llm_is_called_once(tmp_path, monkeypatch):
    monkeypatch.setattr(query_rewrite, "CACHE", query_rewrite.RewriteCache(tmp_path / "rw.json"))
    first = query_rewrite.rewrite("total sales?", 2, llm=fake_llm("a\nb"))
    # A second call with an LLM that would answer differently still returns the cached rewrites.
    second = query_rewrite.rewrite("total sales?", 2, llm=fake_llm("x\ny"))
    assert first == second == ["a", "b"]
    # The cache survives a "restart" (reloaded from the file).
    assert query_rewrite.RewriteCache(tmp_path / "rw.json").get("total sales?", 2) == ["a", "b"]


def test_prompt_contains_no_dataset_term_mappings():
    """Honest-eval rule: the prompt must not teach the answers to our own
    paraphrase questions (e.g. 'sales' -> 'revenue from operations')."""
    prompt = query_rewrite.PROMPT.lower()
    for leaked in ["revenue from operations", "statutory auditor", "chief financial officer", "attrition"]:
        assert leaked not in prompt


@pytest.mark.usefixtures("index_dir", "fake_pdf")
def test_search_uses_the_rewrites(monkeypatch):
    """The user's words ("finance chief") match nothing, but the rewrite
    ("chief financial officer") does, so search must find the CFO page."""
    monkeypatch.setattr(config, "RETRIEVAL_MODE", "bm25")
    monkeypatch.setattr(config, "QUERY_REWRITES", 1)
    monkeypatch.setattr(query_rewrite, "rewrite", lambda q, n: ["chief financial officer"])
    store.ingest_pdf(b"Revenue was 100 crore.\nSamir Seksaria, Chief Financial Officer", "t-a", "r.pdf")

    results = store.search("t-a", "Who is the finance boss?", k=2)

    assert results[0].metadata["page"] == 2
