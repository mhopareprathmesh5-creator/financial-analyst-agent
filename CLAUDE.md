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
rag/store.py         PDF ingestion, per-chat FAISS index saved under indexes/<thread_id>/
app/history.py       Saved messages -> display turns with sources (no Streamlit, unit-testable)
tests/               pytest unit tests (offline: fake embeddings, fake PDFs)
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
