import argparse
import itertools
import json
import math
import re
from pathlib import Path

from scripts.check_package import ROOT, load_json


METRICS = (
    "residual_material_defects", "residual_minor_defects", "reviewer_confirmed",
    "reviewer_refuted", "reviewer_unresolved", "reviewer_duplicate", "reviewer_out_of_scope",
    "harmful_repairs", "unsupported_claims", "user_interventions", "loops_without_progress",
    "unverifiable_checks", "elapsed_seconds", "input_tokens", "output_tokens", "cost_usd",
)
FLOAT_METRICS = frozenset({"elapsed_seconds", "cost_usd"})
REQUIRED_COMPARISON_ARMS = ("no-skill", "current-instructions", "sureforge")
COHORT_FIELDS = ("model_id", "host_id", "settings_id", "input_sha256", "environment_id")
RECORD_FIELDS = frozenset({
    "schema_version", "record_kind", "run_id", "study_id", "task_id", "arm", "repetition",
    "model_id", "host_id", "settings_id", "input_sha256", "environment_id", "treatment_sha256",
    "status", "first_delivery_success", "artifact_sha256", "grading_evidence", "attempts",
    "resources_include_all_attempts", "metrics",
})


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _hash(value):
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _ratio(numerator, denominator):
    return numerator / denominator if denominator else None


def _validate(record, study):
    if not isinstance(record, dict) or set(record) != RECORD_FIELDS or type(record["schema_version"]) is not int or record["schema_version"] != 1:
        raise ValueError("invalid run-record schema")
    if record["record_kind"] not in {"model-run", "synthetic-test"}:
        raise ValueError("templates and expectations are not observed runs")
    if record["study_id"] != study["study_id"] or record["task_id"] not in study["task_ids"] or record["arm"] not in study["arms"]:
        raise ValueError("run is outside the frozen study")
    if any(not _text(record[field]) for field in ("run_id", "model_id", "host_id", "settings_id", "environment_id", "grading_evidence")):
        raise ValueError("missing run identity, environment, or grading evidence")
    if type(record["repetition"]) is not int or not 1 <= record["repetition"] <= study["repetitions_per_cell"]:
        raise ValueError("invalid repetition")
    if type(record["attempts"]) is not int or record["attempts"] < 1 or record["resources_include_all_attempts"] is not True:
        raise ValueError("include all attempts and their measured resources")
    if not _hash(record["input_sha256"]):
        raise ValueError("missing frozen input hash")
    if record["arm"] == "no-skill":
        if record["treatment_sha256"] is not None:
            raise ValueError("no-skill baseline must not have a treatment")
    elif not _hash(record["treatment_sha256"]):
        raise ValueError("missing frozen treatment hash")
    if record["status"] not in {"accepted", "failed", "blocked", "error"} or type(record["first_delivery_success"]) is not bool:
        raise ValueError("invalid outcome")
    if record["first_delivery_success"] and record["status"] != "accepted":
        raise ValueError("non-accepted runs cannot count as first-delivery success")
    if record["artifact_sha256"] is not None and not _hash(record["artifact_sha256"]):
        raise ValueError("invalid artifact hash")
    if record["status"] == "accepted" and not _hash(record["artifact_sha256"]):
        raise ValueError("accepted runs require an artifact identity")
    metrics = record["metrics"]
    if not isinstance(metrics, dict) or set(metrics) != set(METRICS):
        raise ValueError("metric inventory mismatch")
    for name, value in metrics.items():
        if value is None:
            continue
        types = (int, float) if name in FLOAT_METRICS else (int,)
        if type(value) not in types or not math.isfinite(value) or value < 0:
            raise ValueError(f"invalid metric: {name}")
    if record["status"] == "accepted":
        for name in ("residual_material_defects", "unsupported_claims"):
            if metrics[name] is None:
                raise ValueError(f"accepted outcome has an unknown mandatory quality metric: {name}")
            if metrics[name] != 0:
                raise ValueError(f"accepted outcome has a nonzero mandatory quality metric: {name}")


def _metric_summary(records, name):
    values = [record["metrics"][name] for record in records if record["metrics"][name] is not None]
    return {
        "known": len(values), "missing": len(records) - len(values),
        "sum_known": sum(values) if values else None,
        "mean_known": sum(values) / len(values) if values else None,
        "complete": bool(records) and len(values) == len(records),
    }


def aggregate(records, study):
    if not isinstance(records, list) or not records:
        raise ValueError("no observed runs; an unrun study has no performance score")
    for record in records:
        _validate(record, study)
    if len({record["record_kind"] for record in records}) != 1:
        raise ValueError("do not mix synthetic records and model runs")
    if len({record["run_id"] for record in records}) != len(records):
        raise ValueError("duplicate run ID")
    cells = {(record["task_id"], record["arm"], record["repetition"]): record for record in records}
    if len(cells) != len(records):
        raise ValueError("duplicate study cell; combine its internal attempts")
    for field in ("model_id", "host_id", "settings_id"):
        if len({record[field] for record in records}) != 1:
            raise ValueError(f"mixed study cohort: {field}")
    for arm in study["arms"]:
        if len({record["treatment_sha256"] for record in records if record["arm"] == arm}) > 1:
            raise ValueError("treatment changed during the study")
    for task in study["task_ids"]:
        group = [record for record in records if record["task_id"] == task]
        if any(len({record[field] for record in group}) > 1 for field in ("input_sha256", "environment_id")):
            raise ValueError("task inputs or environment changed across repetitions")
    matched = 0
    for task, repetition in itertools.product(study["task_ids"], range(1, study["repetitions_per_cell"] + 1)):
        group = [cells[(task, arm, repetition)] for arm in study["arms"] if (task, arm, repetition) in cells]
        if any(len({record[field] for record in group}) > 1 for field in COHORT_FIELDS):
            raise ValueError("matched cells have different inputs or environments")
        matched += len(group) == len(study["arms"])
    summaries = {}
    for arm in study["arms"]:
        group = [record for record in records if record["arm"] == arm]
        metrics = {name: _metric_summary(group, name) for name in METRICS}
        adjudicated = metrics["reviewer_confirmed"], metrics["reviewer_refuted"]
        false_positive_rate = None
        if all(metric["complete"] for metric in adjudicated):
            false_positive_rate = _ratio(adjudicated[1]["sum_known"], sum(metric["sum_known"] for metric in adjudicated))
        summaries[arm] = {
            "runs": len(group), "attempts": sum(record["attempts"] for record in group),
            "first_delivery_successes": sum(record["first_delivery_success"] for record in group),
            "first_delivery_success_rate": _ratio(sum(record["first_delivery_success"] for record in group), len(group)),
            "outcomes": {status: sum(record["status"] == status for record in group) for status in ("accepted", "failed", "blocked", "error")},
            "reviewer_false_positive_rate": false_positive_rate, "metrics": metrics,
        }
    expected = len(study["task_ids"]) * len(study["arms"]) * study["repetitions_per_cell"]
    limitations = [f"{arm}-arm-absent" for arm in REQUIRED_COMPARISON_ARMS if arm not in study["arms"]]
    if records[0]["record_kind"] != "model-run":
        limitations.append("synthetic-data-not-model-evidence")
    if len(records) != expected:
        limitations.append("incomplete-matched-design")
    if "current-instructions" in study["arms"] and study.get("baseline_status") != "confirmed":
        limitations.append("baseline-unconfirmed")
    if study.get("approved_model_budget") is None:
        limitations.append("model-budget-unapproved")
    if study.get("model_and_host") is None:
        limitations.append("model-host-not-frozen")
    snapshot = study.get("snapshot_id")
    if not _hash(snapshot):
        limitations.append("skill-snapshot-not-frozen")
    elif any(record["arm"] == "sureforge" and record["treatment_sha256"] != snapshot for record in records):
        limitations.append("skill-snapshot-mismatch")
    return {
        "study_id": study["study_id"],
        "record_kind": records[0]["record_kind"], "attempted_runs": len(records),
        "expected_runs": expected, "unattempted_cells": expected - len(records),
        "matched_cells": matched, "full_design_observed": len(records) == expected,
        "comparison_eligible": not limitations, "comparison_limits": limitations,
        "arms": summaries,
        "limits": "Descriptive aggregation of supplied records, not proof of authentic observations, independent grading, statistical superiority, or publication authority. Missing resources remain unknown.",
    }


def activation_metrics(expected, observed):
    if len(expected) != len(observed) or any(type(value) is not bool for value in expected) or any(value is not None and type(value) is not bool for value in observed):
        raise ValueError("activation labels must be paired booleans; missing observations are null")
    pairs = [(want, got) for want, got in zip(expected, observed) if got is not None]
    tp = sum(want and got for want, got in pairs)
    fp = sum(not want and got for want, got in pairs)
    tn = sum(not want and not got for want, got in pairs)
    fn = sum(want and not got for want, got in pairs)
    return {
        "expected_observations": len(expected), "observed": len(pairs),
        "missing_observations": len(expected) - len(pairs),
        "true_positives": tp, "false_positives": fp, "true_negatives": tn, "false_negatives": fn,
        "precision": _ratio(tp, tp + fp), "recall": _ratio(tp, tp + fn),
        "false_positive_rate": _ratio(fp, fp + tn), "false_negative_rate": _ratio(fn, tp + fn),
        "activation_rate": _ratio(tp + fp, len(pairs)),
        "limits": "Counts supplied observations; does not run or observe host activation.",
    }


def main():
    parser = argparse.ArgumentParser(description="Aggregate actual or explicitly synthetic evaluation records without running a model.")
    parser.add_argument("--records", type=Path, required=True)
    parser.add_argument("--study", type=Path, default=ROOT / "evals/study.json")
    args = parser.parse_args()
    try:
        report = aggregate(load_json(args.records.read_text(encoding="utf-8")), load_json(args.study.read_text(encoding="utf-8")))
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(1, f"Evaluation records rejected: {error}\n")
    print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
