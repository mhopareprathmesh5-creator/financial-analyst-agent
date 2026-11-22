"""Query rewriting: turn a user's question into annual-report terminology.

PURPOSE: users and annual reports use different words for the same thing
("total sales" vs "revenue from operations", "finance chief" vs "Chief
Financial Officer"). On questions in users' own wording, every search mode
found the right page in the top 4 only 14–21% of the time (Finding F13).
Here an LLM writes a few alternative search queries in the report's own
language; rag/store.py searches with all of them and merges the results.

Honest-eval rule: the prompt gives the LLM general instructions only, never
term mappings taken from the golden dataset. Putting "sales -> revenue from
operations" in the prompt would teach it the answers to our own exam and make
the eval score meaningless.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

from langchain_core.language_models import BaseChatModel

import config

# Bump this when the prompt changes, so cached rewrites from the old prompt
# are never reused for the new one.
PROMPT_VERSION = "v1"

PROMPT = """You help search a company's annual report (an Indian listed company, \
financial statements under Ind AS). Rewrite the user's question into {n} different \
search queries that use the formal terminology an annual report itself would use \
for the same thing.

Rules:
- Keep the same meaning and the same company, year and scope; don't add facts.
- Use the words that appear in annual reports and financial statements, not casual words.
- Each query on its own line. No numbering, no explanations.

User question: {question}"""


@lru_cache(maxsize=1)
def get_rewriter_llm() -> BaseChatModel:
    """The LLM used for rewriting, created once. Temperature 0 makes the
    rewrites as repeatable as possible, which matters for evals.
    max_retries lets it wait and retry when the free tier's rate limit hits."""
    from langchain_google_genai import ChatGoogleGenerativeAI

    return ChatGoogleGenerativeAI(model=config.REWRITE_MODEL, temperature=0, max_retries=6)


def _parse(text: str, n: int) -> list[str]:
    """Turn the LLM's reply into a clean list of queries: one per line,
    stripped of any numbering or bullets it added anyway."""
    queries = []
    for line in text.splitlines():
        line = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", line).strip().strip('"')
        if line:
            queries.append(line)
    return queries[:n]


def _text_of(reply) -> str:
    """LLM reply content can be a string or a list of blocks (Gemini); get text."""
    content = reply.content
    if isinstance(content, list):
        return "".join(b.get("text", "") for b in content if isinstance(b, dict))
    return str(content)


class RewriteCache:
    """Rewrites saved to a JSON file, keyed by model + prompt version + n +
    question. Eval runs repeat the same questions many times; the cache means
    Gemini is called once per question, not once per run (free-tier limits)."""

    def __init__(self, path: Path):
        self.path = path
        self.data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}

    @staticmethod
    def key(question: str, n: int) -> str:
        return f"{config.REWRITE_MODEL}|{PROMPT_VERSION}|{n}|{question}"

    def get(self, question: str, n: int) -> list[str] | None:
        return self.data.get(self.key(question, n))

    def put(self, question: str, n: int, queries: list[str]):
        self.data[self.key(question, n)] = queries
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, indent=1, ensure_ascii=False), encoding="utf-8")


# Set by the eval runner to a RewriteCache; None in the app (no file cache).
CACHE: RewriteCache | None = None


def rewrite(question: str, n: int, llm: BaseChatModel | None = None) -> list[str]:
    """Return up to n rewrites of the question in annual-report terminology.

    The original question is NOT included; the caller searches with it too.
    `llm` can be passed in by tests (a fake model); normally Gemini is used.
    """
    if n <= 0:
        return []
    if CACHE is not None and (cached := CACHE.get(question, n)) is not None:
        return cached

    reply = (llm or get_rewriter_llm()).invoke(PROMPT.format(n=n, question=question))
    queries = _parse(_text_of(reply), n)

    if CACHE is not None:
        CACHE.put(question, n, queries)
    return queries
