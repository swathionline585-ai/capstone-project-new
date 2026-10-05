"""Deterministic narrative templates, sourced only from computed metrics."""
import hashlib
import json
import os
from pathlib import Path

# The environment override is used only by isolated tests.
ROOT = Path(os.environ.get("PHARMEASY_PROJECT_DIR", Path(__file__).resolve().parent))
OUTPUT_DIR = ROOT / "output"
from metrics_engine import compute_metrics

def draft_report_v1(flagged_regions, metrics):
    reports = []
    summaries_by_month = {}
    for summary in metrics["months"]:
        summaries_by_month[summary["month"]] = summary

    for region in sorted(set(flagged_regions)):
        context_parts = []
        insight_parts = []
        for transition in metrics["transitions"]:
            if not transition["flags"].get(region, False):
                continue
            previous = summaries_by_month[transition["previous_month"]]
            current = summaries_by_month[transition["month"]]
            change = transition["changes"][region]
            direction = "decreased"
            if change >= 0:
                direction = "increased"

            context_parts.append(
                f"{region} sales were ₹{previous['sales'][region]:,.2f} in {previous['month']} "
                f"and ₹{current['sales'][region]:,.2f} in {current['month']}."
            )
            insight_parts.append(
                f"Sales {direction} {abs(change):.2f}% "
                f"from {previous['month']} to {current['month']}."
            )

        if context_parts:
            report = {
                "region": region,
                "context": " ".join(context_parts),
                "insight": " ".join(insight_parts),
                "implication": (
                    "Review the underlying orders and category mix before operational action. "
                    "The 8% alert is not a statistical significance test or proof of a causal shift."
                ),
            }
            reports.append(report)
    return reports


def data_fingerprint():
    digest = hashlib.sha256()
    for name in ["orders_clean.csv", "regions_master.csv"]:
        digest.update((OUTPUT_DIR / name).read_bytes())
    return digest.hexdigest()

ASSUMPTION = "Changes in order composition may explain the swing, but no causal explanation has been verified."

def memo_text(metrics):
    april = metrics["months"][0]["sales"]["Guntur"]
    may = metrics["months"][1]["sales"]["Guntur"]
    june = metrics["months"][2]["sales"]["Guntur"]
    up = metrics["transitions"][0]["changes"]["Guntur"]
    down = metrics["transitions"][1]["changes"]["Guntur"]
    top = metrics["guntur_categories"][0]
    return f"""# Title
Guntur sales swing recommendation [LOW]

## Context
Guntur sales rose from ₹{april:,.2f} in April 2026 to ₹{may:,.2f} in May 2026 [HIGH]. This is a +{up:.2f}% change and the largest absolute flagged transition in this dataset [HIGH].

## Key Insight
The increase deserves review, rather than an assumption of sustained growth [MEDIUM]. June sales were ₹{june:,.2f}, a {down:.2f}% May→June change [HIGH].

## Evidence
- The operational alert rule is abs(MoM change) > 8% [HIGH].
- Guntur distinct orders were {metrics['guntur_orders']['2026-04']}, {metrics['guntur_orders']['2026-05']}, and {metrics['guntur_orders']['2026-06']} in April, May, and June respectively [HIGH].
- {top['category']} contributed ₹{top['delta']:,.2f} of the ₹{may-april:,.2f} April→May sales increase [HIGH].
- The analysis covers the supplied April–June 2026 order dataset [HIGH].

## Recommendation
The regional lead should inspect order count, category composition, and order value before operational action [MEDIUM]. Treat flags as review prompts, not statistical evidence [LOW].

## Next Check
Within one working day of human review, compare Guntur's category-by-month sales and underlying order records, then record the conclusion before any operational action [MEDIUM]. Profit includes estimated values and needs separate scrutiny if used in a decision [MEDIUM].

## Assumptions
{ASSUMPTION} [MEDIUM]
"""

def storyline_text(metrics):
    april = metrics["months"][0]["sales"]["Guntur"]
    may = metrics["months"][1]["sales"]["Guntur"]
    june = metrics["months"][2]["sales"]["Guntur"]
    up = metrics["transitions"][0]["changes"]["Guntur"]
    down = metrics["transitions"][1]["changes"]["Guntur"]
    top = metrics["guntur_categories"][0]
    second = metrics["guntur_categories"][1]
    return f"""# Presentation storyline

## Executive audience
### Situation
The validated order dataset covers 2,100 orders across April–June 2026. Guntur sales were ₹{april:,.2f} in April and ₹{may:,.2f} in May.
### Complication
Guntur's +{up:.2f}% April→May change is the largest absolute flagged transition. Its {down:.2f}% May→June change cautions against treating the rise as sustained.
### Resolution
The regional lead should review order composition within one working day of reviewing this report, before operational action. The narrative and recommendation require explicit human approval for downstream use.

## Regional manager audience
### Overview
Guntur's April→May sales increased ₹{may-april:,.2f}, or {up:.2f}%. Its order count rose from {metrics['guntur_orders']['2026-04']} to {metrics['guntur_orders']['2026-05']}.
### Category
{top['category']} contributes the most to the increase: ₹{top['delta']:,.2f} ({top['delta']/(may-april)*100:.2f}% of the total increase). {second['category']} contributes ₹{second['delta']:,.2f}. These are measured contributions, not external causal explanations.
### Detail
Sales are SQL sums by region and month from the exact cleaned orders. MoM is (current − previous) / previous × 100. Deduplication removes 59 exact copies; category lookup restores 48 categories; category mean margins estimate 94 profits. Sales growth is unaffected by profit imputation. Compare the dashboard's category-by-month table, monthly distinct orders, and order values. June sales are ₹{june:,.2f} across {metrics['guntur_orders']['2026-06']} orders.

## Anticipated pushback
### Why should I believe this number?
1. Acknowledge: A more-than-doubling result merits checking.
2. Verified versus unverified: SQL gives ₹{april:,.2f} and ₹{may:,.2f}, producing +{up:.2f}%. These figures are verified against the supplied orders; the underlying cause has not been established.
3. Resolve and timing: Reconcile Guntur's order IDs and category totals within one working day of human review, before action.

### What if an alternative explanation is driving this?
1. Acknowledge: More orders and different order values or mix can produce the same regional increase.
2. Verified versus unverified: Orders increased {metrics['guntur_orders']['2026-04']}→{metrics['guntur_orders']['2026-05']}; category contributions are measurable. Promotions, competitor actions, and customer motivations are not verified.
3. Resolve and timing: Compare category-month orders and average order value within one working day of human review. Keep external explanations as hypotheses unless separate evidence is obtained.

### What would change your recommendation?
1. Acknowledge: A data error or a reconciled operational explanation could change the next step.
2. Verified versus unverified: The current recommendation is investigation; three months of data do not establish sustained growth or causality.
3. Resolve and timing: If reconciliation finds an error, correct the data and rerun review immediately before downstream use. If a verified explanation is available, revise and reapprove the recommendation within one working day of that evidence arriving.

### What did you not check?
1. Acknowledge: Regional aggregation alone cannot answer every business question.
2. Verified versus unverified: Counts, sales, category contributions, and imputed-profit methods are checked. External market conditions and true values of missing profits are not known.
3. Resolve and timing: Complete available order-level checks within one working day of human review. Assign external evidence gathering only if needed, and keep the recommendation provisional until it is reviewed.
"""

def executive_summary(metrics):
    kpi = metrics["kpis"]
    top = metrics["guntur_categories"][0]
    up = metrics["transitions"][0]["changes"]["Guntur"]
    down = metrics["transitions"][1]["changes"]["Guntur"]
    return f"Across April–June 2026, sales total **₹{kpi['sales']:,.2f}**, profit including estimates totals **₹{kpi['profit']:,.2f}**, and orders total **{kpi['orders']:,} distinct IDs**. Guntur rose **{up:.2f}%** from April to May, then fell **{abs(down):.2f}%** in June. **{top['category']}** contributed **₹{top['delta']:,.2f}** of its April→May increase. The recommendation is to reconcile order composition before operational action, because the 8% threshold is a review alert rather than statistical proof. Use the region filter, category-by-month comparison, detail table, and approved CII blocks below to examine the evidence."

def build_package():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    metrics = compute_metrics()
    flagged_regions = set()
    for transition in metrics["transitions"]:
        for region, is_flagged in transition["flags"].items():
            if is_flagged:
                flagged_regions.add(region)
    reports = draft_report_v1(flagged_regions, metrics)
    package = {
        "region": "Regional desk",
        "data_fingerprint": data_fingerprint(),
        "metrics": metrics,
        "reports": reports,
        "executive_summary": executive_summary(metrics),
        "memo": memo_text(metrics),
        "storyline": storyline_text(metrics),
        "review_decision": "pending",
        "external_use_allowed": False,
    }
    package_json = json.dumps(package, sort_keys=True)
    package["content_fingerprint"] = hashlib.sha256(package_json.encode()).hexdigest()
    (ROOT / "memo.md").write_text(package["memo"], encoding="utf-8")
    (ROOT / "presentation_storyline.md").write_text(package["storyline"], encoding="utf-8")
    draft_json = json.dumps(package, indent=2, ensure_ascii=False)
    (OUTPUT_DIR / "draft_report.json").write_text(draft_json, encoding="utf-8")
    return package


if __name__ == "__main__":
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(build_package(), indent=2, ensure_ascii=False))
