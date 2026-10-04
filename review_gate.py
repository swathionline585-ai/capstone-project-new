"""A human decision, an append-only audit record, and a persisted report."""
import json
import uuid
from datetime import datetime, timezone
import os
from pathlib import Path

# The environment override is used only by isolated tests.
ROOT = Path(os.environ.get("PHARMEASY_PROJECT_DIR", Path(__file__).resolve().parent))
OUTPUT_DIR = ROOT / "output"

VALID_DECISIONS = {"approve", "edit", "reject"}

def review_gate_v1(report, decision, reviewer_note=""):
    if decision not in VALID_DECISIONS:
        raise ValueError("Decision must be approve, edit, or reject")
    if not isinstance(report, dict):
        raise TypeError("Report must be a dictionary")
    if not isinstance(reviewer_note, str):
        raise TypeError("Reviewer note must be text")

    timestamp = datetime.now(timezone.utc).isoformat()
    run_id = str(uuid.uuid4())
    use_allowed = decision == "approve"
    audit_record = {
        "timestamp": timestamp,
        "run_id": run_id,
        "region": report.get("region", "unknown"),
        "decision": decision,
        "reviewer_note": reviewer_note,
        "content_fingerprint": report.get("content_fingerprint"),
        "test_only": report.get("test_only", False),
    }
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    # Append one event without replacing earlier review decisions.
    with (OUTPUT_DIR / "audit_log.jsonl").open("a", encoding="utf-8") as log_file:
        log_file.write(json.dumps(audit_record, ensure_ascii=False) + "\n")

    updated_report = report.copy()
    updated_report["review_decision"] = decision
    updated_report["reviewer_note"] = reviewer_note
    updated_report["external_use_allowed"] = use_allowed
    updated_report["run_id"] = run_id
    updated_report["reviewed_at"] = timestamp
    return updated_report


def record_package_decision(package, decision, note):
    if not note.strip():
        raise ValueError("Record your name and what you reviewed in the note")
    updated_report = review_gate_v1(package, decision, note)
    reviewed_json = json.dumps(updated_report, indent=2, ensure_ascii=False)
    (OUTPUT_DIR / "reviewed_report.json").write_text(reviewed_json, encoding="utf-8")

    use_status = "blocked"
    if updated_report["external_use_allowed"]:
        use_status = "allowed"
    signoff = (
        f"Human sign-off: {decision} at {updated_report['reviewed_at']}; {note}. "
        f"Downstream use {use_status}."
    )
    (ROOT / "reliability_checklist.md").write_text(checklist(signoff), encoding="utf-8")
    return updated_report


def checklist(signoff="Human sign-off: pending; no package approval has been recorded and downstream use is blocked."):
    lines = [
        "# Reliability checklist",
        "",
        "1. Safety check: Reviewed the supplied schema and narrative templates; there are no customer identifiers, and public narratives use regional aggregates.",
        "2. Validation: Cleaning, SQL JOIN counts, exact flag sets, schema failure, and Guntur totals are asserted by the pipeline before review; profit is explicitly identified as partly estimated.",
        "3. Critique and refine: Narrative templates label causal explanations as unverified, describe the alert as operational rather than statistical, and include observed category contributions.",
        "4. " + signoff,
        "",
    ]
    return "\n".join(lines)


def test_harness():
    report = {
        "region": "Guntur",
        "test_only": True,
        "context": "Synthetic function-path test; not a human-approved deliverable.",
    }
    for decision in sorted(VALID_DECISIONS):
        print("Before:", json.dumps(report))
        note = "Automated harness: decision behavior only, not actual sign-off"
        updated_report = review_gate_v1(report, decision, note)
        print("After:", json.dumps(updated_report))
        assert updated_report["external_use_allowed"] == (decision == "approve")

    try:
        review_gate_v1(report, "invalid")
    except ValueError:
        print("Invalid decision correctly blocked")
    else:
        raise AssertionError("Invalid decision accepted")


if __name__ == "__main__":
    test_harness()
