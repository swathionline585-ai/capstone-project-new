"""Print SQL checks for joins, order IDs, and monthly sales."""
import os
import sqlite3
from contextlib import closing
from pathlib import Path

import pandas as pd

ROOT = Path(os.environ.get("PHARMEASY_PROJECT_DIR", Path(__file__).resolve().parent))
OUTPUT_DIR = ROOT / "output"

QUERIES = {
    "LEFT JOIN rows": """
        SELECT COUNT(*) AS row_count
        FROM regions_master r
        LEFT JOIN orders_clean o ON r.region = o.region
    """,
    "INNER JOIN rows": """
        SELECT COUNT(*) AS row_count
        FROM regions_master r
        INNER JOIN orders_clean o ON r.region = o.region
    """,
    "Duplicate keys": """
        SELECT order_id, COUNT(*) AS occurrences
        FROM orders_clean
        GROUP BY order_id
        HAVING COUNT(*) > 1
    """,
    "COUNT star versus matched IDs": """
        SELECT r.region, COUNT(*) AS count_star, COUNT(o.order_id) AS order_count
        FROM regions_master r
        LEFT JOIN orders_clean o ON r.region = o.region
        GROUP BY r.region
        ORDER BY r.region
    """,
    "Count disagreement": """
        SELECT r.region, COUNT(*) AS count_star, COUNT(o.order_id) AS order_count
        FROM regions_master r
        LEFT JOIN orders_clean o ON r.region = o.region
        GROUP BY r.region
        HAVING COUNT(*) <> COUNT(o.order_id)
    """,
    "Region order counts ascending": """
        SELECT r.region, COUNT(o.order_id) AS order_count
        FROM regions_master r
        LEFT JOIN orders_clean o ON r.region = o.region
        GROUP BY r.region
        ORDER BY order_count, r.region
    """,
    "Region month sales": """
        SELECT region, substr(order_date, 1, 7) AS month,
               ROUND(SUM(sales_inr), 2) AS sales_inr
        FROM orders_clean
        GROUP BY region, month
        ORDER BY region, month
    """,
}


def query_checks():
    results = {}
    with closing(sqlite3.connect(OUTPUT_DIR / "pharmeasy.db")) as connection:
        for name, query in QUERIES.items():
            results[name] = pd.read_sql_query(query, connection)

    if results["LEFT JOIN rows"].iloc[0, 0] != 2101:
        raise ValueError("LEFT JOIN should return 2101 rows")
    if results["INNER JOIN rows"].iloc[0, 0] != 2100:
        raise ValueError("INNER JOIN should return 2100 rows")
    if not results["Duplicate keys"].empty:
        raise ValueError("Duplicate order IDs found")
    expected_disagreement = [{"region": "Kurnool", "count_star": 1, "order_count": 0}]
    if results["Count disagreement"].to_dict("records") != expected_disagreement:
        raise ValueError("Unexpected COUNT(*) versus COUNT(order_id) results")

    for name, table in results.items():
        print(name)
        if table.empty:
            print("Zero rows")
        else:
            print(table.to_string(index=False))
    return results


if __name__ == "__main__":
    query_checks()
