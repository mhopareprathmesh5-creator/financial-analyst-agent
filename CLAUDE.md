# Financial Analyst Agent

A LangGraph agent that answers questions about a company's annual report (PDF), computes financial ratios, and adds live share prices and news — plus an **LLM evaluation harness** that measures and gates the agent's behaviour. Evaluation is the point of the project; the agent is what gets evaluated.

Repo: https://github.com/mhopareprathmesh5-creator/financial-analyst-agent

## What the agent does

User uploads an annual report (e.g. TCS, Infosys) and asks questions. The agent:
1. Finds facts in the report, with page citations
2. Calculates ratios the report doesn't state (margin, growth, P/E) using the calculator tool, never mental maths
3. Combines report data with the live share price
4. Searches the web for news since the report
5. Summarises and explains in simple terms
6. Refuses honestly: predictions, or facts not in the report

## Project structure

```
config.py            All settings (models, chunk size, top-k, paths); each overridable by env var
streamlit_app.py     UI entry point
agent/graph.py       LangGraph agent (chat_node <-> tools loop), SQLite checkpointer, chat list helpers
agent/tools.py       search_documents, web_search, get_stock_price, calculator
agent/prompts.py     System prompt
rag/store.py         PDF ingestion (pdfplumber + repair), per-chat FAISS index saved under indexes/<thread_id>/
rag/text_repair.py   Fixes broken-font glyphs from PDF extraction (TCS: ϰ -> 4 etc.; Finding F1)
app/history.py       Saved messages -> display turns with sources (no Streamlit, unit-testable)
tests/               pytest unit tests (offline: fake embeddings; tiny real PDFs via tests/pdf_factory.py)
experiments/         Measured experiments behind design choices, with their results
  pdf_readers/       PDF reader comparison vs hand-verified answer key (Finding F2); own requirements.txt
evals/               LLM eval harness (Phase 3+): datasets/, graders/, reports/
data/reports/        Annual report PDFs used for evals
archive/             Original tutorial code, kept for reference only; do not edit or import
```

## Commands

Run from the project root with the venv active (`.\venv\Scripts\Activate.ps1`). Python 3.10, Windows/PowerShell.

```powershell
streamlit run streamlit_app.py        # run the app
python -m pytest -v                   # unit tests (offline, free, ~2s)
```

Secrets live in `.env` (see `.env.example`): GOOGLE_API_KEY, ALPHA_VANTAGE_API_KEY, LangSmith vars.

## Key design decisions

- **Thread id is injected by code, never by the LLM.** `search_documents` takes a hidden `RunnableConfig` parameter; the model only sees `query`. This prevents cross-chat document access. Keep it that way; there's a test for it.
- **The checkpointer is the single source of truth for chat history.** The UI rebuilds the conversation from `chatbot.get_state()`; don't keep a second copy in `st.session_state`.
- **Tool results use `content_and_artifact`:** text for the LLM, structured sources for the UI.
- **All tunables live in `config.py`** and are env-overridable, so eval experiments change settings, not code.
- **`build_graph(llm, checkpointer)` takes its dependencies** so evals/tests can swap the model or use an in-memory checkpointer.
- Storage: chats in `chatbot.db` (SQLite, via LangGraph `SqliteSaver`); PDF indexes as files in `indexes/`. Both are gitignored.

## Conventions

- Code carries **detailed teaching comments**: a PURPOSE docstring at the top of every file, a docstring on every function, and comments on the "why" of important lines. The owner is learning from this code.
- Every bug fix or behaviour guarantee gets a pytest test. Tests must not call external APIs.
- Never hardcode keys; read from env.
- Resume claims and README numbers must come from **real measured eval results**, never estimates.
- **Log findings in the "Findings" section at the bottom of this file** as they happen: measurements, surprising failures, trade-offs and our own mistakes, each with date, phase and the file that produced the numbers. It is the source for the README and write-up in Phase 8. Keep everything in this file; don't create separate notes files.

## Working with the owner

- Explain what is being built and why, in simple terms, **before** writing code.
- The owner runs git commands (add/commit/push) themselves. Write code and give them the exact git commands; don't commit.
- The owner runs tests and the app and pastes output. Explain unfamiliar commands piece by piece.
- **Update this file at the end of every phase** (status table + anything new in structure, commands or decisions).

## Roadmap and status

| Phase | Scope | Status |
|---|---|---|
| 0 | Setup: git, .gitignore, archive tutorial files, clean requirements | ✅ Done |
| 1 | Modular backend; bug fixes (persistent indexes, injected thread id, multi-PDF, clean history, uploader reset, titles, citations); 19 unit tests | ✅ Done |
| 2 | Financial analyst: annual reports, table-aware chunking, expression calculator, Indian stock symbols, news tool, system prompt; migrate off deprecated `langchain-community` | ⏳ Next |
| 3 | Eval dataset (~120 cases, 6 categories: fact, calculation, live data, should-refuse, no-tool, security); dev/test split | |
| 4 | Graders: numeric, tool trajectory, citation, LLM judge (non-Gemini family) calibrated against human labels; mock live tools for determinism | |
| 5 | Baseline run + failure analysis | |
| 6 | Measured improvements (prompt, chunk size, top-k, hybrid BM25, model); final test-set run | |
| 7 | GitHub Actions: unit tests + small eval set on every PR, fail on regression | |
| 8 | README with results, deployment, resume bullets | |

## Known limitations (deferred to Phase 8 — deployment)

- No user accounts: anyone using the app sees every chat. Needs login + per-user chat ownership.
- SQLite and `indexes/` are local files; Streamlit Cloud wipes disk on redeploy. Move chats to Postgres (e.g. Neon) and indexes to persistent storage.
- SQLite allows one writer at a time.
- No delete-chat (must remove checkpoint rows and `indexes/<thread_id>/` together).
- `langchain-community` is deprecated (warning in tests); migrate in Phase 2.

## Open decisions

- Annual report PDFs in `data/reports/` are gitignored (large files). Phase 7 must decide how CI gets them (commit them, download in CI, or commit a prebuilt eval index).

## Findings (for the final README / write-up)

Only measured or verified facts; each names the file that produced it. Include failures and our own mistakes. Newest at the bottom.

### F1. The TCS report's font maps digits to Greek letters (2026-10-15, Phase 2.1)
- The TCS FY25 annual report's font has a wrong character table. Every PDF library reads the same wrong answer: 4 → "ϰ", 5 → "ϱ", 0 → "Ϭ", "%" → "й", "₹" → "༤", "." → "͘".
- Scale: the broken "4" alone appears **2,591 times on 247 of 336 pages** (74%). Example, consolidated P&L (PDF page 181): extracted `2,55,32ϰ 2,ϰ0,893`, real `2,55,324 2,40,893`.
- Why it matters: it fails silently; no error, just wrong numbers in every answer.
- Found by measuring extraction quality before building retrieval, instead of assuming the PDF library works.
- Fix: `rag/text_repair.py`, a glyph → character lookup. Broken digits sit in one Unicode block (U+03EC = 0 … U+03F5 = 9). Mappings checked against page images; tested in `tests/test_text_repair.py` with real report strings.
- Detail worth telling: repair must run **before** Unicode NFKC normalisation, which would turn "ϰ" into the Greek letter "κ" and make it unrecognisable.

### F2. PDF reader comparison against a hand-verified answer key (2026-10-31, Phase 2.1)
- Answer key: 52 table rows / 164 numbers from 4 key pages (TCS P&L, TCS segment/geography notes, Infosys board's report summary, Infosys consolidated P&L), read from rendered page images. Files: `experiments/pdf_readers/compare.py`, `ground_truth.json`, `results.md`.
- Metrics: number accuracy (exactly as printed), row integrity (label + all its numbers on one line), garbage glyphs, fragmented words, speed (89 sampled pages).

| Reader | Number accuracy | Row integrity | Seconds/page |
|---|---|---|---|
| pypdf (original setup) | 66.5% (109/164) | 40.4% (21/52) | 0.105 |
| pypdf + repair | 76.2% (125/164) | 61.5% (32/52) | 0.116 |
| PyMuPDF | 73.2% (120/164) | 0.0% (0/52) | 0.005 |
| PyMuPDF + repair | 82.9% (136/164) | 0.0% (0/52) | 0.005 |
| pdfplumber | 90.2% (148/164) | 71.2% (37/52) | 0.263 |
| **pdfplumber + repair** | **100.0% (164/164)** | **92.3% (48/52)** | 0.301 |
| pymupdf4llm | 73.2% (120/164) | 51.9% (27/52) | 0.780 |
| pymupdf4llm + repair | 73.2% (120/164) | 51.9% (27/52) | 0.506 |

- **Decision: pdfplumber + repair.** Headline: the original setup read about **1 in 3 numbers wrong**; the chosen one reads all 164.
- Trade-off: pdfplumber is ~3× slower than pypdf. Accepted: extraction runs once per upload; wrong numbers affect every answer. (Full-report timing in F6.)
- PyMuPDF is ~60× faster but 0% row integrity (every table cell on its own line, numbers separated from labels).
- pymupdf4llm didn't improve with repair (its layout engine emits broken text in another form). Not pursued.
- Still imperfect: 4 rows split across lines (multi-line labels); 144 unrecognised glyphs remain in TCS decorative infographic fonts, left visible rather than guessed.

### F3. A PyPI package with no code (2026-10-31, Phase 2.1)
- `pip install pymupdf4llm` installed version **2.0**: no code, no author, empty metadata. The genuine package (Artifex) follows PyMuPDF's versions (1.28.2). Removed and pinned the verified version. Lesson: check what you install, especially an unexpected major version.

### F4. Observations that affect later phases (2026-10-31, Phase 2.1)
- Infosys uses **two number formats**: Indian grouping in the board's report (`1,62,990`), international in the financial statements (`162,990`). The numeric grader (Phase 4) must accept both.
- **Printed page ≠ PDF page:** TCS P&L is printed page 179 but PDF page 181; Infosys PDF 276 = printed 304. Citations use PDF page numbers (what a viewer jumps to); eval dataset and citation grader must use the same.
- **Broken word spacing** in TCS text ("Co n s o lid ated", "sh are w ere") across readers; may hurt keyword search. Revisit with hybrid BM25 in Phase 6.

### F5. Our own mistakes caught along the way (2026-10-31, Phase 2.1)
- **Metric bug:** the first garbage metric missed pdfplumber's `(cid:N)` codes, making pdfplumber look far cleaner (2) than it was (641). Fixed before concluding. Lesson: sanity-check surprising scores; metrics can be wrong too.
- **Wrong character code:** rupee repair first written for U+0F64 instead of U+0F24; a unit test caught it immediately.
- **Miscount:** answer key first described as 54 rows / 168 numbers; the script counted 52 / 164. Trust the script.

### F6. pdfplumber + repair on the full TCS report, in the app's ingestion code (2026-11-01, Phase 2.1)
- `rag/store.py` now reads PDFs with pdfplumber + `repair_text` (replacing LangChain's `PyPDFLoader`/pypdf), with a progress bar in the UI.
- Full TCS report: 336/336 pages with text, **164 s to read** (0.49 s/page; slower than the 0.30 s/page sample estimate in F2). Broken "4" glyphs remaining: **0** (was 2,591). P&L check: `Revenue from operations 12 2,55,324 2,40,893`, `Earnings per equity share:- Basic and diluted (₹) 18 134.19 125.88`, both correct.
- **1,244 unrecognised `(cid:N)` codes remain on 148 pages.** They are letters in *other* broken fonts in narrative/legal text, not the financial tables, e.g. `De(cid:448)elo(cid:393)men(cid:410)` = "Development". Each code is rare. **Decision: not mapped yet**; revisit only if Phase 5 failure analysis shows retrieval misses on those pages.
- Word spacing stays broken in TCS narrative text ("Letter fro m the CEO", "Signif icant innov ation") — see F4.
