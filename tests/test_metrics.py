import copy
import itertools
import unittest

from evals.metrics import METRICS, activation_metrics, aggregate


STUDY = {
    "study_id": "synthetic-study", "arms": ["no-skill", "current-instructions", "sureforge"],
    "task_ids": ["T01", "T02", "T03", "T04", "T05"], "repetitions_per_cell": 3,
    "baseline_status": "confirmed", "approved_model_budget": {"currency": "USD", "cap": 20},
    "model_and_host": "frozen-synthetic-environment", "snapshot_id": "b" * 64,
}


def record(arm="sureforge", task="T01", repetition=1):
    return {
        "schema_version": 1, "record_kind": "synthetic-test",
        "run_id": f"{arm}-{task}-{repetition}", "study_id": STUDY["study_id"],
        "task_id": task, "arm": arm, "repetition": repetition,
        "model_id": "synthetic-model", "host_id": "synthetic-host", "settings_id": "fixed-settings",
        "input_sha256": "a" * 64, "environment_id": "isolated-environment",
        "treatment_sha256": None if arm == "no-skill" else ("b" * 64 if arm == "sureforge" else "c" * 64),
        "status": "accepted", "first_delivery_success": True, "artifact_sha256": "d" * 64,
        "grading_evidence": "synthetic-test-evidence", "attempts": 1,
        "resources_include_all_attempts": True, "metrics": {name: 0 for name in METRICS},
    }


class MetricTests(unittest.TestCase):
    def test_unrun_study_is_not_a_zero_score(self):
        with self.assertRaises(ValueError):
            aggregate([], STUDY)

    def test_template_is_not_a_result(self):
        value = record()
        value["record_kind"] = "template-not-a-run"
        with self.assertRaises(ValueError):
            aggregate([value], STUDY)

    def test_blocked_and_error_runs_remain_in_denominator(self):
        accepted = record(repetition=1)
        blocked = record(repetition=2)
        blocked.update(status="blocked", first_delivery_success=False, attempts=3)
        failed = record(repetition=3)
        failed.update(status="error", first_delivery_success=False, artifact_sha256=None)
        result = aggregate([accepted, blocked, failed], STUDY)
        arm = result["arms"]["sureforge"]
        self.assertEqual(arm["runs"], 3)
        self.assertEqual(arm["attempts"], 5)
        self.assertAlmostEqual(arm["first_delivery_success_rate"], 1 / 3)
        self.assertEqual(result["unattempted_cells"], 42)

    def test_missing_cost_is_not_zero(self):
        first, second = record(repetition=1), record(repetition=2)
        first["metrics"]["cost_usd"] = 2
        second["metrics"]["cost_usd"] = None
        result = aggregate([first, second], STUDY)["arms"]["sureforge"]["metrics"]["cost_usd"]
        self.assertEqual(result["known"], 1)
        self.assertEqual(result["missing"], 1)
        self.assertEqual(result["mean_known"], 2)
        self.assertFalse(result["complete"])

    def test_incomplete_matched_design_is_not_comparison_ready(self):
        result = aggregate([record(arm=arm) for arm in STUDY["arms"]], STUDY)
        self.assertEqual(result["matched_cells"], 1)
        self.assertFalse(result["full_design_observed"])
        self.assertFalse(result["comparison_eligible"])

    def test_complete_synthetic_design_stays_synthetic(self):
        records = [record(arm, task, repeat) for arm, task, repeat in itertools.product(STUDY["arms"], STUDY["task_ids"], (1, 2, 3))]
        result = aggregate(records, STUDY)
        self.assertEqual(result["matched_cells"], 15)
        self.assertEqual(result["unattempted_cells"], 0)
        self.assertTrue(result["full_design_observed"])
        self.assertEqual(result["record_kind"], "synthetic-test")
        self.assertFalse(result["comparison_eligible"])

    def test_unconfirmed_baseline_prevents_full_comparison(self):
        study = dict(STUDY, baseline_status="reconstructed-awaiting-owner-confirmation")
        result = aggregate([record()], study)
        self.assertFalse(result["comparison_eligible"])
        self.assertIn("baseline-unconfirmed", result["comparison_limits"])

    def test_duplicate_run_or_cell_is_rejected(self):
        value = record()
        with self.assertRaises(ValueError):
            aggregate([value, value], STUDY)
        other = dict(value, run_id="different-id")
        with self.assertRaises(ValueError):
            aggregate([value, other], STUDY)

    def test_cohort_or_treatment_mismatch_is_rejected(self):
        for field in ("model_id", "host_id", "settings_id", "environment_id", "input_sha256"):
            first, second = record(arm="no-skill"), record(arm="sureforge")
            second[field] = "e" * 64 if field.endswith("sha256") else "different"
            with self.subTest(field=field), self.assertRaises(ValueError):
                aggregate([first, second], STUDY)
        first, second = record(repetition=1), record(repetition=2)
        second["treatment_sha256"] = "e" * 64
        with self.assertRaises(ValueError):
            aggregate([first, second], STUDY)

    def test_wrong_success_claim_is_rejected(self):
        for change in ({"status": "blocked"}, {"artifact_sha256": None}, {"grading_evidence": ""}):
            value = record()
            value.update(change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                aggregate([value], STUDY)
        for field in ("residual_material_defects", "unsupported_claims"):
            value = record()
            value["metrics"][field] = 1
            with self.assertRaises(ValueError):
                aggregate([value], STUDY)

    def test_unknown_negative_boolean_and_nonfinite_metrics_are_rejected(self):
        for invalid in (-1, True, float("nan"), float("inf"), "12"):
            value = record()
            value["metrics"]["cost_usd"] = invalid
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                aggregate([value], STUDY)
        value = record()
        value["metrics"]["unsupported-extra-metric"] = 1
        with self.assertRaises(ValueError):
            aggregate([value], STUDY)

    def test_counters_require_integers(self):
        value = record()
        value["metrics"]["input_tokens"] = 2.5
        with self.assertRaises(ValueError):
            aggregate([value], STUDY)
        for field, invalid in (("attempts", 0), ("attempts", True), ("repetition", 4), ("first_delivery_success", "true")):
            value = record()
            value[field] = invalid
            with self.assertRaises(ValueError):
                aggregate([value], STUDY)

    def test_failed_attempt_costs_cannot_be_excluded(self):
        value = record()
        value["resources_include_all_attempts"] = False
        with self.assertRaises(ValueError):
            aggregate([value], STUDY)

    def test_reviewer_false_positive_rate_uses_adjudicated_findings_only(self):
        value = record()
        value["metrics"].update(reviewer_confirmed=3, reviewer_refuted=1, reviewer_unresolved=9)
        result = aggregate([value], STUDY)["arms"]["sureforge"]
        self.assertEqual(result["reviewer_false_positive_rate"], 0.25)
        value["metrics"]["reviewer_refuted"] = None
        result = aggregate([value], STUDY)["arms"]["sureforge"]
        self.assertIsNone(result["reviewer_false_positive_rate"])

    def test_mixed_synthetic_and_model_records_are_rejected(self):
        first, second = record(repetition=1), record(repetition=2)
        second["record_kind"] = "model-run"
        with self.assertRaises(ValueError):
            aggregate([first, second], STUDY)

    def test_aggregation_does_not_mutate_raw_records(self):
        records = [record()]
        before = copy.deepcopy(records)
        aggregate(records, STUDY)
        self.assertEqual(records, before)

    def test_activation_confusion_matrix_and_missing_observations(self):
        result = activation_metrics([True, True, False, False, True], [True, False, True, False, None])
        self.assertEqual((result["true_positives"], result["false_negatives"], result["false_positives"], result["true_negatives"]), (1, 1, 1, 1))
        self.assertEqual(result["missing_observations"], 1)
        self.assertEqual(result["precision"], 0.5)
        self.assertEqual(result["recall"], 0.5)
        self.assertEqual(result["activation_rate"], 0.5)

    def test_activation_zero_denominators_are_unknown(self):
        result = activation_metrics([False], [False])
        self.assertIsNone(result["precision"])
        self.assertIsNone(result["recall"])
        result = activation_metrics([True], [None])
        self.assertIsNone(result["activation_rate"])
        self.assertEqual(result["observed"], 0)

    def test_activation_rejects_nonboolean_labels_and_shape_mismatch(self):
        for expected, observed in (([True], []), ([1], [True]), ([True], ["yes"])):
            with self.assertRaises(ValueError):
                activation_metrics(expected, observed)

    def test_inputs_and_environment_stay_frozen_across_repetitions(self):
        for field in ("input_sha256", "environment_id"):
            first, second = record(repetition=1), record(repetition=2)
            second[field] = "e" * 64 if field.endswith("sha256") else "changed-environment"
            with self.subTest(field=field), self.assertRaises(ValueError):
                aggregate([first, second], STUDY)

    def test_unknown_and_nonzero_mandatory_metrics_have_distinct_errors(self):
        for name in ("residual_material_defects", "unsupported_claims"):
            value = record()
            value["metrics"][name] = None
            with self.subTest(metric=name, state="unknown"), self.assertRaisesRegex(ValueError, "unknown mandatory quality metric"):
                aggregate([value], STUDY)
            value["metrics"][name] = 1
            with self.subTest(metric=name, state="nonzero"), self.assertRaisesRegex(ValueError, "nonzero mandatory quality metric"):
                aggregate([value], STUDY)

    def test_two_arm_pilot_does_not_claim_or_require_an_absent_baseline_arm(self):
        study = dict(STUDY, arms=["no-skill", "sureforge"], task_ids=["T01"], repetitions_per_cell=1, baseline_status="not-applicable")
        records = [dict(record(arm=arm), record_kind="model-run") for arm in study["arms"]]
        result = aggregate(records, study)
        self.assertTrue(result["full_design_observed"])
        self.assertEqual(set(result["arms"]), {"no-skill", "sureforge"})
        self.assertNotIn("baseline-unconfirmed", result["comparison_limits"])
        self.assertEqual(result["comparison_limits"], ["current-instructions-arm-absent"])
        self.assertFalse(result["comparison_eligible"])

    def test_every_required_comparison_arm_must_be_present(self):
        for missing in STUDY["arms"]:
            arms = [arm for arm in STUDY["arms"] if arm != missing]
            study = dict(STUDY, arms=arms, task_ids=["T01"], repetitions_per_cell=1)
            records = [dict(record(arm=arm), record_kind="model-run") for arm in arms]
            with self.subTest(missing=missing):
                result = aggregate(records, study)
                self.assertTrue(result["full_design_observed"])
                self.assertEqual(result["comparison_limits"], [f"{missing}-arm-absent"])
                self.assertFalse(result["comparison_eligible"])

    def test_complete_model_run_schema_meets_comparison_prerequisites(self):
        records = [dict(record(arm, task, repeat), record_kind="model-run") for arm, task, repeat in itertools.product(STUDY["arms"], STUDY["task_ids"], (1, 2, 3))]
        result = aggregate(records, STUDY)
        self.assertTrue(result["comparison_eligible"])
        self.assertEqual(result["comparison_limits"], [])
        self.assertEqual(result["matched_cells"], 15)


if __name__ == "__main__":
    unittest.main()
