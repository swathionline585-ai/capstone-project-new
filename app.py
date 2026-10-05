"""Show the regional dashboard after command-line report approval."""
import json
import os
import sqlite3
from contextlib import closing
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from draft_report import data_fingerprint

ROOT = Path(os.environ.get("PHARMEASY_PROJECT_DIR", Path(__file__).resolve().parent))
OUTPUT_DIR = ROOT / "output"
MONTHS = ["2026-04", "2026-05", "2026-06"]


def read_json(filename):
    file_path = OUTPUT_DIR / filename
    if not file_path.exists():
        return {}
    return json.loads(file_path.read_text(encoding="utf-8"))


st.set_page_config(page_title="PharmEasy Regional Pulse", layout="wide")
st.title("PharmEasy Regional Pulse")
st.caption("Regional sales and orders, April–June 2026.")

draft = read_json("draft_report.json")
required_files = ["pharmeasy.db", "orders_clean.csv", "regions_master.csv"]
files_ready = True
for filename in required_files:
    if not (OUTPUT_DIR / filename).exists():
        files_ready = False
if not draft or not files_ready:
    st.info("Run python pipeline.py to prepare the data and review package.")
    st.stop()

if draft["data_fingerprint"] != data_fingerprint():
    st.error("The cleaned data changed after drafting. Rerun python pipeline.py and review the new package.")
    st.stop()

reviewed = read_json("reviewed_report.json")
is_approved = reviewed.get("review_decision") == "approve"
use_allowed = reviewed.get("external_use_allowed", False)
same_report = reviewed.get("content_fingerprint") == draft["content_fingerprint"]
same_data = reviewed.get("data_fingerprint") == draft["data_fingerprint"]
if not (is_approved and use_allowed and same_report and same_data):
    st.warning("Run python pipeline.py in your terminal and approve the report before opening the dashboard.")
    st.stop()
st.success("Approved by: " + reviewed["reviewer_note"])

# Open an existing database without accidentally creating an empty one.
database_uri = (OUTPUT_DIR / "pharmeasy.db").as_uri() + "?mode=ro"
with closing(sqlite3.connect(database_uri, uri=True)) as connection:
    orders = pd.read_sql_query("SELECT * FROM orders_clean", connection)
    region_master = pd.read_sql_query("SELECT * FROM regions_master", connection)
regions = sorted(region_master["region"].tolist())
clean_csv = pd.read_csv(OUTPUT_DIR / "orders_clean.csv")
master_csv = pd.read_csv(OUTPUT_DIR / "regions_master.csv")
if not orders.equals(clean_csv) or not region_master.equals(master_csv):
    st.error("SQLite orders differ from the approved clean CSV. Rebuild and review the pipeline.")
    st.stop()

orders["month"] = pd.to_datetime(orders["order_date"]).dt.to_period("M").astype(str)
metrics = reviewed["metrics"]
st.subheader("Executive summary")
st.markdown(reviewed["executive_summary"])

selected_region = st.sidebar.selectbox("Region", ["All Regions"] + regions)
if selected_region == "All Regions":
    filtered_orders = orders
    visible_regions = regions
else:
    filtered_orders = orders[orders["region"] == selected_region]
    visible_regions = [selected_region]
st.sidebar.caption("All overview, category, and detail views use this region selection. The executive summary remains a desk-wide overview.")

st.header("1. Overview")
sales_column, profit_column, orders_column = st.columns(3)
sales_column.metric("Sales (INR)", f"₹{filtered_orders['sales_inr'].sum():,.2f}")
profit_column.metric("Profit including estimates (INR)", f"₹{filtered_orders['profit_inr'].sum():,.2f}")
orders_column.metric("Distinct orders", f"{filtered_orders['order_id'].nunique():,}")
if filtered_orders.empty:
    st.info(f"{selected_region} has no orders in this period; zero is a valid result.")

# Reindex adds zero monthly rows for regions such as Kurnool.
region_month_grid = pd.MultiIndex.from_product([visible_regions, MONTHS], names=["region", "month"])
monthly_sales = filtered_orders.groupby(["region", "month"], as_index=False)["sales_inr"].sum()
monthly_sales = monthly_sales.set_index(["region", "month"])
monthly_sales = monthly_sales.reindex(region_month_grid, fill_value=0).reset_index()
monthly_sales["month"] = pd.to_datetime(monthly_sales["month"])
region_colors = {}
for index, region in enumerate(regions):
    region_colors[region] = px.colors.qualitative.Safe[index]
region_colors["Guntur"] = "#B45309"
trend_chart = px.line(
    monthly_sales,
    x="month",
    y="sales_inr",
    color="region",
    markers=True,
    color_discrete_map=region_colors,
    labels={"month": "Month", "sales_inr": "Sales (INR)", "region": "Region"},
    title="How did regional monthly sales change from April to June?",
)
trend_chart.update_yaxes(rangemode="tozero")
st.plotly_chart(trend_chart, width="stretch")

if selected_region == "All Regions":
    region_sales = filtered_orders.groupby("region")["sales_inr"].sum()
    region_sales = region_sales.reindex(visible_regions, fill_value=0).reset_index()
    focus_labels = []
    for region in region_sales["region"]:
        if region == "Guntur":
            focus_labels.append("Guntur review focus")
        else:
            focus_labels.append("Other regions")
    region_sales["focus"] = focus_labels
    region_chart = px.bar(
        region_sales,
        x="region",
        y="sales_inr",
        color="focus",
        color_discrete_map={"Guntur review focus": "#B45309", "Other regions": "#64748B"},
        labels={"region": "Region", "sales_inr": "Sales (INR)", "focus": "Review focus"},
        title="Which regions generated the most April–June sales?",
    )
    region_chart.update_yaxes(rangemode="tozero")
    st.plotly_chart(region_chart, width="stretch")
    st.caption("Guntur is highlighted as the largest flagged transition. Other flags are listed in the detail table.")

st.header("2. Category")
category_totals = filtered_orders.groupby("category", as_index=False).agg(
    sales_inr=("sales_inr", "sum"),
    profit_inr=("profit_inr", "sum"),
    distinct_orders=("order_id", "nunique"),
)
st.dataframe(category_totals.round(2), hide_index=True, width="stretch")
if selected_region != "All Regions" and not category_totals.empty:
    category_comparison = category_totals.sort_values("sales_inr")
    category_chart = px.bar(
        category_comparison,
        x="sales_inr",
        y="category",
        orientation="h",
        labels={"sales_inr": "Sales (INR)", "category": "Category"},
        title=f"Which categories generated the most April–June sales in {selected_region}?",
    )
    category_chart.update_traces(marker_color="#64748B")
    category_chart.update_xaxes(rangemode="tozero")
    category_chart.update_layout(showlegend=False)
    st.plotly_chart(category_chart, width="stretch")
if not category_totals.empty:
    share_chart = px.pie(
        category_totals,
        names="category",
        values="sales_inr",
        hole=0.45,
        title="What share of April–June sales (INR) comes from each category?",
        labels={"sales_inr": "Sales (INR)", "category": "Category"},
        color_discrete_sequence=px.colors.qualitative.Safe,
    )
    share_chart.update_traces(
        textinfo="label+percent",
        hovertemplate="%{label}<br>Sales: ₹%{value:,.2f}<br>Share: %{percent}<extra></extra>",
    )
    st.plotly_chart(share_chart, width="stretch")

category_by_month = filtered_orders.groupby(["category", "month"])["sales_inr"].sum()
category_by_month = category_by_month.unstack("month")
category_by_month = category_by_month.reindex(columns=MONTHS, fill_value=0).fillna(0)
category_by_month["April→May change (INR)"] = category_by_month["2026-05"] - category_by_month["2026-04"]
st.subheader("Which categories contributed to the April→May sales change?")
st.dataframe(category_by_month.round(2), width="stretch")

st.header("3. Region and month detail")
monthly_detail = filtered_orders.groupby(["region", "month"]).agg(
    sales_inr=("sales_inr", "sum"),
    profit_inr=("profit_inr", "sum"),
    distinct_orders=("order_id", "nunique"),
)
monthly_detail = monthly_detail.reindex(region_month_grid, fill_value=0).reset_index()
changes_by_month = {}
flags_by_month = {}
for transition in metrics["transitions"]:
    changes_by_month[transition["month"]] = transition["changes"]
    flags_by_month[transition["month"]] = transition["flags"]
percentage_changes = []
alert_flags = []
for _, row in monthly_detail.iterrows():
    month_changes = changes_by_month.get(row["month"], {})
    month_flags = flags_by_month.get(row["month"], {})
    percentage_changes.append(month_changes.get(row["region"]))
    alert_flags.append(month_flags.get(row["region"], False))
monthly_detail["MoM change (%)"] = percentage_changes
monthly_detail["Operational alert"] = alert_flags
st.dataframe(monthly_detail.round(2), hide_index=True, width="stretch")
st.caption("April has no prior baseline. Zero-baseline percentage change is defined as 0 by the specification. Profit contains 94 category-margin estimates; these are not observed original profits.")

st.subheader("Approved Context–Insight–Implication narratives")
visible_reports = []
for report in reviewed["reports"]:
    if selected_region == "All Regions" or report["region"] == selected_region:
        visible_reports.append(report)
if not visible_reports:
    st.info("This region has no operational alerts across either transition.")
for report in visible_reports:
    with st.expander(report["region"]):
        st.write("Context: " + report["context"])
        st.write("Insight: " + report["insight"])
        st.write("Implication: " + report["implication"])
with st.expander("Approved recommendation memo"):
    st.markdown(reviewed["memo"])
with st.expander("Approved presentation storyline"):
    st.markdown(reviewed["storyline"])
