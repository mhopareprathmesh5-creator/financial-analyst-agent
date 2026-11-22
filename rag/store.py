"""Per-chat PDF indexes, saved to disk so they survive app restarts.

PURPOSE: everything to do with uploaded PDFs. It reads a PDF page by page,
repairs broken-font text, splits it into chunks, embeds them into a FAISS
index, saves that index to disk, and searches it when the agent asks a
question.

PDF reading uses pdfplumber + rag/text_repair.py. This was chosen by
measurement (experiments/pdf_readers/, Finding F2 in CLAUDE.md): it read
164/164 numbers of a hand-verified answer key correctly, versus 109/164 for
the pypdf loader we used before.

Each chat has its own index, so one chat can never search another chat's
documents. Uploading a second PDF adds to the index; uploading the same PDF
again is detected by its SHA-256 fingerprint and skipped.

Embeddings come from a local Hugging Face model (config.EMBEDDING_MODEL,
BAAI/bge-small-en-v1.5), run on the CPU with sentence-transformers.

Layout on disk, one folder per embedding model, then one per chat thread:

    indexes/<model>/<thread_id>/index.faiss      FAISS vectors
    indexes/<model>/<thread_id>/index.pkl        chunk texts + metadata
    indexes/<model>/<thread_id>/documents.json   which PDFs are in this index

e.g. indexes/BAAI__bge-small-en-v1.5/3f2a.../. Vectors from different models
can't be compared, so each model gets its own folder: switching models never
mixes them, and indexes from different models can sit side by side.

Functions in this file:
    get_embeddings()   load the local embedding model (once)
    _thread_dir()      folder path for a chat's index (with a safety check)
    list_documents()   which PDFs a chat has
    _load_pages()      PDF bytes -> list of pages with (repaired) text
    load_store()       load a chat's index from memory or disk
    ingest_pdf()       add a new PDF to a chat's index (the main upload function)
    search()           find the best-matching chunks for a question
"""

# Lets us write type hints like "FAISS | None" on Python 3.10.
from __future__ import annotations

import hashlib  # SHA-256 fingerprints, to detect duplicate uploads
import io  # wrap bytes as a file-like object, so pdfplumber can read from memory
import json  # read/write documents.json
import re  # regular expression to validate thread ids
from functools import lru_cache  # cache a function's result after the first call
from pathlib import Path
from typing import Callable

import pdfplumber
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

import config
from rag.keyword_search import BM25Index, rrf_merge
from rag.text_repair import repair_text

# Optional progress callback: called as on_progress(fraction_done, message),
# e.g. on_progress(0.25, "Reading page 84 of 336"). The UI uses it to show a
# progress bar; tests and scripts can leave it out.
ProgressCallback = Callable[[float, str], None]


def _no_progress(fraction: float, message: str) -> None:
    """Default callback that ignores progress updates."""

# Indexes that are already loaded, keyed by their folder path (which includes
# the embedding model and the thread id). Loading from disk is slow, so after
# the first search in a chat we keep its index in memory and reuse it for
# every later question.
_STORE_CACHE: dict[str, FAISS] = {}

# Keyword (BM25) indexes, same keys as _STORE_CACHE. Built from the FAISS
# index's chunks on first use; cheap to rebuild, so never saved to disk.
_BM25_CACHE: dict[str, BM25Index] = {}

# Allowed thread ids: only letters, digits, "_" and "-", 1 to 64 characters.
# UUIDs like "3f2a91bc-..." pass; something like "../secrets" fails.
_SAFE_THREAD_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


# BGE models were trained with this instruction in front of search queries
# (but not in front of the passages being searched). Adding it to questions
# only is the model authors' recommended usage for retrieval.
BGE_QUERY_INSTRUCTION = "Represent this sentence for searching relevant passages: "


@lru_cache(maxsize=1)
def get_embeddings() -> Embeddings:
    """Load the local Hugging Face embedding model (BAAI/bge-small-en-v1.5).

    The first call downloads the model (~130 MB) into the Hugging Face cache
    folder; after that it loads from disk and runs offline on the CPU.

    @lru_cache means this runs only once; every later call returns the same
    loaded model instead of loading it again (loading takes a few seconds).

    The import is inside the function so that tests (which use fake
    embeddings) never load PyTorch or the model.
    """
    from langchain_huggingface import HuggingFaceEmbeddings

    # Settings shared by documents and queries:
    #   normalize_embeddings=True scales every vector to length 1. Then
    #   FAISS's default distance (L2) ranks results exactly like cosine
    #   similarity, which is what BGE was trained for.
    normalise = {"normalize_embeddings": True}

    return HuggingFaceEmbeddings(
        model_name=config.EMBEDDING_MODEL,
        # Passed to sentence-transformers when loading the model:
        #   device="cpu"  run on the processor (no graphics card needed)
        #   token         Hugging Face access token, used for the download
        model_kwargs={"device": "cpu", "token": config.HF_TOKEN},
        # Used when embedding document chunks (at upload): plain text.
        encode_kwargs=normalise,
        # Used when embedding a question (at search): with BGE's instruction.
        query_encode_kwargs={**normalise, "prompt": BGE_QUERY_INSTRUCTION},
    )


def _model_folder_name() -> str:
    """Folder-safe name for the embedding model:
    "BAAI/bge-small-en-v1.5" -> "BAAI__bge-small-en-v1.5"."""
    return config.EMBEDDING_MODEL.replace("/", "__")


def _thread_dir(thread_id: str) -> Path:
    """Return the folder where this chat's index lives:
    indexes/<model>/<thread_id>.

    The leading "_" means it's a private helper, only used inside this file.
    """
    thread_id = str(thread_id)
    # The thread id becomes a folder name, so reject anything that could
    # escape the index directory (e.g. "../other"). This is called a
    # "path traversal" attack.
    if not _SAFE_THREAD_ID.match(thread_id):
        raise ValueError(f"Invalid thread id: {thread_id!r}")
    # In pathlib, "/" joins paths: INDEX_DIR / "a" / "b" -> indexes/a/b
    return config.INDEX_DIR / _model_folder_name() / thread_id


def list_documents(thread_id: str) -> list[dict]:
    """Return the PDFs indexed for this chat, oldest first.

    Reads indexes/<thread_id>/documents.json, which looks like:
        [{"filename": "tcs.pdf", "sha256": "ab12...", "pages": 300, "chunks": 1200}]
    Returns [] if the chat has no PDFs yet.
    """
    path = _thread_dir(thread_id) / "documents.json"
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def page_heading(text: str, max_lines: int = 2, max_chars: int = 150) -> str:
    """The page's heading: its first lines, which in annual reports are the
    section name and the page title, e.g.
        "Consolidated Financial Statements 2024-25 178 | Consolidated Balance Sheet"

    Lines with fewer than 2 words are skipped: on rotated (landscape) pages
    pdfplumber reads the vertical margin text one word per line ("Infosys",
    "Integrated", "Annual"), which isn't a heading.
    """
    lines = [line.strip() for line in text.splitlines() if len(line.split()) >= 2]
    return " | ".join(lines[:max_lines])[:max_chars]


def _load_pages(
    file_bytes: bytes,
    filename: str,
    on_progress: ProgressCallback = _no_progress,
) -> tuple[list[Document], int]:
    """Extract and repair the text of each page of a PDF.

    Returns two things:
        pages        a list of Documents, one per page that has text
        total pages  how many pages the PDF has, including empty ones

    Calls on_progress after each page, because a 300+ page annual report
    takes about 2 minutes to read and the UI should show it's not frozen.
    """
    pages = []
    # io.BytesIO makes the uploaded bytes look like an open file, so
    # pdfplumber can read straight from memory (no temporary file needed).
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        total = len(pdf.pages)
        for number, page in enumerate(pdf.pages, start=1):
            # extract_text() rebuilds lines from character positions, which
            # keeps a table row's label and numbers together on one line.
            # repair_text() then fixes broken-font glyphs (ϰ -> 4, ...).
            text = repair_text(page.extract_text() or "")
            # Skip pages with no text (blank pages, or images without text).
            if text.strip():
                pages.append(
                    Document(
                        page_content=text,
                        # `number` starts at 1, so citations match the page
                        # number a PDF viewer shows. The heading travels with
                        # every chunk cut from this page (see ingest_pdf).
                        metadata={"source": filename, "page": number, "heading": page_heading(text)},
                    )
                )
            on_progress(number / total, f"Reading page {number} of {total}")

            # pdfplumber caches every character of every page it reads.
            # Clearing it keeps memory flat on a 300+ page report.
            page.flush_cache()

    return pages, total


def load_store(thread_id: str, embeddings: Embeddings | None = None) -> FAISS | None:
    """Return the FAISS index for this chat, or None if no PDF was uploaded.

    Looks in three places, in order:
        1. memory (_STORE_CACHE)  fastest, used after the first load
        2. disk (indexes/<id>/)   e.g. right after the app restarts
        3. nowhere                this chat has no PDF -> None

    `embeddings` can be passed in by tests; normally it's None and we use the
    local Hugging Face model.
    """
    folder = _thread_dir(thread_id)
    # Keyed by folder, so an index built with a different embedding model is
    # never served from the cache by mistake.
    key = str(folder)
    if key in _STORE_CACHE:
        return _STORE_CACHE[key]

    if not (folder / "index.faiss").exists():
        return None

    store = FAISS.load_local(
        str(folder),
        # The same embeddings model must be used to search as was used to
        # build the index, otherwise the vectors wouldn't be comparable.
        embeddings or get_embeddings(),
        # FAISS saves part of the index with Python's pickle format, which
        # could run malicious code if someone swapped in a bad file. LangChain
        # makes us confirm we trust the file. Safe here: we only ever load
        # index files this app wrote itself.
        allow_dangerous_deserialization=True,
    )
    _STORE_CACHE[key] = store  # remember it for the next question
    return store


def ingest_pdf(
    file_bytes: bytes,
    thread_id: str,
    filename: str,
    embeddings: Embeddings | None = None,
    on_progress: ProgressCallback = _no_progress,
) -> dict:
    """Add a PDF to this chat's index and save it to disk.

    Uploading the same file twice is a no-op; uploading a different file adds
    to the index instead of replacing it.

    Steps:
        1. Fingerprint the file; stop if this chat already has it
        2. Extract and repair text page by page
        3. Split pages into overlapping chunks
        4. Embed the chunks into the chat's FAISS index (new or existing)
        5. Save the index and the documents list to disk

    on_progress receives updates during the slow steps (2 and 4), for the UI.

    Returns a summary for the UI, e.g.
        {"filename": "tcs.pdf", "sha256": "...", "pages": 300, "chunks": 1200,
         "already_indexed": False}
    """
    if not file_bytes:
        raise ValueError("The uploaded file is empty.")

    key = str(thread_id)

    # Step 1: SHA-256 turns the file's bytes into a 64-character fingerprint.
    # Identical files always give the same fingerprint, even if renamed, so
    # we can tell whether this exact PDF was already uploaded to this chat.
    digest = hashlib.sha256(file_bytes).hexdigest()
    documents = list_documents(key)
    for doc in documents:
        if doc["sha256"] == digest:
            # Already indexed: return its summary without re-embedding
            # (embedding costs API calls and time).
            return {**doc, "already_indexed": True}

    # Step 2: extract and repair text.
    try:
        pages, total_pages = _load_pages(file_bytes, filename, on_progress)
    except Exception as e:
        # pdfplumber raises its own error types for corrupt or non-PDF
        # files. Turn them into a ValueError with a clear message, which the
        # UI shows to the user instead of crashing.
        raise ValueError(f"Could not read {filename}. Is it a valid PDF? ({e})") from e
    if not pages:
        # Scanned PDFs are just images of pages, so there's no text to read.
        raise ValueError(
            f"No text could be extracted from {filename}. It may be a scanned PDF."
        )

    # Step 3: split into chunks. The splitter tries the separators in order:
    # first paragraph breaks ("\n\n"), then line breaks, then spaces, and
    # only as a last resort cuts in the middle of a word ("").
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=config.CHUNK_SIZE,
        chunk_overlap=config.CHUNK_OVERLAP,
        separators=["\n\n", "\n", " ", ""],
    )
    # Each chunk keeps its page's metadata (source, page number, heading).
    chunks = splitter.split_documents(pages)

    # Step 3b (optional, config.CHUNK_HEADINGS): start every chunk with its
    # page heading. Without it, a chunk cut from the middle of the P&L is just
    # rows of numbers and can't be told apart from the standalone P&L or a
    # subsidiary table (Finding F10). The heading is embedded with the chunk,
    # and the LLM sees it too.
    if config.CHUNK_HEADINGS:
        for chunk in chunks:
            heading = chunk.metadata.get("heading", "")
            if heading:
                chunk.page_content = f"[{heading}]\n{chunk.page_content}"

    # Step 4: embed every chunk with the local model; the other slow step,
    # so tell the UI what's happening.
    on_progress(1.0, f"Embedding {len(chunks)} chunks…")
    embeddings = embeddings or get_embeddings()
    store = load_store(key, embeddings)
    if store is None:
        # First PDF in this chat: build a new index.
        store = FAISS.from_documents(chunks, embeddings)
    else:
        # Chat already has PDFs: add to the existing index (the old code
        # replaced it, losing the first PDF).
        store.add_documents(chunks)

    # Step 5: save to disk so the index survives an app restart.
    folder = _thread_dir(key)
    folder.mkdir(parents=True, exist_ok=True)  # create indexes/<model>/<id>/ if needed
    store.save_local(str(folder))  # writes index.faiss and index.pkl

    # Record this PDF in documents.json (shown in the sidebar, and used for
    # the duplicate check in step 1 next time).
    entry = {
        "filename": filename,
        "sha256": digest,
        "pages": total_pages,
        "chunks": len(chunks),
    }
    documents.append(entry)
    (folder / "documents.json").write_text(
        json.dumps(documents, indent=2), encoding="utf-8"
    )

    _STORE_CACHE[str(folder)] = store
    # The chunk list changed, so the keyword index must be rebuilt next time.
    _BM25_CACHE.pop(str(folder), None)
    # {**entry, ...} copies all keys of entry and adds "already_indexed".
    return {**entry, "already_indexed": False}


def search(
    thread_id: str,
    query: str,
    k: int | None = None,
    embeddings: Embeddings | None = None,
) -> list[Document]:
    """Return the top-k passages for the query, from this chat's PDFs only.

    How depends on config.RETRIEVAL_MODE:
        "vector"  FAISS embeds the query and returns the k chunks whose
                  vectors are closest (most similar meaning)
        "bm25"    the k chunks that best match the query's exact words
        "hybrid"  both searches return HYBRID_CANDIDATES chunks each; the two
                  lists are merged with Reciprocal Rank Fusion

    With config.QUERY_REWRITES > 0, an LLM first rewrites the query into
    annual-report terminology (rag/query_rewrite.py). The original query and
    every rewrite are searched, and all the ranked lists are merged with RRF.

    Each result is a Document with .page_content (the text) and .metadata
    ({"source": ..., "page": ..., "heading": ...}). Returns [] if this chat
    has no PDF.
    """
    store = load_store(thread_id, embeddings)
    if store is None:
        return []
    k = k or config.TOP_K
    mode = config.RETRIEVAL_MODE
    if mode not in ("vector", "bm25", "hybrid"):
        raise ValueError(f"Unknown RETRIEVAL_MODE {mode!r}; use vector, bm25 or hybrid")

    queries = [query]
    if config.QUERY_REWRITES > 0:
        # Imported here so the app doesn't need the rewriter unless it's on.
        from rag import query_rewrite

        queries += query_rewrite.rewrite(query, config.QUERY_REWRITES)

    # One query, one search mode: return directly (no merging needed).
    if len(queries) == 1 and mode != "hybrid":
        return _ranked_lists(store, thread_id, query, k, mode)[0]

    # Otherwise merge. Take more candidates than needed from each list, so a
    # chunk ranked e.g. 15th by one list can still win if others rank it high.
    n = max(k, config.HYBRID_CANDIDATES)
    lists = [lst for q in queries for lst in _ranked_lists(store, thread_id, q, n, mode)]
    return rrf_merge(lists, k=k, rrf_k=config.RRF_K)


def _ranked_lists(store: FAISS, thread_id: str, query: str, n: int, mode: str) -> list[list[Document]]:
    """The ranked result list(s) for one query: one list for "vector" or
    "bm25", two (vector + keyword) for "hybrid"."""
    lists = []
    if mode in ("vector", "hybrid"):
        lists.append(store.similarity_search(query, k=n))
    if mode in ("bm25", "hybrid"):
        lists.append(_bm25_index(thread_id, store).search(query, n))
    return lists


def _bm25_index(thread_id: str, store: FAISS) -> BM25Index:
    """The keyword index for this chat, built from the same chunks as its
    FAISS index the first time it's needed, then cached."""
    key = str(_thread_dir(thread_id))
    if key not in _BM25_CACHE:
        # FAISS keeps every chunk in its "docstore"; index_to_docstore_id
        # lists their ids in insertion order.
        docs = [store.docstore.search(doc_id) for doc_id in store.index_to_docstore_id.values()]
        _BM25_CACHE[key] = BM25Index(docs)
    return _BM25_CACHE[key]
