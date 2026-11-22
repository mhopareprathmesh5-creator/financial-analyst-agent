"""Central settings for the app.

PURPOSE: the single place for every setting (which model, chunk size, how many
search results, where data is saved). Every other file reads from here instead
of hardcoding values.

Every value can be overridden with an environment variable. The eval harness
relies on this to run experiments (different models, chunk sizes, top-k)
without touching code, e.g. `CHUNK_SIZE=500 python -m evals.run_evals`.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Read the .env file and put its values (GOOGLE_API_KEY, ALPHA_VANTAGE_API_KEY,
# LangSmith settings...) into environment variables, so os.getenv() can see them.
load_dotenv()

# Absolute path of the project folder (the folder this file lives in).
# Building other paths from this means the app works no matter which folder
# you start it from.
PROJECT_ROOT = Path(__file__).resolve().parent

# How each setting below works:
#   os.getenv("NAME", default)  -> use the environment variable NAME if it is
#                                  set, otherwise fall back to the default.
# Environment variables are always strings, so numbers are wrapped in int().

# ---------------- Models ----------------
# The Gemini model that chats and decides which tools to call.
CHAT_MODEL = os.getenv("CHAT_MODEL", "gemini-3.1-flash-lite-preview")
# The Hugging Face model that turns text into vectors (embeddings) for search.
# It is downloaded once (~130 MB) and then runs locally on the CPU: free, no
# rate limits, works offline, and report text never leaves the machine.
# (Gemini embeddings hit the free tier's 100 requests/min limit on a single
# annual report; Finding F7 in CLAUDE.md.)
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
# Hugging Face access token, used only to authenticate the model download
# (faster downloads, no "unauthenticated" warning). bge-small is a public
# model, so None also works. Read from HUGGINGFACEHUB_API_TOKEN, falling back
# to HF_TOKEN, the name Hugging Face's own tools use.
HF_TOKEN = os.getenv("HUGGINGFACEHUB_API_TOKEN") or os.getenv("HF_TOKEN")

# ---------------- Retrieval ----------------
# PDFs are cut into chunks of about this many characters before embedding.
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
# Neighbouring chunks share this many characters, so a sentence that falls on
# a chunk boundary still appears whole in at least one chunk.
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))
# How many of the best-matching chunks a search returns to the LLM.
TOP_K = int(os.getenv("TOP_K", "4"))
# Put each page's heading (e.g. "Consolidated Statement of Profit and Loss")
# at the start of every chunk from that page, so a chunk from the middle of a
# table still says which table it belongs to. On by default since the
# retrieval eval showed it helps (Finding F11: hit@1 2.7% -> 13.5%).
CHUNK_HEADINGS = os.getenv("CHUNK_HEADINGS", "1") == "1"
# How search finds chunks (Phase B experiment 2):
#   "vector"  meaning-based search with embeddings (the original setup)
#   "bm25"    keyword search: scores chunks by the question's exact words
#   "hybrid"  both, merged with Reciprocal Rank Fusion
# Default is hybrid: the only mode never the worst on both the report's own
# wording and users' wording (Findings F12, F13).
RETRIEVAL_MODE = os.getenv("RETRIEVAL_MODE", "hybrid")
# In hybrid mode, how many candidates each search contributes before merging.
HYBRID_CANDIDATES = int(os.getenv("HYBRID_CANDIDATES", "20"))
# Reciprocal Rank Fusion constant: a chunk's merged score is the sum of
# 1 / (RRF_K + rank) over both searches. 60 is the standard value from the
# original RRF paper; it stops a single #1 rank from dominating.
RRF_K = int(os.getenv("RRF_K", "60"))
# Query rewriting (Phase B experiment 3): before searching, an LLM rewrites
# the question into annual-report terminology this many times, and every
# version is searched; results are merged with RRF. 0 = off. Targets the
# vocabulary mismatch in Finding F13 ("sales" vs "revenue from operations").
QUERY_REWRITES = int(os.getenv("QUERY_REWRITES", "0"))
# The model that writes the rewrites (a small, fast one is enough).
REWRITE_MODEL = os.getenv("REWRITE_MODEL", CHAT_MODEL)

# ---------------- Storage ----------------
# SQLite file where LangGraph saves every conversation (chat memory).
DB_PATH = Path(os.getenv("DB_PATH", PROJECT_ROOT / "chatbot.db"))
# Folder where each chat's PDF search index is saved.
INDEX_DIR = Path(os.getenv("INDEX_DIR", PROJECT_ROOT / "indexes"))
