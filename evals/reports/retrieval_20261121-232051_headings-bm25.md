# Retrieval eval: headings-bm25

Run 20261121-232051 · split **dev** · 37 questions (not-in-report questions excluded: nothing to retrieve)

Config: `EMBEDDING_MODEL=BAAI/bge-small-en-v1.5`, `CHUNK_SIZE=1000`, `CHUNK_OVERLAP=200`, `CHUNK_HEADINGS=True`, `RETRIEVAL_MODE=bm25`, `HYBRID_CANDIDATES=20`, `RRF_K=60`, `k_values=[1, 4, 10]`

Mean search latency: 0.236 s per question

## Overall

| Group | n | hit@1 | hit@4 | hit@10 | mrr | page_recall@4 | value_hit@4 |
|---|---|---|---|---|---|---|---|
| all | 37 | 0.297 | 0.595 | 0.730 | 0.431 | 0.450 | 0.630 |

## By category

| Group | n | hit@1 | hit@4 | hit@10 | mrr | page_recall@4 | value_hit@4 |
|---|---|---|---|---|---|---|---|
| calculation | 5 | 0.400 | 0.600 | 0.800 | 0.522 | 0.600 | – |
| consolidated_vs_standalone | 8 | 0.250 | 0.625 | 0.750 | 0.442 | 0.417 | 0.750 |
| fact | 11 | 0.273 | 0.545 | 0.545 | 0.371 | 0.500 | 0.500 |
| multi_location | 6 | 0.333 | 0.667 | 1.000 | 0.501 | 0.361 | 0.667 |
| narrative | 7 | 0.286 | 0.571 | 0.714 | 0.387 | 0.381 | 0.667 |

## By report

| Group | n | hit@1 | hit@4 | hit@10 | mrr | page_recall@4 | value_hit@4 |
|---|---|---|---|---|---|---|---|
| infosys_ar_fy25.pdf | 19 | 0.316 | 0.684 | 0.842 | 0.489 | 0.553 | 0.769 |
| tcs_ar_fy25.pdf | 18 | 0.278 | 0.500 | 0.611 | 0.370 | 0.343 | 0.500 |

## Misses at k=4 (15)

| id | category | expected pages | retrieved pages (top 10, best first) |
|---|---|---|---|
| tcs-rev-cons-01 | multi_location | [181, 230, 95] | [70, 155, 155, 88, 200, 172, 172, 155, 181, 155] |
| tcs-rev-stand-01 | consolidated_vs_standalone | [253, 287] | [155, 155, 307, 70, 155, 155, 70, 305, 155, 272] |
| tcs-eps-stand-01 | consolidated_vs_standalone | [253] | [300, 229, 181, 315, 307, 69, 319, 88, 155, 155] |
| tcs-assets-cons-01 | fact | [180] | [273, 201, 186, 230, 230, 279, 174, 171, 111, 206] |
| tcs-equity-cons-01 | fact | [180] | [111, 186, 276, 276, 171, 203, 273, 108, 203, 240] |
| tcs-headcount-01 | fact | [95] | [152, 157, 151, 159, 154, 157, 157, 273, 157, 108] |
| tcs-dividend-01 | narrative | [23] | [69, 240, 69, 307, 307, 108, 315, 23, 155, 315] |
| inf-pat-cons-01 | fact | [30, 276, 283] | [76, 323, 265, 264, 340, 339, 73, 341, 342, 76] |
| inf-eps-cons-01 | consolidated_vs_standalone | [30] | [332, 332, 277, 249, 30, 249, 15, 332, 249, 332] |
| inf-employees-01 | multi_location | [10, 22, 37, 78, 124] | [16, 4, 28, 337, 329, 28, 78, 28, 311, 337] |
| inf-taxrate-cons-01 | calculation | [276] | [74, 74, 74, 74, 74, 74, 74, 30, 135, 317] |
| tcs-cfo-01 | narrative | [180, 181, 253] | [99, 106, 317, 72, 64, 71, 317, 44, 229, 45] |
| inf-auditor-01 | narrative | [197] | [91, 77, 77, 91, 77, 91, 91, 108, 117, 356] |
| inf-rev-growth-01 | calculation | [276, 30] | [73, 73, 74, 321, 165, 73, 266, 183, 30, 266] |
| tcs-false-decline-01 | fact | [181, 230, 95] | [315, 155, 70, 172, 172, 155, 155, 155, 155, 180] |
