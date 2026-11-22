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
rag/store.py         PDF ingestion (pdfplumber + repair), local bge-small embeddings, per-chat FAISS index under indexes/<model>/<thread_id>/
rag/text_repair.py   Fixes broken-font glyphs from PDF extraction (TCS: ϰ -> 4 etc.; Finding F1)
app/history.py       Saved messages -> display turns with sources (no Streamlit, unit-testable)
tests/               pytest unit tests (offline: fake embeddings; tiny real PDFs via tests/pdf_factory.py)
experiments/         Measured experiments behind design choices, with their results
  pdf_readers/       PDF reader comparison vs hand-verified answer key (Finding F2); own requirements.txt
evals/               Eval harness
  datasets/          golden.jsonl (60 questions) + schema.py (validation, load())
  graders/           metrics
  reports/           eval run outputs (*.json gitignored, *.md committed)
data/reports/        Annual report PDFs used for evals
archive/             Original tutorial code, kept for reference only; do not edit or import
```

## Commands

Run from the project root with the venv active (`.\venv\Scripts\Activate.ps1`). Python 3.10, Windows/PowerShell.

```powershell
streamlit run streamlit_app.py        # run the app
python -m pytest -v                   # unit tests (offline, free, ~2s)
```

Secrets live in `.env` (see `.env.example`): GOOGLE_API_KEY (chat model), HUGGINGFACEHUB_API_TOKEN (embedding model download only), ALPHA_VANTAGE_API_KEY, LangSmith vars.

## Key design decisions

- **Thread id is injected by code, never by the LLM.** `search_documents` takes a hidden `RunnableConfig` parameter; the model only sees `query`. This prevents cross-chat document access. Keep it that way; there's a test for it.
- **The checkpointer is the single source of truth for chat history.** The UI rebuilds the conversation from `chatbot.get_state()`; don't keep a second copy in `st.session_state`.
- **Tool results use `content_and_artifact`:** text for the LLM, structured sources for the UI.
- **All tunables live in `config.py`** and are env-overridable, so eval experiments change settings, not code.
- **`build_graph(llm, checkpointer)` takes its dependencies** so evals/tests can swap the model or use an in-memory checkpointer.
- **Embeddings are local, not Gemini:** `BAAI/bge-small-en-v1.5` via `langchain-huggingface` on CPU (owner's choice after the Gemini free-tier limit, F7). Vectors are normalised; BGE's query instruction is added to questions only. Gemini is used for chat only.
- **Indexes are stored per embedding model** (`indexes/<model>/<thread_id>/`), so changing the model never mixes incompatible vectors; old chats just need a re-upload.
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

Approach (agreed 2026-11-18): **evaluate each pipeline stage before improving it.**

```
PDF -> (1) Extraction -> (2) Chunk + embed + retrieve -> (3) Generate answer -> (4) Agent + tools -> answer
       number accuracy     contextual recall/precision/     faithfulness,         tool correctness,
       (done, F2)          relevancy, page hit@k, MRR,      answer relevancy,     task completion,
                           ingestion latency                numeric + citation    refusals, injection
```

| Phase | Scope | Status |
|---|---|---|
| 0 | Setup: git, .gitignore, archive tutorial files, clean requirements | ✅ Done |
| 1 | Modular backend; bug fixes (persistent indexes, injected thread id, multi-PDF, clean history, uploader reset, titles, citations); unit tests | ✅ Done |
| 2 | Stage 1, extraction: pdfplumber + glyph repair chosen by measurement (F1, F2, F6); local bge-small embeddings (F7) | ✅ Done |
| A | **Golden dataset** `evals/datasets/golden.jsonl`: 60 questions (30 TCS, 30 Infosys; 40 dev / 20 test), each with expected answer, values, **expected PDF pages**, statement, category. Structure enforced by `evals/datasets/schema.py` + `tests/test_golden_dataset.py`; 19 entries verified by the owner against the PDFs | ✅ Done |
| B | ⏳ **Stage 2, retrieval eval**: deterministic page hit@k / MRR + DeepEval contextual recall / precision / relevancy; baseline → fix known misses (F8) → chunk size, top-k, hybrid BM25, reranker → **upload-speed optimisation under a recall guardrail** (target < 60 s for a 336-page report) | |
| C | **Stage 3, generation eval**: financial analyst system prompt (consolidated by default, cite pages, calculator for maths); faithfulness, answer relevancy, numeric correctness, citation correctness; prompt versions compared | |
| D | **Stage 4, agent eval**: expression calculator, Indian stock symbols, news tool; tool correctness, task completion, refusals, prompt-injection tests; live tools mocked for repeatable runs | |
| E | **Regression gate**: DeepEval + pytest in GitHub Actions on every push, with thresholds | |
| F | **Ship**: README with all results, deployment (see known limitations), resume bullets from real numbers | |

## Scope rule

**The project is about evals.** Build the eval for a stage **before** changing that stage, then change it only with measured before/after numbers. Speed-ups (e.g. faster ingestion) must hold quality metrics within an agreed guardrail.

## Eval setup

- Framework: **DeepEval** (pytest integration; RAG + agent metrics). RAGAS optional, once, as a cross-check.
- Judge: **Gemini** (owner's choice, 2026-11-18), using a stronger Gemini model than the agent's Flash-Lite. Same model family judging itself is a known bias, so the judge is **calibrated against the owner's hand labels** on a sample and its agreement is reported.
- **Deterministic metrics first** (page hit@k, numeric match, tool-call match): free, exact, repeatable. LLM-judged metrics only where code can't decide.
- Free-tier limits: judge calls cached and rate limited. Eval runs use reports indexed once and reused.

## Known limitations

- **Upload is slow: ~5 min for a 336-page report** (read 109–164 s, embed 189 s; F6/F7). Fixed in **Phase B**, under a retrieval-quality guardrail. Ideas: parallel page reading, larger chunks / ONNX embedding, keyword search available while embeddings build, preloaded sample reports, per-document index reuse.

Deferred to Phase F (deployment):

- `langchain-community` is deprecated (warning in tests).
- No user accounts: anyone using the app sees every chat. Needs login + per-user chat ownership.
- SQLite and `indexes/` are local files; Streamlit Cloud wipes disk on redeploy. Move chats to Postgres (e.g. Neon) and indexes to persistent storage.
- SQLite allows one writer at a time.
- No delete-chat (must remove checkpoint rows and `indexes/<model>/<thread_id>/` together).
- Free-tier rate limits on Gemini (agent and judge) will bite on repeated eval runs; see "Eval setup".

## Open decisions

- Annual report PDFs in `data/reports/` are gitignored (large files). Phase E must decide how CI gets them (commit them, download in CI, or commit a prebuilt eval index).
- Which stronger Gemini model is the judge (decide in Phase B when the first LLM-judged metric runs, based on free-tier availability).

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

### F7. Gemini embeddings hit the free-tier limit; switched to local bge-small (2026-11-02, Phase 2.1)
- Uploading the TCS report with Gemini embeddings (`gemini-embedding-2`) failed with `429 RESOURCE_EXHAUSTED`: free tier allows **100 embed requests per minute**, and each chunk counts as one request. One report needs ~1,400 chunks, and Phase 6 experiments re-embed both reports repeatedly.
- Owner's decision: local `BAAI/bge-small-en-v1.5` (Hugging Face, `langchain-huggingface` + sentence-transformers, CPU). Free, no limits, offline, report text stays local.
- Measured on the full TCS report through the real `ingest_pdf` (scratch index): model load **11 s**; read + repair **109 s**; chunk + embed + save **189 s** for **1,415 chunks** (~7.5 chunks/s on CPU). Total ≈ 5 min, no errors. (Read time varies run to run: 164 s in F6, 109 s here.)

### F8. Retrieval spot check reveals standalone vs consolidated confusion (2026-11-02, Phase 2.1)
- Spot check only (4 questions, top-4 chunks, bge-small, chunk 1000/200), not a measured eval; it shows what the eval set must cover.
- **Annual reports contain two sets of financial statements**: consolidated (whole group) and standalone (parent company only), with different numbers. Retrieval mixed them:
  - "Basic earnings per share?" → standalone EPS ₹132.83 (p253) ranked above the consolidated ₹134.19 (p181, not in top 4).
  - "Revenue from Europe?" → top hit standalone ₹59,339 crore (p287); consolidated ₹79,487 crore (p230) second.
- "Revenue from operations FY2025?" → p88 (MD&A financial overview table), a sensible hit, though not the P&L page 181.
- "Who is the CEO?" → **no relevant chunk** in top 4 (all p87 marketing text). Possible cause: broken spacing in "Letter fro m the CEO" (F4).
- Implications: eval set needs consolidated-vs-standalone cases; the system prompt should default to consolidated figures and say which one it used; retrieval improvements (top-k, hybrid BM25) to be measured in Phase 6.

### F9. Golden dataset built (2026-11-19, Phase A)
- 60 questions: fact 16, consolidated-vs-standalone 12, narrative 11, calculation 8, multi-location 7, not-in-report 6; 30 per report; 40 dev / 20 test fixed before any results existed.
- Every answer checked against a rendered page image (tables) or the repaired page text (prose); calculation answers computed in Python. **19/60 independently verified by the owner** against the PDFs; no errors found in the owner's sample.
- Deliberately hard cases: 3 false-premise questions (TCS revenue "decline", Infosys FY25 "special dividend", MRE acquisition "completed"); not-in-report traps where the year/term does appear in an unrelated context (TCS "2009-10" tax years, "June 30, 2025" results calendar; Infosys "fiscal 2026" CSR plan, "ESG Vision 2030"); a bar-chart answer whose extracted text has no labels (Infosys North America 57.9%); the same number in Indian and international formats; FY2024 EPS reported (125.88) vs adjusted (127.74).
- Dropped one candidate during building: "Infosys revenue from Japan" was not cleanly absent (subsidiary HIPUS turnover on p44 could count as an answer). Ambiguous not-in-report questions make an eval unfair.

### F10. Retrieval baseline is poor: hit@4 = 24.3% (2026-11-21, Phase B)
- Run: `python -m evals.retrieval_eval --label baseline` → `evals/reports/retrieval_20261121-222530_baseline.md`. Dev split, 37 questions (not-in-report excluded), bge-small, chunk 1000 / overlap 200, plain vector search.
- **hit@1 2.7% · hit@4 24.3% · hit@10 37.8% · MRR 0.140 · value_hit@4 29.6%.** Only 9/37 questions get a chunk from an expected page into the 4 chunks the agent sees.
- By category (hit@4): consolidated-vs-standalone 37.5%, multi-location 33.3%, narrative 28.6%, calculation 20.0%, **fact 9.1%**.
- **Sanity check before trusting it (F5 lesson):** for the misses, the expected number is absent from the top-4 retrieved chunks in all but one case, so the misses are real retrieval failures, not an answer key that missed valid pages.
- What search returns instead: **TCS** — summary/narrative pages (p88 MD&A overview, p22–23 Financial Capital, p70 Board's report) for nearly every financial question. **Infosys** — the subsidiary financials table (AOC-1, p45–48: every subsidiary's turnover and profit) and p73, which look like "revenue/profit" text but are about other entities.
- Indexing time on this run: Infosys 369 pages → 1,570 chunks, read 59.9 s + embed 242.8 s; TCS 336 pages → 1,415 chunks, read 122.4 s + embed 211.6 s.
- Hypotheses to test, one at a time: table chunks lose their heading (a chunk from the middle of the P&L doesn't say "Consolidated Statement of Profit and Loss"); a small embedding model is weak on number-heavy tables; exact terms like "Revenue from operations" need keyword search (BM25); a reranker; broken TCS word spacing (F4).

### F11. Experiment 1: page headings on every chunk (2026-11-21, Phase B)
- Change: `CHUNK_HEADINGS=1` prepends each page's heading (first 2 lines with ≥2 words, e.g. "Consolidated Financial Statements 2024-25 | Consolidated Statement of Profit and Loss") to every chunk from that page. Code: `rag/store.py` `page_heading()`; tests in `tests/test_pdf_reading.py`.
- Run: `evals/reports/retrieval_20261121-225734_headings.md` vs baseline (F10), same 37 dev questions.

| Metric | Baseline | Headings |
|---|---|---|
| hit@1 | 2.7% (1) | **13.5% (5)** |
| hit@4 | 24.3% (9) | **29.7% (11)** |
| hit@10 | 37.8% | 40.5% |
| MRR | 0.140 | **0.200** |
| value_hit@4 | 29.6% | 37.0% |
| TCS / Infosys hit@4 | 27.8% / 21.1% | **38.9%** / 21.1% |

- Per question: hit@1 **+4 gained, 0 lost** (TCS consolidated EPS, UK revenue, TCS and Infosys consolidated operating cash flow). hit@4 +4 gained (TCS standalone EPS, UK revenue, headcount, Infosys consolidated EPS), **2 lost**.
- Prediction made before the run held: TCS improved (its pages are titled "Consolidated …" / "Standalone …"), Infosys didn't.
- Loss analysis: `inf-ocf-stand-01` — Infosys's standalone statements are titled without "Standalone" ("Statement of Cash Flows"), while consolidated ones say "Consolidated …", so a "standalone" question now matches the consolidated page more strongly. `tcs-attrition-01` — heading text added noise to a prose chunk.
- Caveat: 37 questions, 1 question = 2.7 points; the hit@4 gain is +2 questions net. The ranking gain (hit@1, MRR, zero rank-1 losses) is the stronger evidence.
- Still ~70% of questions miss at k=4: headings help ranking but don't fix the main problem.
- **Decision: headings kept, now on by default** (`CHUNK_HEADINGS=1`).

### F12. Experiment 2: keyword (BM25) and hybrid search (2026-11-21, Phase B)
- Code: `rag/keyword_search.py` (BM25 via `rank-bm25`, RRF merge); `config.RETRIEVAL_MODE` = vector | bm25 | hybrid; hybrid = 20 candidates from each search, RRF with k=60. Tests: `tests/test_keyword_search.py`. All runs with headings, same 37 dev questions, same indexes.
- Reproducibility check: the vector run reproduced F11 exactly (hit@4 29.7%).

| Mode | hit@1 | hit@4 | hit@10 | MRR | value_hit@4 |
|---|---|---|---|---|---|
| vector | 13.5% | 29.7% | 40.5% | 0.200 | 37.0% |
| **bm25** | **29.7%** | **59.5%** | **73.0%** | **0.431** | **63.0%** |
| hybrid (equal-weight RRF) | 21.6% | 48.6% | 73.0% | 0.362 | 55.6% |

- vector → bm25 at hit@4: **+15 gained, 4 lost**; every category improves (fact 27→55%, narrative 14→57%, calculation 20→60%, consolidated-vs-standalone 50→63%); Infosys 21→68%, TCS 39→50%.
- **Hybrid is worse than BM25 alone** (bm25 → hybrid: +3 gained, 7 lost at hit@4). Equal-weight RRF assumes both searches are comparably good; here vector is much weaker, so its rankings push BM25's correct chunks out of the top 4. Fusion only helps when the retrievers are of similar quality.
- hit@10 is 73% for both bm25 and hybrid: the right page is usually in the top 10 but ranked too low → a reranker over the top candidates is the natural next step.
- **Caveat about our own dataset:** the golden questions were written with the report's own terms ("revenue from operations", "statutory auditors", "attrition"), which favours keyword search. Users paraphrase ("sales", "who audits"), where vector search should help. BM25's lead is probably overstated; paraphrased question variants would test this.
- A unit test caught a BM25 subtlety while building: in standard BM25 a word present in ≥ half of all chunks gets zero weight (IDF = log 1), so "drop chunks scoring 0" wrongly drops matching chunks. Fixed by filtering on word overlap instead.
- Remaining TCS misses often return p155 (several times in the top 10), and broken word spacing ("Co n s o lid ated", F4) breaks keyword matching on TCS narrative pages.

### F13. Paraphrased questions: BM25's lead was mostly our dataset's wording (2026-11-21, Phase B)
- Added 17 paraphrases (`paraphrase_of` field; 14 dev, 3 test) of existing questions in users' own words, avoiding report terms ("total group sales" for revenue from operations, "finance chief" for CFO, "which firm audits" for statutory auditors). Same answers and pages; `schema.py` enforces same split as the original. Dataset now 77 entries.
- Runs: `evals/reports/retrieval_*_para-{vector,bm25,hybrid}.md`; report has a "By wording" table. Fair comparison = the 14 dev paraphrases vs their own 14 originals (1 question = 7.1 points):

| Mode | hit@4, report's wording | hit@4, user's wording |
|---|---|---|
| vector | 21.4% | 21.4% |
| bm25 | **50.0%** | **14.3%** |
| hybrid | 42.9% | 21.4% |

- **BM25 collapses on user wording** (it matches words; "sales" never finds "revenue from operations"). Vector is wording-robust but weak overall. Hybrid is the safest: near BM25 on report wording, never below vector on user wording.
- **For real users, every mode scores 14–21% hit@4.** The core problem is vocabulary mismatch between users and annual reports.
- The F12 caveat is confirmed: a dataset written in the source document's own terms overstates keyword search.
- Fix candidates, to measure next: query rewriting (an LLM rewrites the question into report terminology), a cross-encoder reranker, a stronger embedding model.

### F14. Windows Smart App Control blocked FAISS; fixed by pinning a trusted version (2026-11-22, environment)
- After working until 2026-11-21, `import faiss` failed: `DLL load failed while importing _swigfaiss: An Application Control policy has blocked this file`. 16 tests and every search failed. No project change caused it.
- Windows Code Integrity log: Smart App Control state **1 (enforcing)**; 68 block events since 2026-11-16 (the PyTorch block on 2026-11-18 was one of them). Smart App Control judges each file by Microsoft cloud reputation, and the verdict can change over time; it has **no per-file exceptions**.
- Owner chose to keep FAISS and keep Smart App Control on. Tried other official releases: **faiss-cpu 1.15.0 and 1.16.0 blocked; 1.12.0 allowed.** All 72 tests pass on 1.12.0; pinned in `requirements.txt`.
- Risk remains: any unsigned native library (FAISS, PyTorch) can be blocked again at any time. Fallbacks if it recurs: another faiss-cpu version, NumPy-based vector search (also removes the deprecated `langchain-community` FAISS wrapper), or running in WSL.
- Reproducibility check after the switch: hybrid without rewriting (`retrieval_*_repro-hybrid.md`) reproduced F13 exactly, so neither faiss 1.12.0 nor the refactored `search()` changed results.

### F15. Experiment 3: query rewriting, prompt v1 (2026-11-22, Phase B)
- Code: `rag/query_rewrite.py` (Gemini `gemini-3.1-flash-lite-preview`, temperature 0, general instructions only, no dataset term mappings — enforced by a test); `config.QUERY_REWRITES=3`; original + 3 rewrites searched in hybrid mode, all 8 ranked lists merged with RRF. Rewrites cached in `evals/cache/rewrites.json` (51 Gemini calls, once).
- Run: `retrieval_*_hybrid-rewrite3.md` vs `retrieval_*_repro-hybrid.md`.

| hit@4 | hybrid | hybrid + 3 rewrites |
|---|---|---|
| user's wording (14 paraphrases) | 21.4% | **35.7%** |
| report's wording, same 14 originals | 42.9% | 28.6% |
| all 37 originals | 48.6% | 48.6% (hit@10 73.0% → 64.9%; value_hit@4 55.6% → 66.7%) |

- Per question at hit@4: **9 gained, 7 lost**. Rewriting moves questions around more than it helps.
- **Rewrite quality is good on vocabulary:** "total group sales" → "consolidated revenue from operations"; "cash the group's day-to-day business brought in" → "net cash generated from operating activities"; "what companies did Infosys buy" → "business combinations and acquisitions".
- **Failure 1 — the rewriter adds facts:** with no year in the question, Gemini inserted the wrong one ("TCS annual report **2023-24** Chief Financial Officer", "statutory auditor … financial year **2023-24**"; the report is 2024-25), despite "don't add facts" in the prompt.
- **Failure 2 — verbose boilerplate:** rewrites like "Tata Consultancy Services Limited consolidated … for the financial year ended March 31, 2025" are full of words found on hundreds of pages; BM25 then favours generic pages (TCS p302, p200, p186) over the statements, and the original question is only 2 of 8 merged lists. Most losses are questions that worked before (TCS revenue, profit, dividend).
- Overfitting caution: further prompt tuning is evaluated on the same dev questions; only general rules are allowed, and the untouched test split gives the final number.

### F16. Experiment 4: query rewriting prompt v2 + weighted original (2026-11-22, Phase B)
- Changes (general rules only, no dataset terms): prompt v2 adds "never add a year, date, company name or any other fact not in the question" and "3 to 8 words, keywords only"; the original question's ranked lists get weight 2 in RRF (`ORIGINAL_QUERY_WEIGHT`, fixed up front, not tuned). Run: `retrieval_*_hybrid-rewrite3-v2.md`.
- Rewrite quality, v1 → v2 (153 rewrites each): average length **13.7 → 4.8 words**; rewrites with a year **134 → 0**; with a company name **153 → 0**; invented years **0**. Example: "Which firm audits Infosys's accounts?" → "Statutory auditor appointment" / "Independent auditor firm name" / "Statutory audit firm details".

| hit@4 | hybrid | rewrite v1 | rewrite v2 |
|---|---|---|---|
| user's wording (14) | 21.4% | 35.7% | **57.1%** |
| report's wording, same 14 | 42.9% | 28.6% | **57.1%** |
| all 37 originals | 48.6% | 48.6% | **56.8%** |
| hit@1, all originals | 21.6% | 24.3% | **35.1%** |
| MRR, all originals | 0.362 | 0.362 | **0.464** |

- vs hybrid at hit@4: **11 gained, 3 lost** (all dividend questions: "dividend per share" appears on many pages).
- **The wording gap from F13 is closed:** user wording and report wording both 57.1% on the paired 14.
- Progress so far on the 37 original dev questions, hit@4: baseline 24.3% → headings 29.7% → hybrid 48.6% → **rewrite v2 56.8%**; hit@1 2.7% → **35.1%**.
- Caveats: tuned on the dev split (test split untouched); one extra Gemini call per search, whose latency in the app isn't measured yet (rewrites were cached in this run).
