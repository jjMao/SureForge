from dataclasses import dataclass


@dataclass(frozen=True)
class Snapshot:
    artifact: str
    contract: str
    environment: str


@dataclass(frozen=True)
class Method:
    id: str
    family: str
    failure_target: str
    procedure: str
    oracle: str
    evidence: str
    performed: bool


@dataclass(frozen=True)
class Evidence:
    id: str
    unit: str
    role: str
    snapshot: Snapshot
    status: str
    passed: bool
    observation: str
    locator: str
    reuse_target: Snapshot | None = None
    applicability_checked: bool = False
    reuse_reason: str = ""
    applicability_evidence: str = ""


@dataclass(frozen=True)
class Review:
    available: bool
    fresh_context: bool
    author_advocacy_present: bool
    within_authority: bool
    methods_selected_independently: bool
    methods: tuple[Method, ...]
    evidence: tuple[Evidence, ...]


@dataclass(frozen=True)
class Finding:
    id: str
    classification: str
    material: bool
    resolution: Evidence | None = None
    canonical_id: str | None = None
    scope_decision: str | None = None
    deferral_decision: str | None = None
    deferral_reason: str | None = None
    follow_up: str | None = None


@dataclass(frozen=True)
class Gate:
    phase: str
    tier: str
    round_number: int
    snapshot: Snapshot
    authorized: bool
    decisions_resolved: bool
    capabilities_available: bool
    budget_remaining: bool
    progress_possible: bool
    review_required: bool
    requirements: frozenset[str]
    satisfied: frozenset[str]
    units: frozenset[str]
    owner_methods: tuple[Method, ...]
    owner_evidence: tuple[Evidence, ...]
    reviewer: Review | None
    findings: tuple[Finding, ...]


@dataclass(frozen=True)
class Decision:
    state: str
    reasons: tuple[str, ...]


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _snapshot(value):
    return isinstance(value, Snapshot) and all(_text(v) for v in (value.artifact, value.contract, value.environment))


def _unique_ids(items):
    ids = [item.id for item in items]
    return all(_text(item) for item in ids) and len(ids) == len(set(ids))


def applicable(evidence, target, role=None, require_pass=True):
    if not isinstance(evidence, Evidence) or not _snapshot(evidence.snapshot) or not _snapshot(target):
        return False
    if type(evidence.passed) is not bool or (require_pass and not evidence.passed):
        return False
    if not all(_text(v) for v in (evidence.id, evidence.unit, evidence.observation, evidence.locator)):
        return False
    if evidence.role not in {"owner", "reviewer", "critic"} or (role is not None and evidence.role != role):
        return False
    if evidence.status == "fresh" or (not require_pass and evidence.status == "failed"):
        return evidence.snapshot == target and evidence.reuse_target is None
    if evidence.status == "reused":
        return (
            evidence.reuse_target == target
            and evidence.applicability_checked is True
            and _text(evidence.reuse_reason)
            and _text(evidence.applicability_evidence)
        )
    return False


def _methods_sufficient(methods, minimum):
    if len(methods) < minimum or not _unique_ids(methods):
        return False
    if any(not isinstance(method, Method) or method.performed is not True or not all(_text(v) for v in (method.family, method.failure_target, method.procedure, method.oracle, method.evidence)) for method in methods):
        return False
    distinct = ({" ".join(getattr(method, field).split()).casefold() for method in methods} for field in ("family", "procedure", "failure_target"))
    return all(len(values) >= minimum for values in distinct)


def _coverage_sufficient(evidence, units, target, role):
    covered = {item.unit for item in evidence if applicable(item, target, role)}
    current_failures = any(
        item.unit in units and item.passed is False and applicable(item, target, role, require_pass=False)
        for item in evidence
    )
    return units <= covered and not current_failures


def _finding_gaps(findings, snapshot):
    known = {finding.id: finding for finding in findings}
    allowed = {"confirmed", "refuted-with-evidence", "unresolved", "duplicate", "out-of-scope"}
    gaps = []
    for finding in findings:
        if finding.classification not in allowed or type(finding.material) is not bool:
            raise ValueError("invalid finding")
        canonical = finding
        visited = set()
        while canonical.classification == "duplicate":
            if canonical.id in visited or canonical.canonical_id not in known:
                raise ValueError("invalid duplicate chain")
            visited.add(canonical.id)
            canonical = known[canonical.canonical_id]
        material = finding.material or canonical.material
        has_resolution = applicable(canonical.resolution, snapshot)
        authorized_deferral = not material and all(_text(value) for value in (canonical.deferral_decision, canonical.deferral_reason, canonical.follow_up))
        if canonical.classification == "confirmed" and not has_resolution and not authorized_deferral:
            gaps.append("unclosed-finding")
        if canonical.classification == "refuted-with-evidence" and not has_resolution:
            gaps.append("unsupported-refutation")
        if canonical.classification == "unresolved" and material:
            gaps.append("unresolved-finding")
        if canonical.classification == "out-of-scope" and not (has_resolution and _text(canonical.scope_decision)):
            gaps.append("unsupported-exclusion")
    return gaps


def _decide(gate):
    boolean_fields = (
        gate.authorized, gate.decisions_resolved, gate.capabilities_available,
        gate.budget_remaining, gate.progress_possible, gate.review_required,
    )
    if (
        gate.phase not in {"research", "plan", "execute", "deliver"}
        or gate.tier not in {"light", "standard", "full"}
        or type(gate.round_number) is not int
        or not 1 <= gate.round_number <= 3
        or not _snapshot(gate.snapshot)
        or any(type(value) is not bool for value in boolean_fields)
        or not gate.requirements or not gate.units
        or any(not isinstance(values, frozenset) or not all(_text(value) for value in values) for values in (gate.requirements, gate.satisfied, gate.units))
        or not _unique_ids(gate.owner_evidence)
        or not _unique_ids(gate.owner_methods)
        or not _unique_ids(gate.findings)
        or (gate.reviewer is not None and (not _unique_ids(gate.reviewer.methods) or not _unique_ids(gate.reviewer.evidence)))
    ):
        return Decision("BLOCKED", ("invalid-record",))

    blockers = []
    for value, reason in (
        (gate.authorized, "unauthorized"),
        (gate.decisions_resolved, "unanswered-decision"),
        (gate.capabilities_available, "missing-capability"),
        (gate.budget_remaining, "budget-exhausted"),
        (gate.progress_possible, "no-progress"),
    ):
        if not value:
            blockers.append(reason)

    if gate.reviewer is not None and gate.reviewer.available is True and gate.reviewer.within_authority is not True:
        blockers.append("unauthorized-review")

    gaps = []
    if not gate.requirements <= gate.satisfied:
        gaps.append("acceptance-gap")
    minimum = {"light": 1, "standard": 2, "full": 3}[gate.tier]
    if not _methods_sufficient(gate.owner_methods, minimum):
        gaps.append("owner-methods")
    if not _coverage_sufficient(gate.owner_evidence, gate.units, gate.snapshot, "owner"):
        gaps.append("owner-coverage")

    if gate.tier == "full" or gate.review_required:
        review = gate.reviewer
        if review is None or review.available is not True:
            blockers.append("missing-reviewer")
        else:
            if not _unique_ids(review.evidence):
                blockers.append("invalid-review-evidence")
            if review.fresh_context is not True or review.author_advocacy_present is not False:
                blockers.append("review-context-not-independent")
            if review.within_authority is not True or review.methods_selected_independently is not True:
                blockers.append("review-not-authorized-or-self-selected")
            if not _methods_sufficient(review.methods, 3 if gate.tier == "full" else 1):
                gaps.append("reviewer-methods")
            if not _coverage_sufficient(review.evidence, gate.units, gate.snapshot, "reviewer"):
                gaps.append("reviewer-coverage")

    gaps.extend(_finding_gaps(gate.findings, gate.snapshot))
    if blockers:
        return Decision("BLOCKED", tuple(sorted(set(blockers + gaps))))
    if gaps:
        reasons = gaps + (["rounds-exhausted"] if gate.round_number == 3 else [])
        return Decision("BLOCKED" if gate.round_number == 3 else "REPAIR", tuple(sorted(set(reasons))))
    return Decision("READY", ())


def decide(gate):
    try:
        return _decide(gate)
    except (AttributeError, TypeError, ValueError):
        return Decision("BLOCKED", ("invalid-record",))
