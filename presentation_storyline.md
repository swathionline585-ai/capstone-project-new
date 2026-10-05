# Presentation storyline

## Executive audience
### Situation
The validated order dataset covers 2,100 orders across April–June 2026. Guntur sales were ₹62,442.27 in April and ₹138,738.93 in May.
### Complication
Guntur's +122.19% April→May change is the largest absolute flagged transition. Its -28.11% May→June change cautions against treating the rise as sustained.
### Resolution
The regional lead should review order composition within one working day of reviewing this report, before operational action. The narrative and recommendation require explicit human approval for downstream use.

## Regional manager audience
### Overview
Guntur's April→May sales increased ₹76,296.66, or 122.19%. Its order count rose from 51 to 77.
### Category
Wellness & Nutrition contributes the most to the increase: ₹33,787.42 (44.28% of the total increase). Medical Devices contributes ₹23,276.06. These are measured contributions, not external causal explanations.
### Detail
Sales are SQL sums by region and month from the exact cleaned orders. MoM is (current − previous) / previous × 100. Deduplication removes 59 exact copies; category lookup restores 48 categories; category mean margins estimate 94 profits. Sales growth is unaffected by profit imputation. Compare the dashboard's category-by-month table, monthly distinct orders, and order values. June sales are ₹99,745.18 across 62 orders.

## Anticipated pushback
### Why should I believe this number?
1. Acknowledge: A more-than-doubling result merits checking.
2. Verified versus unverified: SQL gives ₹62,442.27 and ₹138,738.93, producing +122.19%. These figures are verified against the supplied orders; the underlying cause has not been established.
3. Resolve and timing: Reconcile Guntur's order IDs and category totals within one working day of human review, before action.

### What if an alternative explanation is driving this?
1. Acknowledge: More orders and different order values or mix can produce the same regional increase.
2. Verified versus unverified: Orders increased 51→77; category contributions are measurable. Promotions, competitor actions, and customer motivations are not verified.
3. Resolve and timing: Compare category-month orders and average order value within one working day of human review. Keep external explanations as hypotheses unless separate evidence is obtained.

### What would change your recommendation?
1. Acknowledge: A data error or a reconciled operational explanation could change the next step.
2. Verified versus unverified: The current recommendation is investigation; three months of data do not establish sustained growth or causality.
3. Resolve and timing: If reconciliation finds an error, correct the data and rerun review immediately before downstream use. If a verified explanation is available, revise and reapprove the recommendation within one working day of that evidence arriving.

### What did you not check?
1. Acknowledge: Regional aggregation alone cannot answer every business question.
2. Verified versus unverified: Counts, sales, category contributions, and imputed-profit methods are checked. External market conditions and true values of missing profits are not known.
3. Resolve and timing: Complete available order-level checks within one working day of human review. Assign external evidence gathering only if needed, and keep the recommendation provisional until it is reviewed.

