"""Calculate monthly sales, operational alerts, and saved state."""
import argparse
import json
import os
import sqlite3
from contextlib import closing
from pathlib import Path

import pandas as pd

from clean_data import REQUIRED_COLUMNS, validate_schema

ROOT = Path(os.environ.get("PHARMEASY_PROJECT_DIR", Path(__file__).resolve().parent))
OUTPUT_DIR = ROOT / "output"


def compute_percentage_change_v1(current, previous):
    if previous == 0:
        return 0
    difference = current - previous
    return difference / previous * 100


def flag_significant_regions_v1(changes, threshold=8):
    flags = {}
    for region, percentage_change in changes.items():
        flags[region] = abs(percentage_change) > threshold
    return flags


def save_state_v1(month_summary, path):
    state_file = Path(path)
    state_file.parent.mkdir(parents=True, exist_ok=True)
    temporary_file = state_file.with_suffix(state_file.suffix + ".tmp")
    state_json = json.dumps(month_summary, indent=2)
    temporary_file.write_text(state_json, encoding="utf-8")
    # Replace the old state only after the new file has been written.
    temporary_file.replace(state_file)


def load_previous_state_v1(path):
    state_file = Path(path)
    if not state_file.exists():
        return {}
    state_json = state_file.read_text(encoding="utf-8")
    return json.loads(state_json)


def monthly_summary(month, orders=None):
    if orders is None:
        connection = sqlite3.connect(OUTPUT_DIR / "pharmeasy.db")
    else:
        schema_result = validate_schema(orders, REQUIRED_COLUMNS)
        if schema_result["status"] != "validated":
            raise ValueError("New-month orders have a blocked schema")
        if orders[REQUIRED_COLUMNS].isna().any().any():
            raise ValueError("New-month orders must already be clean and unique")
        if orders["order_id"].duplicated().any():
            raise ValueError("New-month orders must already be clean and unique")
        dates = pd.to_datetime(orders["order_date"], errors="raise")
        order_months = dates.dt.to_period("M").astype(str)
        if orders.empty or not order_months.eq(month).all():
            raise ValueError("Supply only the specified new month's clean orders")
        region_master = pd.read_csv(OUTPUT_DIR / "regions_master.csv")
        if not set(orders["region"]).issubset(set(region_master["region"])):
            raise ValueError("Unknown new-month region")

        # Only the new month's rows are needed for incremental processing.
        connection = sqlite3.connect(":memory:")
        region_master.to_sql("regions_master", connection, index=False)
        orders.to_sql("orders_clean", connection, index=False)

    query = """
        SELECT r.region, ROUND(COALESCE(SUM(o.sales_inr), 0), 2)
        FROM regions_master r
        LEFT JOIN orders_clean o
            ON r.region = o.region
            AND substr(o.order_date, 1, 7) = ?
        GROUP BY r.region
        ORDER BY r.region
    """
    with closing(connection) as connection:
        rows = connection.execute(query, (month,)).fetchall()

    sales_by_region = {}
    for region, sales in rows:
        sales_by_region[region] = sales
    return {"month": month, "sales": sales_by_region}


def process_month(month, state_path=None, orders=None):
    if state_path is None:
        state_path = OUTPUT_DIR / "monthly_state.json"
    previous = load_previous_state_v1(state_path)
    if previous:
        expected_month = str(pd.Period(previous["month"], freq="M") + 1)
        if month != expected_month:
            raise ValueError(
                f"Expected next month {expected_month}; got {month}. "
                "Use a separate state file to replay history."
            )

    current = monthly_summary(month, orders)
    changes = {}
    if previous:
        for region, current_sales in current["sales"].items():
            previous_sales = previous["sales"].get(region, 0)
            changes[region] = compute_percentage_change_v1(current_sales, previous_sales)
    result = {
        "previous_month": previous.get("month"),
        "current": current,
        "changes": changes,
        "flags": flag_significant_regions_v1(changes),
    }
    save_state_v1(current, state_path)
    return result


def compute_metrics():
    months = []
    for month in ["2026-04", "2026-05", "2026-06"]:
        months.append(monthly_summary(month))

    transitions = []
    for index in range(1, len(months)):
        previous = months[index - 1]
        current = months[index]
        changes = {}
        for region, current_sales in current["sales"].items():
            previous_sales = previous["sales"][region]
            changes[region] = compute_percentage_change_v1(current_sales, previous_sales)
        transitions.append({
            "previous_month": previous["month"],
            "month": current["month"],
            "changes": changes,
            "flags": flag_significant_regions_v1(changes),
        })

    with closing(sqlite3.connect(OUTPUT_DIR / "pharmeasy.db")) as connection:
        totals = connection.execute("""
            SELECT ROUND(SUM(sales_inr), 2), ROUND(SUM(profit_inr), 2),
                   COUNT(DISTINCT order_id)
            FROM orders_clean
        """).fetchone()
        category_sales = pd.read_sql_query("""
            SELECT category, substr(order_date, 1, 7) AS month,
                   ROUND(SUM(sales_inr), 2) AS sales_inr
            FROM orders_clean
            WHERE region = 'Guntur'
            GROUP BY category, month
        """, connection)
        order_counts = connection.execute("""
            SELECT substr(order_date, 1, 7), COUNT(DISTINCT order_id)
            FROM orders_clean
            WHERE region = 'Guntur'
            GROUP BY substr(order_date, 1, 7)
        """).fetchall()

    category_table = category_sales.pivot(index="category", columns="month", values="sales_inr")
    category_table = category_table.fillna(0)
    category_table["increase"] = category_table["2026-05"] - category_table["2026-04"]
    category_table = category_table.sort_values("increase", ascending=False)
    contributions = []
    for category, values in category_table.iterrows():
        april_sales = float(values["2026-04"])
        may_sales = float(values["2026-05"])
        contributions.append({
            "category": category,
            "april": april_sales,
            "may": may_sales,
            "delta": round(may_sales - april_sales, 2),
        })
    guntur_orders = {}
    for month, count in order_counts:
        guntur_orders[month] = count

    return {
        "months": months,
        "transitions": transitions,
        "kpis": {"sales": totals[0], "profit": totals[1], "orders": totals[2]},
        "guntur_categories": contributions,
        "guntur_orders": guntur_orders,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--month", help="Process this month using the saved previous state")
    parser.add_argument("--orders-clean", help="Optional CSV containing only the new month")
    args = parser.parse_args()
    if args.orders_clean and not args.month:
        parser.error("--orders-clean requires --month")

    orders = None
    if args.orders_clean:
        orders = pd.read_csv(args.orders_clean)
    if args.month:
        result = process_month(args.month, orders=orders)
    else:
        result = compute_metrics()
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
