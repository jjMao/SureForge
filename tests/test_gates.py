import itertools
import unittest
from dataclasses import replace

from evals.gate_model import Evidence, Finding, Gate, Method, Review, Snapshot, decide


SNAPSHOT = Snapshot("artifact-2", "contract-1", "environment-1")
UNITS = frozenset({"page-1/visual", "page-2/visual"})


def checks(role, count=3):
    return tuple(
        Method(f"{role}-{i}", f"family-{i}", f"failure-{i}", f"procedure-{i}", "contract", "observation", True)
        for i in range(count)
    )


def coverage(role, snapshot=SNAPSHOT):
    return tuple(Evidence(f"{role}-{unit}", unit, role, snapshot, "fresh", True, "observed", "retained-output") for unit in sorted(UNITS))


def valid_gate(**changes):
    reviewer = Review(True, True, False, True, True, checks("reviewer"), coverage("reviewer"))
    gate = Gate(
        phase="deliver", tier="full", round_number=1, snapshot=SNAPSHOT,
        authorized=True, decisions_resolved=True, capabilities_available=True,
        budget_remaining=True, progress_possible=True, review_required=True,
        requirements=frozenset({"R1", "R2"}), satisfied=frozenset({"R1", "R2"}),
        units=UNITS, owner_methods=checks("owner"), owner_evidence=coverage("owner"),
        reviewer=reviewer, findings=(),
    )
    return replace(gate, **changes)


def resolution():
    return Evidence("finding-check", "finding-F1", "owner", SNAPSHOT, "fresh", True, "reproduced", "counterexample")


class GateTests(unittest.TestCase):
    def test_positive_control_at_each_phase_tier_and_round(self):
        for phase, tier, round_number in itertools.product(("research", "plan", "execute", "deliver"), ("light", "standard", "full"), (1, 2, 3)):
            with self.subTest(phase=phase, tier=tier, round=round_number):
                self.assertEqual(decide(valid_gate(phase=phase, tier=tier, round_number=round_number)).state, "READY")

    def test_no_reviewer_required_for_light_or_standard(self):
        for tier, count in (("light", 1), ("standard", 2)):
            gate = valid_gate(tier=tier, review_required=False, reviewer=None, owner_methods=checks("owner", count))
            self.assertEqual(decide(gate).state, "READY")

    def test_full_mode_cannot_be_silently_downgraded(self):
        self.assertEqual(decide(valid_gate(review_required=False, reviewer=None)).state, "BLOCKED")

    def test_explicit_review_requirement_survives_light_tier(self):
        self.assertEqual(decide(valid_gate(tier="light", reviewer=None)).state, "BLOCKED")

    def test_required_authority_capability_and_budget_flags_fail_closed(self):
        names = ("authorized", "decisions_resolved", "capabilities_available", "budget_remaining", "progress_possible")
        for flags in itertools.product((False, True), repeat=len(names)):
            changes = dict(zip(names, flags))
            with self.subTest(flags=changes):
                expected = "READY" if all(flags) else "BLOCKED"
                self.assertEqual(decide(valid_gate(**changes)).state, expected)

    def test_missing_requirement_is_not_hidden_by_green_checks(self):
        result = decide(valid_gate(satisfied=frozenset({"R1"})))
        self.assertEqual(result.state, "REPAIR")
        self.assertIn("acceptance-gap", result.reasons)

    def test_missing_owner_page_and_missing_reviewer_page(self):
        gate = valid_gate()
        for changed in (
            replace(gate, owner_evidence=gate.owner_evidence[:1]),
            replace(gate, reviewer=replace(gate.reviewer, evidence=gate.reviewer.evidence[:1])),
        ):
            self.assertEqual(decide(changed).state, "REPAIR")

    def test_each_snapshot_dependency_change_invalidates_fresh_evidence(self):
        for field in ("artifact", "contract", "environment"):
            old = replace(SNAPSHOT, **{field: "old"})
            with self.subTest(field=field):
                self.assertEqual(decide(valid_gate(owner_evidence=coverage("owner", old))).state, "REPAIR")

    def test_documented_reuse_can_target_current_contract_and_environment(self):
        previous = Snapshot("artifact-1", "contract-old", "environment-old")
        reused = tuple(replace(e, snapshot=previous, status="reused", reuse_target=SNAPSHOT, applicability_checked=True, reuse_reason="Only an unrelated packaging note changed; inspected dependency delta", applicability_evidence="bounded-impact-record") for e in coverage("owner"))
        self.assertEqual(decide(valid_gate(owner_evidence=reused)).state, "READY")

    def test_reuse_requires_each_applicability_field(self):
        evidence = replace(coverage("owner")[0], status="reused", snapshot=Snapshot("old", "old", "old"), reuse_target=SNAPSHOT, applicability_checked=True, reuse_reason="bounded change", applicability_evidence="delta-check")
        variants = (
            replace(evidence, reuse_target=None),
            replace(evidence, applicability_checked=False),
            replace(evidence, reuse_reason=""),
            replace(evidence, applicability_evidence=""),
            replace(evidence, reuse_target=Snapshot("wrong", "wrong", "wrong")),
        )
        for variant in variants:
            with self.subTest(variant=variant):
                self.assertEqual(decide(valid_gate(owner_evidence=(variant, coverage("owner")[1]))).state, "REPAIR")

    def test_reuse_cannot_be_relabeled_fresh(self):
        old = tuple(replace(e, snapshot=Snapshot("old", "contract-1", "environment-1"), status="fresh", applicability_checked=True) for e in coverage("owner"))
        self.assertEqual(decide(valid_gate(owner_evidence=old)).state, "REPAIR")

    def test_missing_failed_and_blocked_evidence_do_not_cover_a_unit(self):
        for status in ("missing", "failed", "blocked"):
            gate = valid_gate(owner_evidence=tuple(replace(e, status=status) for e in coverage("owner")))
            self.assertEqual(decide(gate).state, "REPAIR")

    def test_failed_result_cannot_be_counted_as_fresh_pass(self):
        self.assertEqual(decide(valid_gate(owner_evidence=tuple(replace(e, passed=False) for e in coverage("owner")))).state, "REPAIR")

    def test_owner_evidence_cannot_impersonate_reviewer(self):
        gate = valid_gate()
        gate = replace(gate, reviewer=replace(gate.reviewer, evidence=coverage("owner")))
        self.assertEqual(decide(gate).state, "REPAIR")

    def test_incomplete_or_contaminated_reviewer(self):
        gate = valid_gate()
        for changes in ({"available": False}, {"fresh_context": False}, {"author_advocacy_present": True}, {"within_authority": False}, {"methods_selected_independently": False}):
            with self.subTest(changes=changes):
                self.assertEqual(decide(replace(gate, reviewer=replace(gate.reviewer, **changes))).state, "BLOCKED")

    def test_approval_without_methods_or_coverage_is_not_review(self):
        gate = valid_gate()
        incomplete = replace(gate.reviewer, methods=(), evidence=())
        self.assertEqual(decide(replace(gate, reviewer=incomplete)).state, "REPAIR")

    def test_owner_and_reviewer_methods_are_additive_not_interchangeable(self):
        self.assertEqual(decide(valid_gate(owner_methods=checks("owner", 2))).state, "REPAIR")
        gate = valid_gate()
        self.assertEqual(decide(replace(gate, reviewer=replace(gate.reviewer, methods=checks("reviewer", 2)))).state, "REPAIR")

    def test_method_relabeling_and_unperformed_checks_are_rejected(self):
        methods = checks("owner")
        variants = (
            (methods[0], replace(methods[0], id="new-1"), replace(methods[0], id="new-2")),
            tuple(replace(m, procedure="same inspection") for m in methods),
            tuple(replace(m, performed=False) for m in methods),
            tuple(replace(m, evidence="") for m in methods),
        )
        for variant in variants:
            self.assertEqual(decide(valid_gate(owner_methods=variant)).state, "REPAIR")

    def test_no_defect_quota_and_no_cross_role_method_difference_requirement(self):
        gate = valid_gate(findings=())
        reviewer = replace(gate.reviewer, methods=gate.owner_methods)
        self.assertEqual(decide(replace(gate, reviewer=reviewer)).state, "READY")

    def test_confirmed_material_finding_needs_current_closure(self):
        finding = Finding("F1", "confirmed", True)
        self.assertEqual(decide(valid_gate(findings=(finding,))).state, "REPAIR")
        self.assertEqual(decide(valid_gate(findings=(replace(finding, resolution=resolution()),))).state, "READY")

    def test_refutation_requires_counterevidence(self):
        finding = Finding("F1", "refuted-with-evidence", True)
        self.assertEqual(decide(valid_gate(findings=(finding,))).state, "REPAIR")
        self.assertEqual(decide(valid_gate(findings=(replace(finding, resolution=resolution()),))).state, "READY")

    def test_material_unresolved_finding_is_a_gap_even_with_support(self):
        finding = Finding("F1", "unresolved", True, resolution=resolution())
        self.assertEqual(decide(valid_gate(findings=(finding,))).state, "REPAIR")

    def test_duplicate_does_not_hide_canonical_blocker(self):
        findings = (Finding("F1", "confirmed", True), Finding("F2", "duplicate", True, canonical_id="F1"))
        self.assertEqual(decide(valid_gate(findings=findings)).state, "REPAIR")

    def test_invalid_duplicate_cycle_or_missing_canonical_blocks(self):
        for findings in (
            (Finding("F1", "duplicate", True, canonical_id="absent"),),
            (Finding("F1", "duplicate", True, canonical_id="F2"), Finding("F2", "duplicate", True, canonical_id="F1")),
        ):
            self.assertEqual(decide(valid_gate(findings=findings)).state, "BLOCKED")

    def test_out_of_scope_requires_authority_and_does_not_remove_acceptance(self):
        finding = Finding("F1", "out-of-scope", True)
        self.assertEqual(decide(valid_gate(findings=(finding,))).state, "REPAIR")
        documented = replace(finding, scope_decision="approved-exclusion-D1", resolution=resolution())
        self.assertEqual(decide(valid_gate(findings=(documented,))).state, "READY")
        self.assertEqual(decide(valid_gate(findings=(documented,), satisfied=frozenset({"R1"}))).state, "REPAIR")

    def test_round_limit_with_and_without_repairs(self):
        for number, expected in ((1, "REPAIR"), (2, "REPAIR"), (3, "BLOCKED")):
            decision = decide(valid_gate(round_number=number, satisfied=frozenset()))
            self.assertEqual(decision.state, expected)
            self.assertIn("acceptance-gap", decision.reasons)
            self.assertEqual("rounds-exhausted" in decision.reasons, number == 3, decision.reasons)
        self.assertEqual(decide(valid_gate(round_number=3)).state, "READY")
        self.assertEqual(decide(valid_gate(round_number=4)).state, "BLOCKED")

    def test_version_changes_do_not_reset_round_number(self):
        for version in ("v3", "v4", "renamed-final"):
            gate = valid_gate(round_number=3, snapshot=replace(SNAPSHOT, artifact=version), satisfied=frozenset())
            self.assertEqual(decide(gate).state, "BLOCKED")

    def test_malformed_gate_values_fail_closed(self):
        for changes in ({"round_number": True}, {"round_number": 0}, {"phase": "unknown"}, {"tier": "unknown"}, {"units": frozenset()}, {"authorized": "yes"}, {"requirements": frozenset()}):
            with self.subTest(changes=changes):
                self.assertEqual(decide(valid_gate(**changes)).state, "BLOCKED")

    def test_duplicate_ids_fail_closed(self):
        gate = valid_gate()
        duplicated = gate.owner_evidence + (gate.owner_evidence[0],)
        self.assertEqual(decide(replace(gate, owner_evidence=duplicated)).state, "BLOCKED")
        self.assertEqual(decide(valid_gate(findings=(Finding("F1", "confirmed", True), Finding("F1", "unresolved", True)))).state, "BLOCKED")

    def test_missing_observation_or_locator_does_not_count_as_evidence(self):
        for field in ("observation", "locator"):
            changed = tuple(replace(e, **{field: ""}) for e in coverage("owner"))
            self.assertEqual(decide(valid_gate(owner_evidence=changed)).state, "REPAIR")

    def test_optional_review_cannot_hide_an_authority_violation(self):
        gate = valid_gate(tier="standard", review_required=False)
        unauthorized = replace(gate.reviewer, within_authority=False)
        self.assertEqual(decide(replace(gate, reviewer=unauthorized)).state, "BLOCKED")

    def test_revalidated_failure_cannot_be_hidden_by_a_passing_record(self):
        gate = valid_gate()
        failed = replace(gate.owner_evidence[0], id="retained-failure", passed=False, snapshot=Snapshot("old", "old", "old"), status="reused", reuse_target=SNAPSHOT, applicability_checked=True, reuse_reason="Failure still applies", applicability_evidence="current-impact-check")
        self.assertEqual(decide(replace(gate, owner_evidence=gate.owner_evidence + (failed,))).state, "REPAIR")

    def test_duplicate_failure_targets_require_repair_for_both_roles(self):
        for role in ("owner", "reviewer"):
            gate = valid_gate()
            methods = tuple(replace(method, failure_target=" Shared   failure target ") for method in checks(role))
            if role == "owner":
                gate = replace(gate, owner_methods=methods)
            else:
                gate = replace(gate, reviewer=replace(gate.reviewer, methods=methods))
            with self.subTest(role=role):
                decision = decide(gate)
                self.assertEqual(decision.state, "REPAIR")
                self.assertIn(f"{role}-methods", decision.reasons)

    def test_shared_oracle_does_not_make_distinct_methods_duplicates(self):
        gate = valid_gate()
        self.assertEqual({method.oracle for method in gate.owner_methods}, {"contract"})
        self.assertEqual(decide(gate).state, "READY")

    def test_nonmaterial_confirmed_finding_needs_repair_or_authorized_deferral(self):
        finding = Finding("F1", "confirmed", False)
        self.assertEqual(decide(valid_gate(findings=(finding,))).state, "REPAIR")
        self.assertEqual(decide(valid_gate(findings=(replace(finding, resolution=resolution()),))).state, "READY")
        deferred = replace(finding, deferral_decision="approved-D1", deferral_reason="Non-blocking wording polish", follow_up="Tracked for the next approved revision")
        self.assertEqual(decide(valid_gate(findings=(deferred,))).state, "READY")
        for field in ("deferral_decision", "deferral_reason", "follow_up"):
            with self.subTest(field=field):
                self.assertEqual(decide(valid_gate(findings=(replace(deferred, **{field: " "}),))).state, "REPAIR")
        self.assertEqual(decide(valid_gate(findings=(replace(deferred, material=True),))).state, "REPAIR")

    def test_duplicate_method_ids_are_malformed_for_each_role(self):
        for role in ("owner", "reviewer"):
            gate = valid_gate()
            original = checks(role)
            methods = (original[0], replace(original[1], id=original[0].id), original[2])
            changed = replace(gate, owner_methods=methods) if role == "owner" else replace(gate, reviewer=replace(gate.reviewer, methods=methods))
            with self.subTest(role=role):
                result = decide(changed)
                self.assertEqual(result.state, "BLOCKED")
                self.assertIn("invalid-record", result.reasons)

    def test_standard_review_needs_one_actual_method_full_needs_three(self):
        gate = valid_gate(tier="standard", review_required=True)
        one = replace(gate.reviewer, methods=checks("reviewer", 1))
        self.assertEqual(decide(replace(gate, reviewer=one)).state, "READY")
        self.assertEqual(decide(replace(gate, reviewer=replace(one, methods=()))).state, "REPAIR")
        self.assertEqual(decide(replace(gate, tier="full", reviewer=one)).state, "REPAIR")


if __name__ == "__main__":
    unittest.main()
