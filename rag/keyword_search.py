"""Keyword search (BM25) and Reciprocal Rank Fusion, for hybrid retrieval.

PURPOSE: vector search finds chunks with similar *meaning*, but it is weak at
exact terms. The retrieval baseline (Finding F10) missed ~70% of questions,
many of them worded with the report's own terms: "Revenue from operations",
"statutory auditors", "attrition". BM25 scores chunks by those exact words.
Hybrid search runs both and merges the two ranked lists with RRF.

How BM25 scores a chunk for a question, roughly:
    for each word of the question that appears in the chunk:
        + more if the word is rare across the report ("attrition" counts far
          more than "the" or "company", which are everywhere)
        + more if the word appears several times in the chunk, with
          diminishing returns
        - a little if the chunk is long (long chunks match words by chance)

How Reciprocal Rank Fusion merges two ranked lists:
    score(chunk) = 1 / (RRF_K + rank in list 1) + 1 / (RRF_K + rank in list 2)
    A chunk ranked high by either search scores well; ranked high by both,
    it scores best. Only ranks are used, never raw scores, which is why it
    works even though BM25 and vector scores are on completely different scales.
"""

from __future__ import annotations

import re

from langchain_core.documents import Document
from rank_bm25 import BM25Okapi

# Very common words carry no signal for search; dropping them stops BM25
# from matching chunks just because they contain "the" or "what".
STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "did", "do", "does", "for",
    "from", "had", "has", "have", "how", "in", "is", "it", "its", "much", "of",
    "on", "or", "s", "that", "the", "their", "this", "to", "was", "were", "what",
    "when", "which", "who", "why", "with",
}

# A token is a run of letters/digits; digits may contain , or . inside, so a
# number like 2,55,324 or 134.19 stays one token instead of being split up.
_TOKEN = re.compile(r"[a-z0-9]+(?:[.,][0-9]+)*")


def tokenize(text: str) -> list[str]:
    """Lowercase words and numbers, without stopwords."""
    return [t for t in _TOKEN.findall(text.lower()) if t not in STOPWORDS]


class BM25Index:
    """BM25 over a fixed list of chunks. Building it takes well under a second
    for a whole annual report (~1,500 chunks), so it isn't saved to disk: it is
    rebuilt from the FAISS index's chunks when first needed."""

    def __init__(self, docs: list[Document]):
        self.docs = docs
        tokens = [tokenize(d.page_content) for d in docs]
        # Each chunk's set of words, to check quickly which chunks share at
        # least one word with the question.
        self.token_sets = [set(t) for t in tokens]
        # BM25Okapi is the standard BM25 variant. It needs every chunk as a
        # list of tokens; an empty list would break it, so use a placeholder.
        self.bm25 = BM25Okapi([t or ["<empty>"] for t in tokens])

    def search(self, query: str, k: int) -> list[Document]:
        """The k chunks with the highest BM25 score, best first. Chunks that
        share no word with the question are left out.

        Why not just drop chunks scoring 0: in standard BM25 a word found in
        half or more of all chunks gets zero weight (its "rarity" is log(1)),
        so a chunk can match the question and still score 0. A unit test with
        a tiny corpus caught this.
        """
        query_tokens = tokenize(query)
        wanted = set(query_tokens)
        scores = self.bm25.get_scores(query_tokens)
        matching = [i for i in range(len(self.docs)) if self.token_sets[i] & wanted]
        ranked = sorted(matching, key=lambda i: scores[i], reverse=True)
        return [self.docs[i] for i in ranked[:k]]


def _key(doc: Document) -> tuple:
    """Identify a chunk across the two result lists. Both lists contain the
    same chunks, but as separate Python objects, so compare their content."""
    return (doc.metadata.get("source"), doc.metadata.get("page"), doc.page_content)


def rrf_merge(
    result_lists: list[list[Document]],
    k: int,
    rrf_k: int = 60,
    weights: list[float] | None = None,
) -> list[Document]:
    """Merge several ranked lists into one with Reciprocal Rank Fusion.

    Each list is best-first. A chunk's score is the sum over lists of
    weight / (rrf_k + rank), rank starting at 1. Returns the top k, best first.

    weights (one per list, default all 1.0) let some lists count more. Query
    rewriting uses this to give the user's original question extra say, so
    the rewrites add candidates without drowning it out (Finding F15).
    """
    weights = weights or [1.0] * len(result_lists)
    scores: dict[tuple, float] = {}
    docs: dict[tuple, Document] = {}
    for results, weight in zip(result_lists, weights):
        for rank, doc in enumerate(results, start=1):
            key = _key(doc)
            scores[key] = scores.get(key, 0.0) + weight / (rrf_k + rank)
            docs.setdefault(key, doc)
    best = sorted(scores, key=scores.get, reverse=True)
    return [docs[key] for key in best[:k]]
