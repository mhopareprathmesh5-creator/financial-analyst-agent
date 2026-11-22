"""Retrieval eval: score the search stage alone against the golden dataset.

PURPOSE: Stage 2 of the pipeline (chunk -> embed -> retrieve) is evaluated
on its own, with no LLM writing answers, so any failure here is clearly a
search failure. For each golden question it runs the app's real search
(rag/store.py), then scores the ranked results with the deterministic
metrics in evals/graders/retrieval_metrics.py.

Run from the project root:
    python -m evals.retrieval_eval                 # dev split (default)
    python -m evals.retrieval_eval --split test    # held-out split: final scores only
    python -m evals.retrieval_eval --label k8      # name the run in the report

Experiments change settings through environment variables (config.py), e.g.
    $env:CHUNK_SIZE=500; python -m evals.retrieval_eval --label chunk500

How indexing works: each report is indexed once per configuration (embedding
model + chunk size + overlap) into its own eval index, then reused by every
later run with that configuration. The first run takes ~5 min per report.

Output, in evals/reports/:
    retrieval_<time>_<label>.json   every question with its retrieved pages (gitignored)
    retrieval_<time>_<label>.md     summary tables + failures (committed)
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
from datetime import datetime
from pathlib import Path

import config
from evals.datasets import schema
from evals.graders import retrieval_metrics as m
from rag import query_rewrite, store

REPORTS_DIR = Path(__file__).resolve().parent / "reports"
# Query rewrites from the LLM, cached so reruns don't call Gemini again and
# give identical results. Committed to git: it makes runs reproducible.
REWRITE_CACHE_PATH = Path(__file__).resolve().parent / "cache" / "rewrites.json"
PDF_DIR = config.PROJECT_ROOT / "data" / "reports"
K_VALUES = (1, 4, 10)  # 4 is what the app uses today (config.TOP_K)
SUMMARY_METRICS = ["hit@1", "hit@4", "hit@10", "mrr", "page_recall@4", "value_hit@4"]


def eval_thread_id(doc: str) -> str:
    """Index name for one report under the current configuration, e.g.
    "eval-tcs_ar_fy25-c1000-o200" or, with chunk headings, "...-o200-h1".
    Every setting that changes the index must appear here, otherwise an
    experiment would silently reuse an index built with other settings. The
    embedding model is already part of the folder (indexes/<model>/...)."""
    name = f"eval-{Path(doc).stem}-c{config.CHUNK_SIZE}-o{config.CHUNK_OVERLAP}"
    return name + ("-h1" if config.CHUNK_HEADINGS else "")


def ensure_indexed(doc: str) -> dict:
    """Index the report for this configuration if it isn't already.
    Returns timing info, so ingestion speed is measured too (a Phase B goal)."""
    thread_id = eval_thread_id(doc)
    if store.list_documents(thread_id):
        return {"doc": doc, "indexed_now": False}

    print(f"Indexing {doc} as {thread_id} (first run for this config, ~5 min)...", flush=True)
    start = time.perf_counter()
    stage = {"read_done": None}

    def progress(fraction: float, message: str):
        # The first "Embedding..." message marks the end of PDF reading.
        if message.startswith("Embedding") and stage["read_done"] is None:
            stage["read_done"] = time.perf_counter()
            print(f"  {message}", flush=True)

    summary = store.ingest_pdf((PDF_DIR / doc).read_bytes(), thread_id, doc, on_progress=progress)
    end = time.perf_counter()
    return {
        "doc": doc,
        "indexed_now": True,
        "pages": summary["pages"],
        "chunks": summary["chunks"],
        "read_seconds": round(stage["read_done"] - start, 1),
        "embed_seconds": round(end - stage["read_done"], 1),
    }


def score_entry(entry: dict, k_max: int) -> dict:
    """Search for one golden question and compute every metric."""
    start = time.perf_counter()
    docs = store.search(eval_thread_id(entry["doc"]), entry["question"], k=k_max)
    latency = time.perf_counter() - start

    retrieved = [{"page": d.metadata["page"], "text": d.page_content} for d in docs]
    pages, match = entry["expected_pages"], entry["page_match"]
    scores = {"mrr": m.reciprocal_rank(retrieved, pages)}
    for k in K_VALUES:
        scores[f"hit@{k}"] = m.hit_at_k(retrieved, pages, match, k)
        scores[f"page_recall@{k}"] = m.page_recall_at_k(retrieved, pages, k)
        # Calculation answers (e.g. 19.11%) are computed, not printed, so
        # they can't appear in the chunks; value hits are skipped for them.
        if entry["category"] != "calculation":
            scores[f"value_hit@{k}"] = m.value_hit_at_k(retrieved, entry["expected_values"], k)

    return {
        "id": entry["id"],
        "doc": entry["doc"],
        "category": entry["category"],
        "wording": "paraphrase" if "paraphrase_of" in entry else "original",
        "paraphrase_of": entry.get("paraphrase_of"),
        "question": entry["question"],
        "expected_pages": pages,
        # What the LLM rewrote the question into (empty when rewriting is off),
        # kept so the rewrites themselves can be read and judged.
        "rewrites": query_rewrite.rewrite(entry["question"], config.QUERY_REWRITES),
        "retrieved_pages": [r["page"] for r in retrieved],
        # Kept for the DeepEval step, which judges the retrieved text itself.
        "retrieved_texts": [r["text"] for r in retrieved],
        "scores": scores,
        "latency_s": round(latency, 3),
    }


def average(results: list[dict], metric: str) -> float | None:
    """Mean of one metric over the results that have it (skips None)."""
    values = [r["scores"][metric] for r in results if r["scores"].get(metric) is not None]
    return statistics.mean(values) if values else None


def summarise(results: list[dict], key: str | None = None) -> dict:
    """Average metrics overall (key=None) or per group (e.g. key="category")."""
    groups: dict[str, list] = {"all": results} if key is None else {}
    if key:
        for r in results:
            groups.setdefault(r[key], []).append(r)
    return {
        name: {"n": len(rows), **{metric: average(rows, metric) for metric in SUMMARY_METRICS}}
        for name, rows in sorted(groups.items())
    }


def summarise_wording(results: list[dict]) -> dict:
    """Original vs paraphrased wording. The fair comparison is each
    paraphrase against ITS OWN original (same answer, same pages), so the
    originals that have a paraphrase get their own row."""
    paraphrased_ids = {r["paraphrase_of"] for r in results if r["paraphrase_of"]}
    groups = {
        "original (all)": [r for r in results if r["wording"] == "original"],
        "original (paraphrased ones)": [r for r in results if r["id"] in paraphrased_ids],
        "paraphrase": [r for r in results if r["wording"] == "paraphrase"],
    }
    return {
        name: {"n": len(rows), **{metric: average(rows, metric) for metric in SUMMARY_METRICS}}
        for name, rows in groups.items()
        if rows
    }


def fmt(value: float | None) -> str:
    return "–" if value is None else f"{value:.3f}"


def write_markdown(path: Path, run: dict):
    """Human-readable report: config, overall / per-category / per-report
    tables, then every question that missed at k=4."""
    lines = [
        f"# Retrieval eval: {run['label']}",
        "",
        f"Run {run['time']} · split **{run['split']}** · {run['n_questions']} questions "
        "(not-in-report questions excluded: nothing to retrieve)",
        "",
        "Config: " + ", ".join(f"`{k}={v}`" for k, v in run["config"].items()),
        "",
        f"Mean search latency: {run['mean_latency_s']:.3f} s per question",
        "",
    ]
    tables = [
        ("Overall", run["overall"]),
        # Compare experiments on "original (all)": it's the same questions in
        # every run, while "Overall" also includes paraphrases.
        ("By wording", run["by_wording"]),
        ("By category", run["by_category"]),
        ("By report", run["by_doc"]),
    ]
    for title, table in tables:
        lines += [f"## {title}", "", "| Group | n | " + " | ".join(SUMMARY_METRICS) + " |",
                  "|---|---|" + "---|" * len(SUMMARY_METRICS)]
        for name, row in table.items():
            lines.append(f"| {name} | {row['n']} | " + " | ".join(fmt(row[x]) for x in SUMMARY_METRICS) + " |")
        lines.append("")

    misses = [r for r in run["results"] if r["scores"]["hit@4"] == 0]
    lines += [f"## Misses at k=4 ({len(misses)})", "",
              "| id | category | expected pages | retrieved pages (top 10, best first) |", "|---|---|---|---|"]
    for r in misses:
        lines.append(f"| {r['id']} | {r['category']} | {r['expected_pages']} | {r['retrieved_pages']} |")

    if run["indexing"]:
        lines += ["", "## Indexing (first run for this config)", ""]
        lines += [f"- {i['doc']}: {i['pages']} pages, {i['chunks']} chunks, read {i['read_seconds']} s, "
                  f"embed {i['embed_seconds']} s" for i in run["indexing"]]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Retrieval eval against the golden dataset")
    parser.add_argument("--split", choices=["dev", "test", "all"], default="dev")
    parser.add_argument("--label", default="baseline")
    args = parser.parse_args()

    # Not-in-report questions have no evidence to retrieve; Phase C tests
    # that the agent refuses them.
    entries = [e for e in schema.load() if args.split == "all" or e["split"] == args.split]
    entries = [e for e in entries if e["category"] != "not_in_report"]

    # Rewrites go through the file cache during evals (search() calls the
    # rewriter, and score_entry() reads the same cached rewrites back).
    query_rewrite.CACHE = query_rewrite.RewriteCache(REWRITE_CACHE_PATH)

    indexing =[i for i in (ensure_indexed(d) for d in sorted({e["doc"] for e in entries})) if i["indexed_now"]]
    results = [score_entry(e, k_max=max(K_VALUES)) for e in entries]

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    run = {
        "label": args.label,
        "time": stamp,
        "split": args.split,
        "config": {"EMBEDDING_MODEL": config.EMBEDDING_MODEL, "CHUNK_SIZE": config.CHUNK_SIZE,
                   "CHUNK_OVERLAP": config.CHUNK_OVERLAP, "CHUNK_HEADINGS": config.CHUNK_HEADINGS,
                   "RETRIEVAL_MODE": config.RETRIEVAL_MODE, "HYBRID_CANDIDATES": config.HYBRID_CANDIDATES,
                   "RRF_K": config.RRF_K, "QUERY_REWRITES": config.QUERY_REWRITES,
                   "REWRITE_MODEL": config.REWRITE_MODEL if config.QUERY_REWRITES else None,
                   "k_values": list(K_VALUES)},
        "n_questions": len(results),
        "mean_latency_s": statistics.mean(r["latency_s"] for r in results),
        "overall": summarise(results),
        "by_wording": summarise_wording(results),
        "by_category": summarise(results, "category"),
        "by_doc": summarise(results, "doc"),
        "indexing": indexing,
        "results": results,
    }

    REPORTS_DIR.mkdir(exist_ok=True)
    base = REPORTS_DIR / f"retrieval_{stamp}_{args.label}"
    base.with_suffix(".json").write_text(json.dumps(run, indent=2, ensure_ascii=False), encoding="utf-8")
    write_markdown(base.with_suffix(".md"), run)

    for name, row in run["by_wording"].items():
        print(f"{name:<28} n={row['n']:<3} " + " | ".join(f"{k} {fmt(row[k])}" for k in SUMMARY_METRICS))
    print(f"Report: {base.with_suffix('.md')}")


if __name__ == "__main__":
    main()
