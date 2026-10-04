"""Load the exact cleaned CSV and region master into SQLite."""
import os
import sqlite3
from contextlib import closing
from pathlib import Path

import pandas as pd

from clean_data import REQUIRED_COLUMNS, validate_schema

ROOT = Path(os.environ.get("PHARMEASY_PROJECT_DIR", Path(__file__).resolve().parent))
OUTPUT_DIR = ROOT / "output"


def build_database():
    orders = pd.read_csv(OUTPUT_DIR / "orders_clean.csv")
    region_master = pd.read_csv(OUTPUT_DIR / "regions_master.csv")
    schema_result = validate_schema(orders, REQUIRED_COLUMNS)
    if schema_result["status"] != "validated":
        raise ValueError("Blocked schema")
    if len(orders) != 2100 or len(region_master) != 10:
        raise ValueError("Unexpected capstone dataset counts")

    # closing() releases the database file even if a query fails.
    with closing(sqlite3.connect(OUTPUT_DIR / "pharmeasy.db")) as connection:
        region_master.to_sql("regions_master", connection, if_exists="replace", index=False)
        orders.to_sql("orders_clean", connection, if_exists="replace", index=False)
        connection.execute("CREATE UNIQUE INDEX order_id_unique ON orders_clean(order_id)")
        connection.execute("CREATE UNIQUE INDEX region_unique ON regions_master(region)")
        connection.commit()
    print("Built pharmeasy.db: 10 regions; 2100 orders")


if __name__ == "__main__":
    build_database()
