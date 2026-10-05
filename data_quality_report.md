# Data quality report

The deterministic raw dataset contains 2,159 rows. Deduplication removes 59 copies, leaving 2,100 orders. Sixteen raw region variants become nine active canonical names. Category lookup fills 48 missing categories; category mean margins estimate 94 missing profits. No required values remain missing.

| Dimension | Implemented action and limit |
|---|---|
| Accuracy | Exact product lookup recovers category; profit estimates use observed category margins but do not recover verified original profits. |
| Completeness | Missing categories and profits are filled without dropping affected orders. |
| Consistency | Region text is stripped and title-cased; a common schema is used downstream. |
| Timeliness | Dates are preserved; no external freshness or export-latency evidence is available. |
| Validity | Required columns, canonical regions, numeric fields, positive sales/quantity, date parsing, and unambiguous product mappings are checked. |
| Uniqueness | Exact duplicate rows are removed first; remaining duplicate order IDs block processing. |
| Relevance | Required order, date, region, category, product, quantity, sales, and profit fields are retained for the analysis. |

Cleaning order: deduplicate → normalize region → restore category → estimate profit. Category mean margin is the unweighted mean of observed profit/sales ratios, not the ratio of total profit to total sales. Missing categories must be restored before margin grouping. Schema validation returns `validated` for the clean data and `blocked_schema` with `profit_inr` for the deliberately broken copy. Evidence is saved in `output/cleaning_checks.json` and printed by `clean_data.py`.
