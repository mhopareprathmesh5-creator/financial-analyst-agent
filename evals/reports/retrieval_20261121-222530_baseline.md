# Retrieval eval: baseline

Run 20261121-222530 · split **dev** · 37 questions (not-in-report questions excluded: nothing to retrieve)

Config: `EMBEDDING_MODEL=BAAI/bge-small-en-v1.5`, `CHUNK_SIZE=1000`, `CHUNK_OVERLAP=200`, `k_values=[1, 4, 10]`

Mean search latency: 0.024 s per question

## Overall

| Group | n | hit@1 | hit@4 | hit@10 | mrr | page_recall@4 | value_hit@4 |
|---|---|---|---|---|---|---|---|
| all | 37 | 0.027 | 0.243 | 0.378 | 0.140 | 0.176 | 0.296 |

## By category

| Group | n | hit@1 | hit@4 | hit@10 | mrr | page_recall@4 | value_hit@4 |
|---|---|---|---|---|---|---|---|
| calculation | 5 | 0.000 | 0.200 | 0.200 | 0.067 | 0.200 | – |
| consolidated_vs_standalone | 8 | 0.000 | 0.375 | 0.500 | 0.182 | 0.292 | 0.375 |
| fact | 11 | 0.000 | 0.091 | 0.364 | 0.065 | 0.091 | 0.100 |
| multi_location | 6 | 0.000 | 0.333 | 0.333 | 0.167 | 0.139 | 0.167 |
| narrative | 7 | 0.143 | 0.286 | 0.429 | 0.238 | 0.190 | 1.000 |

## By report

| Group | n | hit@1 | hit@4 | hit@10 | mrr | page_recall@4 | value_hit@4 |
|---|---|---|---|---|---|---|---|
| infosys_ar_fy25.pdf | 19 | 0.000 | 0.211 | 0.316 | 0.107 | 0.175 | 0.385 |
| tcs_ar_fy25.pdf | 18 | 0.056 | 0.278 | 0.444 | 0.174 | 0.176 | 0.214 |

## Misses at k=4 (28)

| id | category | expected pages | retrieved pages (top 10, best first) |
|---|---|---|---|
| tcs-rev-cons-01 | multi_location | [181, 230, 95] | [88, 88, 70, 23, 23, 210, 22, 195, 22, 186] |
| tcs-rev-stand-01 | consolidated_vs_standalone | [253, 287] | [88, 23, 62, 88, 23, 258, 22, 253, 137, 75] |
| tcs-pat-cons-01 | fact | [181, 184] | [88, 88, 23, 89, 22, 109, 70, 186, 23, 210] |
| tcs-eps-stand-01 | consolidated_vs_standalone | [253] | [88, 23, 88, 23, 62, 315, 258, 229, 195, 109] |
| tcs-europe-cons-01 | consolidated_vs_standalone | [230, 95] | [88, 88, 20, 22, 210, 70, 22, 89, 23, 262] |
| tcs-uk-cons-01 | fact | [230] | [88, 88, 70, 22, 23, 198, 230, 89, 20, 195] |
| tcs-assets-cons-01 | fact | [180] | [186, 88, 195, 88, 210, 23, 283, 190, 89, 194] |
| tcs-equity-cons-01 | fact | [180] | [88, 186, 88, 23, 210, 195, 22, 240, 89, 109] |
| tcs-headcount-01 | fact | [95] | [195, 210, 88, 88, 95, 22, 186, 23, 22, 200] |
| tcs-margin-cons-01 | calculation | [181] | [88, 88, 23, 22, 70, 22, 186, 23, 210, 89] |
| inf-rev-cons-01 | multi_location | [30, 276] | [73, 47, 196, 237, 46, 265, 242, 68, 257, 45] |
| inf-pat-cons-01 | fact | [30, 276, 283] | [73, 47, 196, 45, 48, 46, 265, 43, 339, 15] |
| inf-pat-stand-01 | consolidated_vs_standalone | [30, 203] | [47, 73, 182, 238, 318, 48, 45, 23, 44, 196] |
| inf-eps-cons-01 | consolidated_vs_standalone | [30] | [23, 47, 265, 46, 43, 48, 15, 214, 45, 339] |
| inf-employees-01 | multi_location | [10, 22, 37, 78, 124] | [257, 260, 259, 228, 258, 256, 215, 42, 334, 232] |
| inf-special-div-01 | fact | [35] | [23, 310, 110, 110, 51, 69, 202, 17, 214, 259] |
| inf-chairman-01 | narrative | [11, 16, 197] | [346, 83, 12, 204, 282, 11, 284, 202, 12, 14] |
| inf-opmargin-01 | narrative | [17] | [228, 23, 73, 47, 48, 46, 212, 107, 96, 45] |
| inf-na-share-01 | fact | [32] | [46, 48, 47, 43, 73, 45, 44, 48, 42, 96] |
| inf-taxrate-cons-01 | calculation | [276] | [237, 73, 318, 96, 228, 238, 47, 350, 65, 48] |
| inf-attrition-01 | fact | [135] | [228, 73, 47, 45, 107, 46, 150, 135, 43, 44] |
| inf-acq-01 | narrative | [36] | [254, 257, 51, 260, 337, 259, 51, 258, 42, 260] |
| inf-locations-01 | multi_location | [36, 115] | [333, 251, 47, 334, 335, 260, 369, 46, 48, 252] |
| tcs-cfo-01 | narrative | [180, 181, 253] | [88, 129, 23, 88, 23, 94, 134, 87, 87, 87] |
| inf-auditor-01 | narrative | [197] | [119, 282, 108, 180, 202, 277, 57, 39, 29, 77] |
| tcs-americas-share-01 | calculation | [230] | [88, 88, 186, 23, 22, 89, 62, 195, 109, 70] |
| inf-rev-growth-01 | calculation | [276, 30] | [73, 47, 257, 266, 46, 237, 68, 45, 23, 43] |
| tcs-false-decline-01 | fact | [181, 230, 95] | [88, 22, 88, 22, 89, 23, 210, 93, 23, 186] |

## Indexing (first run for this config)

- infosys_ar_fy25.pdf: 369 pages, 1570 chunks, read 59.9 s, embed 242.8 s
- tcs_ar_fy25.pdf: 336 pages, 1415 chunks, read 122.4 s, embed 211.6 s
