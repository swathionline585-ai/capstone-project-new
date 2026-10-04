"""One command prepares every stage and offers explicit human review."""
import argparse
import json
import subprocess
import sys
import os
from pathlib import Path

# The environment override is used only by isolated tests.
ROOT = Path(os.environ.get("PHARMEASY_PROJECT_DIR", Path(__file__).resolve().parent))
OUTPUT_DIR = ROOT / "output"
from clean_data import main as clean
from build_db import build_database
from queries import query_checks
from metrics_engine import compute_metrics, process_month
from draft_report import build_package
from review_gate import record_package_decision, checklist, test_harness

APR_FLAGS = {"Hyderabad", "Warangal", "Visakhapatnam", "Guntur", "Tirupati", "Karimnagar", "Bengaluru"}
MAY_FLAGS = {"Hyderabad", "Warangal", "Vijayawada", "Visakhapatnam", "Guntur", "Tirupati", "Karimnagar"}

def check_result(actual, expected, description):
    if actual != expected:
        raise ValueError(f"{description}: expected {expected}, got {actual}")


def prepare():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    generator = Path(__file__).resolve().parent / "generate_dataset.py"
    subprocess.run([sys.executable, str(generator)], cwd=OUTPUT_DIR, check=True)
    clean()

    checks = json.loads((OUTPUT_DIR / "cleaning_checks.json").read_text(encoding="utf-8"))
    expected_counts = {
        "raw_rows": 2159,
        "duplicates_removed": 59,
        "raw_region_variants": 16,
        "categories_imputed": 48,
        "profits_imputed": 94,
        "clean_rows": 2100,
        "canonical_regions": 9,
    }
    for name, expected_count in expected_counts.items():
        check_result(checks[name], expected_count, name)

    build_database()
    query_checks()
    metrics = compute_metrics()
    expected_guntur_sales = [62442.27, 138738.93, 99745.18]
    for index in range(len(metrics["months"])):
        summary = metrics["months"][index]
        check_result(summary["sales"]["Guntur"], expected_guntur_sales[index], "Guntur sales")
    expected_totals = {"sales": 3265191.42, "profit": 492279.59, "orders": 2100}
    check_result(metrics["kpis"], expected_totals, "Overall totals")
    top_category = metrics["guntur_categories"][0]
    check_result(top_category["category"], "Wellness & Nutrition", "Top category")
    check_result(top_category["delta"], 33787.42, "Category sales increase")

    expected_flag_sets = [APR_FLAGS, MAY_FLAGS]
    for index in range(len(metrics["transitions"])):
        transition = metrics["transitions"][index]
        flagged_regions = set()
        for region, is_flagged in transition["flags"].items():
            if is_flagged:
                flagged_regions.add(region)
        check_result(flagged_regions, expected_flag_sets[index], "Flagged regions")

    # Replay the supplied months separately from normal incremental processing.
    replay_file = OUTPUT_DIR / "pipeline_replay_state.json"
    if replay_file.exists():
        replay_file.unlink()
    for month in ["2026-04", "2026-05", "2026-06"]:
        process_month(month, replay_file)
    (OUTPUT_DIR / "monthly_state.json").write_bytes(replay_file.read_bytes())
    replay_file.unlink()

    package = build_package()
    check_result(len(package["reports"]), 8, "Unique regional reports")
    review_file = OUTPUT_DIR / "reviewed_report.json"
    if review_file.exists():
        previous_review = json.loads(review_file.read_text(encoding="utf-8"))
        if previous_review.get("content_fingerprint") != package["content_fingerprint"]:
            review_file.unlink()
    if not review_file.exists():
        (ROOT / "reliability_checklist.md").write_text(checklist(), encoding="utf-8")
    if not (OUTPUT_DIR / "audit_log.jsonl").exists():
        test_harness()
    return package


def main():
    # Older Windows terminals may otherwise fail to print the rupee symbol.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare-only", action="store_true", help="Prepare files without approval")
    args = parser.parse_args()
    package = prepare()

    print("Verified metrics:", json.dumps(package["metrics"], indent=2))
    for report in package["reports"]:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    print(package["executive_summary"])
    print(package["memo"])
    print(package["storyline"])
    if args.prepare_only:
        print("Prepared without approval. Run python pipeline.py to review the report in your terminal.")
        return

    while True:
        decision = input("Review this complete package: approve / edit / reject: ").strip().lower()
        if decision in {"approve", "edit", "reject"}:
            break
        print("Enter one of the three listed decisions.")
    note = input("Your name and what you checked (required): ").strip()
    updated_report = record_package_decision(package, decision, note)
    print("Downstream use allowed:", updated_report["external_use_allowed"])
    print("If edits are needed, update the wording in draft_report.py, then rerun python pipeline.py to review the revised report.")


if __name__ == "__main__":
    main()
