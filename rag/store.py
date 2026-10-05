"""Per-chat PDF indexes, saved to disk so they survive app restarts.

PURPOSE: everything to do with uploaded PDFs. It reads a PDF page by page,
splits it into chunks, embeds them into a FAISS index, saves that index to
disk, and searches it when the agent asks a question.

Each chat has its own index, so one chat can never search another chat's
documents. Uploading a second PDF adds to the index; uploading the same PDF
again is detected by its SHA-256 fingerprint and skipped.

Layout on disk, one folder per chat thread:

    indexes/<thread_id>/index.faiss      FAISS vectors
    indexes/<thread_id>/index.pkl        chunk texts + metadata
    indexes/<thread_id>/documents.json   which PDFs are in this index

Functions in this file:
    get_embeddings()   create the Gemini embeddings client (once)
    _thread_dir()      folder path for a chat's index (with a safety check)
    list_documents()   which PDFs a chat has
    _load_pages()      PDF bytes -> list of pages with text
    load_store()       load a chat's index from memory or disk
    ingest_pdf()       add a new PDF to a chat's index (the main upload function)
    search()           find the best-matching chunks for a question
"""

# Lets us write type hints like "FAISS | None" on Python 3.10.
from __future__ import annotations

import hashlib  # SHA-256 fingerprints, to detect duplicate uploads
import json  # read/write documents.json
import os  # delete the temporary PDF file
import re  # regular expression to validate thread ids
import tempfile  # temporary file, because PyPDFLoader needs a file path
from functools import lru_cache  # cache a function's result after the first call
from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

import config

# Indexes that are already loaded, keyed by thread id. Loading from disk is
# slow, so after the first search in a chat we keep its index in memory and
# reuse it for every later question.
_STORE_CACHE: dict[str, FAISS] = {}

# Allowed thread ids: only letters, digits, "_" and "-", 1 to 64 characters.
# UUIDs like "3f2a91bc-..." pass; something like "../secrets" fails.
_SAFE_THREAD_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


@lru_cache(maxsize=1)
def get_embeddings() -> Embeddings:
    """Create the Gemini embeddings client.

    @lru_cache means this runs only once; every later call returns the same
    client instead of creating a new one.

    The import is inside the function so that tests (which use fake
    embeddings) never need the Gemini library or an API key.
    """
    from langchain_google_genai import GoogleGenerativeAIEmbeddings

    return GoogleGenerativeAIEmbeddings(model=config.EMBEDDING_MODEL)


def _thread_dir(thread_id: str) -> Path:
    """Return the folder where this chat's index lives: indexes/<thread_id>.

    The leading "_" means it's a private helper, only used inside this file.
    """
    thread_id = str(thread_id)
    # The thread id becomes a folder name, so reject anything that could
    # escape the index directory (e.g. "../other"). This is called a
    # "path traversal" attack.
    if not _SAFE_THREAD_ID.match(thread_id):
        raise ValueError(f"Invalid thread id: {thread_id!r}")
    # In pathlib, "/" joins paths: INDEX_DIR / "abc" -> indexes/abc
    return config.INDEX_DIR / thread_id


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


def _load_pages(file_bytes: bytes, filename: str) -> tuple[list[Document], int]:
    """Extract the text of each page of a PDF.

    Returns two things:
        pages        a list of Documents, one per page that has text
        total pages  how many pages the PDF has, including empty ones
    """
    # Streamlit gives us the upload as bytes in memory, but PyPDFLoader can
    # only read a file on disk. So: write the bytes to a temporary file...
    # (delete=False keeps the file after the "with" block so the loader can open it)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
        temp_file.write(file_bytes)
        temp_path = temp_file.name

    try:
        # ...read it (one Document per page)...
        raw_pages = PyPDFLoader(temp_path).load()
    finally:
        # ...and always delete the temp file afterwards, even if reading failed.
        try:
            os.remove(temp_path)
        except OSError:
            pass

    # Build clean Documents with just the metadata we need for citations.
    pages = [
        Document(
            page_content=page.page_content,
            # PyPDFLoader counts pages from 0; we add 1 so citations match the
            # page numbers a reader sees. "source" is the real filename
            # (otherwise it would be the random temp file name).
            metadata={"source": filename, "page": page.metadata.get("page", 0) + 1},
        )
        for page in raw_pages
        # Skip pages with no text (blank pages, or images without text).
        if page.page_content.strip()
    ]
    return pages, len(raw_pages)


def load_store(thread_id: str, embeddings: Embeddings | None = None) -> FAISS | None:
    """Return the FAISS index for this chat, or None if no PDF was uploaded.

    Looks in three places, in order:
        1. memory (_STORE_CACHE)  fastest, used after the first load
        2. disk (indexes/<id>/)   e.g. right after the app restarts
        3. nowhere                this chat has no PDF -> None

    `embeddings` can be passed in by tests; normally it's None and we use Gemini.
    """
    key = str(thread_id)
    if key in _STORE_CACHE:
        return _STORE_CACHE[key]

    folder = _thread_dir(key)
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
) -> dict:
    """Add a PDF to this chat's index and save it to disk.

    Uploading the same file twice is a no-op; uploading a different file adds
    to the index instead of replacing it.

    Steps:
        1. Fingerprint the file; stop if this chat already has it
        2. Extract text page by page
        3. Split pages into overlapping chunks
        4. Embed the chunks into the chat's FAISS index (new or existing)
        5. Save the index and the documents list to disk

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

    # Step 2: extract text.
    pages, total_pages = _load_pages(file_bytes, filename)
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
    # Each chunk keeps its page's metadata (source + page number).
    chunks = splitter.split_documents(pages)

    # Step 4: embed into FAISS.
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
    folder.mkdir(parents=True, exist_ok=True)  # create indexes/<id>/ if needed
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

    _STORE_CACHE[key] = store
    # {**entry, ...} copies all keys of entry and adds "already_indexed".
    return {**entry, "already_indexed": False}


def search(
    thread_id: str,
    query: str,
    k: int | None = None,
    embeddings: Embeddings | None = None,
) -> list[Document]:
    """Return the top-k passages for the query, from this chat's PDFs only.

    FAISS embeds the query and finds the k chunks whose vectors are closest
    to it (most similar meaning). Each result is a Document with
    .page_content (the text) and .metadata ({"source": ..., "page": ...}).
    Returns [] if this chat has no PDF.
    """
    store = load_store(thread_id, embeddings)
    if store is None:
        return []
    return store.similarity_search(query, k=k or config.TOP_K)
