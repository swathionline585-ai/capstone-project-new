"""Clean the supplied orders before calculating any metrics."""
import json
import os
from pathlib import Path

import pandas as pd

# Tests use a temporary folder; normal runs use this script's folder.
ROOT = Path(os.environ.get("PHARMEASY_PROJECT_DIR", Path(__file__).resolve().parent))
OUTPUT_DIR = ROOT / "output"
REQUIRED_COLUMNS = [
    "order_id", "order_date", "region", "category",
    "product", "quantity", "sales_inr", "profit_inr",
]


def validate_schema(df, required_columns):
    missing_columns = []
    for column in required_columns:
        if column not in df.columns:
            missing_columns.append(column)

    status = "validated"
    if missing_columns:
        status = "blocked_schema"

    return {
        "status": status,
        "row_count": len(df),
        "missing_columns": missing_columns,
    }


def clean_orders(raw, master):
    schema_result = validate_schema(raw, REQUIRED_COLUMNS)
    if schema_result["status"] != "validated":
        raise ValueError(schema_result)

    stats = {
        "raw_rows": len(raw),
        "raw_region_variants": raw["region"].nunique(),
        "duplicates_removed": int(raw.duplicated(subset=REQUIRED_COLUMNS).sum()),
    }

    # Remove copies before they affect totals or the average profit margin.
    orders = raw.drop_duplicates(subset=REQUIRED_COLUMNS).copy()
    orders["region"] = orders["region"].str.strip().str.title()
    known_regions = set(master["region"])
    if orders["region"].isna().any():
        raise ValueError("Unknown or missing region")
    if not set(orders["region"]).issubset(known_regions):
        raise ValueError("Unknown or missing region")

    known_categories = orders.dropna(subset=["category"])
    categories_per_product = known_categories.groupby("product")["category"].nunique()
    if (categories_per_product > 1).any():
        raise ValueError("Ambiguous product-to-category mapping")

    category_lookup = known_categories.drop_duplicates("product")
    category_lookup = category_lookup.set_index("product")["category"]
    stats["categories_imputed"] = int(orders["category"].isna().sum())
    recovered_categories = orders["product"].map(category_lookup)
    orders["category"] = orders["category"].fillna(recovered_categories)
    if orders["category"].isna().any():
        raise ValueError("Category lookup incomplete")

    for column in ["quantity", "sales_inr", "profit_inr"]:
        orders[column] = pd.to_numeric(orders[column], errors="raise")
    if (orders["sales_inr"] <= 0).any() or (orders["quantity"] <= 0).any():
        raise ValueError("Sales and quantity must be positive")

    # Category must be filled first because it determines the margin estimate.
    observed_orders = orders.dropna(subset=["profit_inr"])
    observed_margins = observed_orders["profit_inr"] / observed_orders["sales_inr"]
    category_margins = observed_margins.groupby(observed_orders["category"]).mean()

    missing_profit = orders["profit_inr"].isna()
    stats["profits_imputed"] = int(missing_profit.sum())
    sales_to_estimate = orders.loc[missing_profit, "sales_inr"]
    margins_to_use = orders.loc[missing_profit, "category"].map(category_margins)
    orders.loc[missing_profit, "profit_inr"] = (sales_to_estimate * margins_to_use).round(2)

    if orders[REQUIRED_COLUMNS].isna().any().any():
        raise ValueError("Required values still missing")
    if orders["order_id"].duplicated().any():
        raise ValueError("Conflicting duplicate order IDs remain")
    pd.to_datetime(orders["order_date"], format="%Y-%m-%d", errors="raise")

    stats["clean_rows"] = len(orders)
    stats["canonical_regions"] = orders["region"].nunique()
    stats["schema"] = validate_schema(orders, REQUIRED_COLUMNS)
    broken_orders = orders.drop(columns="profit_inr")
    stats["broken_schema"] = validate_schema(broken_orders, REQUIRED_COLUMNS)
    return orders.reset_index(drop=True), stats


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    raw_orders = pd.read_csv(OUTPUT_DIR / "pharmeasy_orders_raw.csv")
    region_master = pd.read_csv(OUTPUT_DIR / "regions_master.csv")
    clean_orders_df, stats = clean_orders(raw_orders, region_master)
    clean_orders_df.to_csv(OUTPUT_DIR / "orders_clean.csv", index=False)
    checks_json = json.dumps(stats, indent=2)
    (OUTPUT_DIR / "cleaning_checks.json").write_text(checks_json, encoding="utf-8")
    print(checks_json)
    return clean_orders_df


if __name__ == "__main__":
    main()
