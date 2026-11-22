# Retrieval eval: headings

Run 20261121-225734 · split **dev** · 37 questions (not-in-report questions excluded: nothing to retrieve)

Config: `EMBEDDING_MODEL=BAAI/bge-small-en-v1.5`, `CHUNK_SIZE=1000`, `CHUNK_OVERLAP=200`, `CHUNK_HEADINGS=True`, `k_values=[1, 4, 10]`

Mean search latency: 0.039 s per question

## Overall

| Group | n | hit@1 | hit@4 | hit@10 | mrr | page_recall@4 | value_hit@4 |
|---|---|---|---|---|---|---|---|
| all | 37 | 0.135 | 0.297 | 0.405 | 0.200 | 0.248 | 0.370 |

## By category

| Group | n | hit@1 | hit@4 | hit@10 | mrr | page_recall@4 | value_hit@4 |
|---|---|---|---|---|---|---|---|
| calculation | 5 | 0.000 | 0.200 | 0.200 | 0.050 | 0.200 | – |
| consolidated_vs_standalone | 8 | 0.250 | 0.500 | 0.875 | 0.367 | 0.417 | 0.375 |
| fact | 11 | 0.091 | 0.273 | 0.273 | 0.144 | 0.273 | 0.400 |
| multi_location | 6 | 0.167 | 0.333 | 0.333 | 0.250 | 0.139 | 0.167 |
| narrative | 7 | 0.143 | 0.143 | 0.286 | 0.161 | 0.143 | 0.667 |

## By report

| Group | n | hit@1 | hit@4 | hit@10 | mrr | page_recall@4 | value_hit@4 |
|---|---|---|---|---|---|---|---|
| infosys_ar_fy25.pdf | 19 | 0.053 | 0.211 | 0.368 | 0.128 | 0.175 | 0.462 |
| tcs_ar_fy25.pdf | 18 | 0.222 | 0.389 | 0.444 | 0.275 | 0.324 | 0.286 |

## Misses at k=4 (26)

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

## Indexing (first run for this config)

- infosys_ar_fy25.pdf: 369 pages, 1570 chunks, read 52.0 s, embed 230.5 s
- tcs_ar_fy25.pdf: 336 pages, 1415 chunks, read 207.0 s, embed 280.8 s
