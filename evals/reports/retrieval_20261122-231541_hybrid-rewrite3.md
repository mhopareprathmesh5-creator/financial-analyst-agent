# Retrieval eval: hybrid-rewrite3

Run 20261122-231541 · split **dev** · 51 questions (not-in-report questions excluded: nothing to retrieve)

Config: `EMBEDDING_MODEL=BAAI/bge-small-en-v1.5`, `CHUNK_SIZE=1000`, `CHUNK_OVERLAP=200`, `CHUNK_HEADINGS=True`, `RETRIEVAL_MODE=hybrid`, `HYBRID_CANDIDATES=20`, `RRF_K=60`, `QUERY_REWRITES=3`, `REWRITE_MODEL=gemini-3.1-flash-lite-preview`, `k_values=[1, 4, 10]`

Mean search latency: 9.126 s per question

## Overall

| Group | n | hit@1 | hit@4 | hit@10 | mrr | page_recall@4 | value_hit@4 |
|---|---|---|---|---|---|---|---|
| all | 51 | 0.196 | 0.451 | 0.608 | 0.313 | 0.344 | 0.568 |

## By wording

| Group | n | hit@1 | hit@4 | hit@10 | mrr | page_recall@4 | value_hit@4 |
|---|---|---|---|---|---|---|---|
| original (all) | 37 | 0.243 | 0.486 | 0.649 | 0.362 | 0.392 | 0.667 |
| original (paraphrased ones) | 14 | 0.143 | 0.286 | 0.500 | 0.237 | 0.202 | 0.400 |
| paraphrase | 14 | 0.071 | 0.357 | 0.500 | 0.185 | 0.217 | 0.300 |

## By category

| Group | n | hit@1 | hit@4 | hit@10 | mrr | page_recall@4 | value_hit@4 |
|---|---|---|---|---|---|---|---|
| calculation | 5 | 0.400 | 0.800 | 0.800 | 0.550 | 0.700 | – |
| consolidated_vs_standalone | 10 | 0.100 | 0.600 | 0.900 | 0.299 | 0.450 | 0.900 |
| fact | 15 | 0.133 | 0.267 | 0.467 | 0.230 | 0.267 | 0.357 |
| multi_location | 8 | 0.500 | 0.625 | 0.625 | 0.542 | 0.358 | 0.625 |
| narrative | 13 | 0.077 | 0.308 | 0.462 | 0.188 | 0.205 | 0.400 |

## By report

| Group | n | hit@1 | hit@4 | hit@10 | mrr | page_recall@4 | value_hit@4 |
|---|---|---|---|---|---|---|---|
| infosys_ar_fy25.pdf | 25 | 0.200 | 0.600 | 0.720 | 0.376 | 0.448 | 0.875 |
| tcs_ar_fy25.pdf | 26 | 0.192 | 0.308 | 0.500 | 0.253 | 0.244 | 0.333 |

## Misses at k=4 (28)

| id | category | expected pages | retrieved pages (top 10, best first) |
|---|---|---|---|
| tcs-rev-cons-01 | multi_location | [181, 230, 95] | [88, 302, 186, 238, 178, 305, 200, 200, 171, 178] |
| tcs-rev-stand-01 | consolidated_vs_standalone | [253, 287] | [302, 305, 302, 88, 258, 258, 200, 306, 262, 246] |
| tcs-pat-cons-01 | fact | [181, 184] | [88, 186, 302, 200, 181, 181, 200, 262, 171, 88] |
| tcs-eps-cons-01 | consolidated_vs_standalone | [181, 95, 23] | [229, 186, 307, 88, 300, 315, 302, 181, 200, 200] |
| tcs-eps-stand-01 | consolidated_vs_standalone | [253] | [307, 302, 300, 229, 258, 262, 258, 88, 253, 276] |
| tcs-assets-cons-01 | fact | [180] | [88, 186, 200, 302, 195, 200, 178, 185, 306, 262] |
| tcs-equity-cons-01 | fact | [180] | [186, 307, 276, 240, 203, 185, 200, 203, 88, 111] |
| tcs-headcount-01 | fact | [95] | [302, 200, 262, 200, 177, 228, 88, 228, 283, 302] |
| tcs-dividend-01 | narrative | [23] | [240, 307, 315, 108, 69, 23, 23, 186, 240, 88] |
| inf-pat-cons-01 | fact | [30, 276, 283] | [265, 277, 290, 73, 264, 339, 345, 45, 238, 265] |
| inf-eps-cons-01 | consolidated_vs_standalone | [30] | [277, 197, 249, 15, 265, 30, 332, 332, 23, 249] |
| inf-employees-01 | multi_location | [10, 22, 37, 78, 124] | [337, 257, 259, 260, 258, 258, 258, 257, 228, 215] |
| inf-special-div-01 | fact | [35] | [23, 310, 110, 110, 310, 231, 231, 228, 231, 69] |
| inf-chairman-01 | narrative | [11, 16, 197] | [12, 13, 12, 346, 11, 12, 83, 92, 180, 204] |
| inf-taxrate-cons-01 | calculation | [276] | [74, 238, 317, 30, 238, 265, 290, 345, 317, 238] |
| inf-acq-01 | narrative | [36] | [260, 258, 258, 259, 257, 260, 216, 92, 334, 216] |
| tcs-cfo-01 | narrative | [180, 181, 253] | [302, 262, 64, 306, 302, 88, 177, 64, 302, 258] |
| inf-auditor-01 | narrative | [197] | [77, 77, 108, 91, 40, 182, 188, 77, 117, 40] |
| tcs-false-decline-01 | fact | [181, 230, 95] | [186, 200, 88, 88, 302, 93, 70, 228, 22, 23] |
| tcs-rev-cons-01-para | multi_location | [181, 230, 95] | [200, 186, 88, 200, 302, 178, 177, 178, 171, 185] |
| tcs-pat-cons-01-para | fact | [181, 184] | [302, 228, 262, 200, 200, 305, 181, 88, 171, 300] |
| tcs-assets-cons-01-para | fact | [180] | [200, 200, 186, 302, 88, 195, 283, 210, 306, 230] |
| tcs-headcount-01-para | fact | [95] | [302, 262, 200, 306, 302, 305, 177, 200, 283, 228] |
| tcs-dividend-01-para | narrative | [23] | [276, 307, 302, 200, 240, 200, 276, 108, 69, 88] |
| tcs-attrition-01-para | narrative | [85, 24, 13] | [302, 262, 177, 222, 258, 167, 283, 302, 305, 305] |
| tcs-cfo-01-para | narrative | [180, 181, 253] | [99, 186, 302, 317, 185, 88, 71, 72, 106, 131] |
| inf-auditor-01-para | narrative | [197] | [77, 182, 265, 182, 57, 77, 188, 108, 272, 119] |
| inf-na-share-01-para | fact | [32] | [73, 345, 333, 334, 334, 257, 68, 322, 32, 19] |
