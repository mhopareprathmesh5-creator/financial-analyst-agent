# Retrieval eval: para-vector

Run 20261121-234959 · split **dev** · 51 questions (not-in-report questions excluded: nothing to retrieve)

Config: `EMBEDDING_MODEL=BAAI/bge-small-en-v1.5`, `CHUNK_SIZE=1000`, `CHUNK_OVERLAP=200`, `CHUNK_HEADINGS=True`, `RETRIEVAL_MODE=vector`, `HYBRID_CANDIDATES=20`, `RRF_K=60`, `k_values=[1, 4, 10]`

Mean search latency: 0.162 s per question

## Overall

| Group | n | hit@1 | hit@4 | hit@10 | mrr | page_recall@4 | value_hit@4 |
|---|---|---|---|---|---|---|---|
| all | 51 | 0.137 | 0.275 | 0.392 | 0.194 | 0.210 | 0.351 |

## By wording

| Group | n | hit@1 | hit@4 | hit@10 | mrr | page_recall@4 | value_hit@4 |
|---|---|---|---|---|---|---|---|
| original (all) | 37 | 0.135 | 0.297 | 0.405 | 0.200 | 0.248 | 0.370 |
| original (paraphrased ones) | 14 | 0.143 | 0.214 | 0.286 | 0.176 | 0.214 | 0.300 |
| paraphrase | 14 | 0.143 | 0.214 | 0.357 | 0.180 | 0.110 | 0.300 |

## By category

| Group | n | hit@1 | hit@4 | hit@10 | mrr | page_recall@4 | value_hit@4 |
|---|---|---|---|---|---|---|---|
| calculation | 5 | 0.000 | 0.200 | 0.200 | 0.050 | 0.200 | – |
| consolidated_vs_standalone | 10 | 0.200 | 0.400 | 0.700 | 0.293 | 0.333 | 0.300 |
| fact | 15 | 0.067 | 0.200 | 0.200 | 0.106 | 0.200 | 0.286 |
| multi_location | 8 | 0.250 | 0.375 | 0.500 | 0.333 | 0.129 | 0.250 |
| narrative | 13 | 0.154 | 0.231 | 0.385 | 0.190 | 0.179 | 0.800 |

## By report

| Group | n | hit@1 | hit@4 | hit@10 | mrr | page_recall@4 | value_hit@4 |
|---|---|---|---|---|---|---|---|
| infosys_ar_fy25.pdf | 25 | 0.080 | 0.200 | 0.360 | 0.141 | 0.141 | 0.438 |
| tcs_ar_fy25.pdf | 26 | 0.192 | 0.346 | 0.423 | 0.245 | 0.276 | 0.286 |

## Misses at k=4 (37)

| id | category | expected pages | retrieved pages (top 10, best first) |
|---|---|---|---|
| tcs-rev-cons-01 | multi_location | [181, 230, 95] | [23, 88, 185, 238, 186, 228, 302, 20, 88, 296] |
| tcs-rev-stand-01 | consolidated_vs_standalone | [253, 287] | [23, 302, 258, 62, 137, 258, 296, 253, 130, 23] |
| tcs-pat-cons-01 | fact | [181, 184] | [23, 88, 20, 186, 88, 22, 89, 23, 109, 185] |
| tcs-europe-cons-01 | consolidated_vs_standalone | [230, 95] | [20, 23, 20, 88, 88, 210, 87, 130, 22, 195] |
| tcs-assets-cons-01 | fact | [180] | [186, 195, 210, 194, 190, 88, 185, 23, 200, 184] |
| tcs-equity-cons-01 | fact | [180] | [186, 23, 88, 210, 195, 185, 302, 276, 200, 200] |
| tcs-margin-cons-01 | calculation | [181] | [22, 23, 88, 88, 186, 20, 89, 62, 23, 302] |
| inf-rev-cons-01 | multi_location | [30, 276] | [73, 345, 257, 258, 265, 216, 322, 216, 259, 10] |
| inf-pat-cons-01 | fact | [30, 276, 283] | [345, 73, 277, 15, 265, 257, 333, 339, 196, 238] |
| inf-pat-stand-01 | consolidated_vs_standalone | [30, 203] | [238, 345, 238, 182, 240, 30, 290, 73, 15, 196] |
| inf-ocf-stand-01 | consolidated_vs_standalone | [203] | [283, 205, 182, 51, 65, 216, 203, 33, 216, 228] |
| inf-employees-01 | multi_location | [10, 22, 37, 78, 124] | [257, 257, 259, 260, 215, 258, 257, 334, 258, 258] |
| inf-special-div-01 | fact | [35] | [23, 110, 310, 110, 228, 51, 238, 202, 216, 73] |
| inf-chairman-01 | narrative | [11, 16, 197] | [12, 12, 13, 12, 83, 14, 13, 11, 51, 12] |
| inf-opmargin-01 | narrative | [17] | [228, 65, 345, 76, 110, 257, 259, 258, 42, 216] |
| inf-na-share-01 | fact | [32] | [73, 252, 334, 252, 335, 254, 43, 48, 345, 215] |
| inf-taxrate-cons-01 | calculation | [276] | [74, 345, 238, 238, 30, 290, 318, 73, 257, 317] |
| tcs-attrition-01 | narrative | [85, 24, 13] | [84, 158, 62, 84, 154, 6, 228, 140, 84, 155] |
| inf-attrition-01 | fact | [135] | [73, 107, 150, 78, 108, 228, 110, 45, 43, 353] |
| inf-acq-01 | narrative | [36] | [258, 254, 257, 258, 215, 334, 216, 259, 260, 252] |
| inf-locations-01 | multi_location | [36, 115] | [252, 334, 259, 335, 334, 252, 260, 369, 257, 51] |
| tcs-cfo-01 | narrative | [180, 181, 253] | [99, 23, 87, 90, 98, 186, 87, 86, 302, 87] |
| inf-auditor-01 | narrative | [197] | [119, 77, 180, 71, 77, 77, 282, 108, 77, 77] |
| tcs-americas-share-01 | calculation | [230] | [23, 20, 186, 228, 130, 6, 109, 6, 87, 195] |
| inf-rev-growth-01 | calculation | [276, 30] | [73, 345, 257, 258, 215, 333, 216, 65, 17, 259] |
| tcs-false-decline-01 | fact | [181, 230, 95] | [23, 22, 185, 228, 186, 88, 88, 20, 93, 23] |
| tcs-rev-cons-01-para | multi_location | [181, 230, 95] | [186, 109, 81, 88, 210, 230, 23, 302, 136, 87] |
| tcs-pat-cons-01-para | fact | [181, 184] | [228, 20, 195, 20, 296, 131, 23, 88, 85, 148] |
| tcs-europe-cons-01-para | consolidated_vs_standalone | [230, 95] | [20, 6, 81, 87, 81, 130, 302, 87, 20, 82] |
| tcs-assets-cons-01-para | fact | [180] | [186, 23, 109, 195, 88, 210, 200, 302, 200, 185] |
| tcs-headcount-01-para | fact | [95] | [84, 6, 6, 195, 85, 93, 210, 81, 87, 85] |
| tcs-cfo-01-para | narrative | [180, 181, 253] | [99, 23, 186, 87, 87, 86, 90, 302, 129, 134] |
| inf-auditor-01-para | narrative | [197] | [77, 77, 77, 182, 205, 40, 202, 39, 282, 17] |
| inf-acq-01-para | narrative | [36] | [259, 369, 259, 252, 259, 260, 258, 109, 254, 36] |
| inf-ocf-cons-01-para | consolidated_vs_standalone | [283] | [345, 65, 228, 258, 259, 43, 110, 73, 257, 216] |
| inf-chairman-01-para | narrative | [11, 16, 197] | [12, 83, 13, 12, 12, 13, 12, 85, 13, 97] |
| inf-na-share-01-para | fact | [32] | [73, 333, 252, 334, 257, 334, 215, 258, 345, 251] |
