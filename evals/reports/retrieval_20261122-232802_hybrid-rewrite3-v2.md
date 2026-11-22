# Retrieval eval: hybrid-rewrite3-v2

Run 20261122-232802 · split **dev** · 51 questions (not-in-report questions excluded: nothing to retrieve)

Config: `EMBEDDING_MODEL=BAAI/bge-small-en-v1.5`, `CHUNK_SIZE=1000`, `CHUNK_OVERLAP=200`, `CHUNK_HEADINGS=True`, `RETRIEVAL_MODE=hybrid`, `HYBRID_CANDIDATES=20`, `RRF_K=60`, `QUERY_REWRITES=3`, `REWRITE_MODEL=gemini-3.1-flash-lite-preview`, `REWRITE_PROMPT=v2`, `ORIGINAL_QUERY_WEIGHT=2.0`, `k_values=[1, 4, 10]`

Mean search latency: 8.050 s per question

## Overall

| Group | n | hit@1 | hit@4 | hit@10 | mrr | page_recall@4 | value_hit@4 |
|---|---|---|---|---|---|---|---|
| all | 51 | 0.333 | 0.569 | 0.765 | 0.448 | 0.423 | 0.730 |

## By wording

| Group | n | hit@1 | hit@4 | hit@10 | mrr | page_recall@4 | value_hit@4 |
|---|---|---|---|---|---|---|---|
| original (all) | 37 | 0.351 | 0.568 | 0.784 | 0.464 | 0.446 | 0.741 |
| original (paraphrased ones) | 14 | 0.429 | 0.571 | 0.714 | 0.482 | 0.405 | 0.800 |
| paraphrase | 14 | 0.286 | 0.571 | 0.714 | 0.407 | 0.362 | 0.700 |

## By category

| Group | n | hit@1 | hit@4 | hit@10 | mrr | page_recall@4 | value_hit@4 |
|---|---|---|---|---|---|---|---|
| calculation | 5 | 0.400 | 0.600 | 0.600 | 0.467 | 0.600 | – |
| consolidated_vs_standalone | 10 | 0.100 | 0.900 | 1.000 | 0.427 | 0.633 | 0.900 |
| fact | 15 | 0.400 | 0.533 | 0.667 | 0.463 | 0.467 | 0.714 |
| multi_location | 8 | 0.500 | 0.625 | 0.875 | 0.585 | 0.321 | 0.625 |
| narrative | 13 | 0.308 | 0.308 | 0.692 | 0.356 | 0.205 | 0.600 |

## By report

| Group | n | hit@1 | hit@4 | hit@10 | mrr | page_recall@4 | value_hit@4 |
|---|---|---|---|---|---|---|---|
| infosys_ar_fy25.pdf | 25 | 0.320 | 0.520 | 0.800 | 0.449 | 0.476 | 0.812 |
| tcs_ar_fy25.pdf | 26 | 0.346 | 0.615 | 0.731 | 0.447 | 0.372 | 0.667 |

## Misses at k=4 (22)

| id | category | expected pages | retrieved pages (top 10, best first) |
|---|---|---|---|
| tcs-eps-stand-01 | consolidated_vs_standalone | [253] | [229, 307, 300, 315, 69, 88, 181, 311, 318, 253] |
| tcs-assets-cons-01 | fact | [180] | [273, 201, 184, 186, 195, 283, 88, 190, 230, 171] |
| tcs-equity-cons-01 | fact | [180] | [276, 203, 181, 186, 307, 276, 171, 174, 185, 275] |
| tcs-dividend-01 | narrative | [23] | [69, 307, 240, 315, 202, 275, 69, 108, 23, 23] |
| inf-rev-cons-01 | multi_location | [30, 276] | [242, 323, 73, 73, 264, 346, 276, 196, 242, 344] |
| inf-pat-cons-01 | fact | [30, 276, 283] | [277, 265, 323, 76, 323, 276, 264, 73, 346, 339] |
| inf-employees-01 | multi_location | [10, 22, 37, 78, 124] | [157, 280, 149, 134, 134, 147, 149, 218, 257, 16] |
| inf-dividend-01 | multi_location | [35, 17, 110] | [23, 231, 310, 231, 35, 310, 110, 310, 33, 51] |
| inf-special-div-01 | fact | [35] | [23, 310, 231, 23, 35, 310, 230, 23, 35, 231] |
| inf-chairman-01 | narrative | [11, 16, 197] | [84, 84, 346, 84, 282, 202, 11, 13, 85, 83] |
| inf-opmargin-01 | narrative | [17] | [76, 344, 75, 23, 321, 23, 15, 266, 240, 17] |
| inf-taxrate-cons-01 | calculation | [276] | [74, 74, 74, 74, 317, 74, 74, 74, 317, 323] |
| tcs-cfo-01 | narrative | [180, 181, 253] | [106, 99, 71, 73, 64, 317, 72, 229, 71, 131] |
| inf-auditor-01 | narrative | [197] | [108, 77, 77, 117, 91, 56, 119, 180, 356, 91] |
| inf-rev-growth-01 | calculation | [276, 30] | [73, 73, 76, 73, 266, 74, 267, 184, 73, 75] |
| tcs-false-decline-01 | fact | [181, 230, 95] | [172, 88, 174, 70, 172, 286, 172, 180, 214, 286] |
| tcs-assets-cons-01-para | fact | [180] | [186, 174, 230, 273, 200, 200, 174, 282, 184, 299] |
| tcs-headcount-01-para | fact | [95] | [131, 313, 157, 139, 81, 141, 84, 131, 140, 85] |
| tcs-dividend-01-para | narrative | [23] | [69, 69, 307, 275, 202, 23, 229, 240, 315, 276] |
| tcs-cfo-01-para | narrative | [180, 181, 253] | [99, 103, 106, 64, 72, 317, 87, 229, 73, 98] |
| inf-auditor-01-para | narrative | [197] | [77, 40, 108, 57, 56, 182, 77, 56, 40, 57] |
| inf-chairman-01-para | narrative | [11, 16, 197] | [85, 85, 12, 13, 13, 85, 84, 84, 11, 13] |
