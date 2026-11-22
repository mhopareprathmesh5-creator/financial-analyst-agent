# Retrieval eval: para-hybrid

Run 20261121-235032 · split **dev** · 51 questions (not-in-report questions excluded: nothing to retrieve)

Config: `EMBEDDING_MODEL=BAAI/bge-small-en-v1.5`, `CHUNK_SIZE=1000`, `CHUNK_OVERLAP=200`, `CHUNK_HEADINGS=True`, `RETRIEVAL_MODE=hybrid`, `HYBRID_CANDIDATES=20`, `RRF_K=60`, `k_values=[1, 4, 10]`

Mean search latency: 0.177 s per question

## Overall

| Group | n | hit@1 | hit@4 | hit@10 | mrr | page_recall@4 | value_hit@4 |
|---|---|---|---|---|---|---|---|
| all | 51 | 0.216 | 0.412 | 0.627 | 0.326 | 0.321 | 0.459 |

## By wording

| Group | n | hit@1 | hit@4 | hit@10 | mrr | page_recall@4 | value_hit@4 |
|---|---|---|---|---|---|---|---|
| original (all) | 37 | 0.216 | 0.486 | 0.730 | 0.362 | 0.401 | 0.556 |
| original (paraphrased ones) | 14 | 0.143 | 0.429 | 0.714 | 0.290 | 0.298 | 0.500 |
| paraphrase | 14 | 0.214 | 0.214 | 0.357 | 0.232 | 0.110 | 0.200 |

## By category

| Group | n | hit@1 | hit@4 | hit@10 | mrr | page_recall@4 | value_hit@4 |
|---|---|---|---|---|---|---|---|
| calculation | 5 | 0.200 | 0.600 | 0.600 | 0.400 | 0.600 | – |
| consolidated_vs_standalone | 10 | 0.200 | 0.400 | 0.700 | 0.330 | 0.350 | 0.400 |
| fact | 15 | 0.200 | 0.267 | 0.467 | 0.251 | 0.233 | 0.286 |
| multi_location | 8 | 0.375 | 0.750 | 0.875 | 0.528 | 0.379 | 0.625 |
| narrative | 13 | 0.154 | 0.308 | 0.615 | 0.258 | 0.256 | 0.800 |

## By report

| Group | n | hit@1 | hit@4 | hit@10 | mrr | page_recall@4 | value_hit@4 |
|---|---|---|---|---|---|---|---|
| infosys_ar_fy25.pdf | 25 | 0.240 | 0.400 | 0.640 | 0.337 | 0.315 | 0.562 |
| tcs_ar_fy25.pdf | 26 | 0.192 | 0.423 | 0.615 | 0.316 | 0.327 | 0.381 |

## Misses at k=4 (30)

| id | category | expected pages | retrieved pages (top 10, best first) |
|---|---|---|---|
| tcs-rev-stand-01 | consolidated_vs_standalone | [253, 287] | [305, 23, 155, 302, 155, 258, 307, 62, 70, 137] |
| tcs-eps-cons-01 | consolidated_vs_standalone | [181, 95, 23] | [315, 88, 229, 186, 62, 23, 300, 88, 181, 69] |
| tcs-eps-stand-01 | consolidated_vs_standalone | [253] | [315, 229, 88, 307, 23, 300, 258, 258, 181, 253] |
| tcs-europe-cons-01 | consolidated_vs_standalone | [230, 95] | [6, 88, 62, 20, 230, 23, 287, 20, 89, 88] |
| tcs-assets-cons-01 | fact | [180] | [186, 195, 88, 230, 185, 273, 201, 210, 194, 190] |
| tcs-equity-cons-01 | fact | [180] | [186, 276, 203, 307, 111, 23, 88, 276, 210, 195] |
| tcs-headcount-01 | fact | [95] | [157, 157, 157, 157, 195, 152, 210, 157, 95, 151] |
| inf-rev-cons-01 | multi_location | [30, 276] | [73, 73, 345, 165, 257, 258, 30, 265, 264, 216] |
| inf-pat-cons-01 | fact | [30, 276, 283] | [265, 73, 339, 277, 65, 345, 76, 323, 15, 264] |
| inf-employees-01 | multi_location | [10, 22, 37, 78, 124] | [257, 16, 257, 4, 259, 28, 260, 337, 215, 329] |
| inf-special-div-01 | fact | [35] | [23, 310, 110, 110, 35, 231, 35, 310, 228, 51] |
| inf-chairman-01 | narrative | [11, 16, 197] | [51, 346, 204, 284, 282, 202, 12, 16, 12, 85] |
| inf-opmargin-01 | narrative | [17] | [76, 23, 228, 65, 15, 345, 17, 240, 110, 321] |
| inf-na-share-01 | fact | [32] | [73, 19, 252, 19, 334, 19, 252, 32, 335, 362] |
| inf-taxrate-cons-01 | calculation | [276] | [74, 30, 317, 345, 74, 238, 74, 238, 74, 74] |
| tcs-cfo-01 | narrative | [180, 181, 253] | [99, 98, 23, 106, 87, 317, 90, 72, 64, 186] |
| inf-auditor-01 | narrative | [197] | [77, 77, 108, 91, 77, 77, 77, 119, 180, 71] |
| inf-rev-growth-01 | calculation | [276, 30] | [73, 73, 345, 257, 74, 258, 321, 215, 165, 333] |
| tcs-false-decline-01 | fact | [181, 230, 95] | [88, 186, 62, 23, 315, 22, 155, 185, 70, 228] |
| tcs-pat-cons-01-para | fact | [181, 184] | [228, 224, 20, 297, 195, 223, 20, 297, 296, 224] |
| tcs-europe-cons-01-para | consolidated_vs_standalone | [230, 95] | [82, 90, 20, 83, 6, 83, 81, 91, 87, 81] |
| tcs-assets-cons-01-para | fact | [180] | [186, 230, 200, 200, 206, 23, 109, 164, 195, 279] |
| tcs-headcount-01-para | fact | [95] | [81, 84, 86, 6, 313, 6, 320, 195, 272, 85] |
| tcs-attrition-01-para | narrative | [85, 24, 13] | [84, 50, 62, 108, 86, 142, 85, 49, 6, 330] |
| tcs-cfo-01-para | narrative | [180, 181, 253] | [99, 87, 98, 59, 23, 186, 106, 317, 87, 277] |
| inf-auditor-01-para | narrative | [197] | [40, 193, 77, 356, 77, 3, 77, 3, 182, 3] |
| inf-acq-01-para | narrative | [36] | [17, 259, 57, 369, 57, 259, 192, 252, 60, 259] |
| inf-ocf-cons-01-para | consolidated_vs_standalone | [283] | [345, 236, 65, 122, 228, 55, 258, 79, 259, 87] |
| inf-chairman-01-para | narrative | [11, 16, 197] | [12, 85, 13, 13, 13, 12, 85, 36, 11, 12] |
| inf-na-share-01-para | fact | [32] | [334, 73, 334, 251, 333, 251, 252, 73, 28, 257] |
