"""Seed one implementation fault at a time into a temporary copy and confirm the tests catch it.

Each mutation is a single textual substitution in one file of the copy. A mutation counts as
killed only when the named test module runs, exits nonzero, and reports at least one failing
assertion; syntax and import errors are reported as invalid rather than as detections. The
source tree is never modified. This measures the sensitivity of the deterministic tests to the
listed faults; it is not exhaustive mutation coverage, model behavior, or independent review.
"""
import argparse
import ast
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from scripts.check_package import ROOT, load_json, source_manifest, write_report


MUTATIONS = (
    # Gate model
    ("always-ready", "evals/gate_model.py", "return _decide(gate)", 'return Decision("READY", ())', "test_gates.py"),
    ("always-blocked", "evals/gate_model.py", "return _decide(gate)", 'return Decision("BLOCKED", ("mutant",))', "test_gates.py"),
    ("partial-coverage-as-complete", "evals/gate_model.py", "return units <= covered and not current_failures", "return bool(covered) and not current_failures", "test_gates.py"),
    ("skip-required-review", "evals/gate_model.py", 'if gate.tier == "full" or gate.review_required:', "if False:", "test_gates.py"),
    ("accept-stale-evidence", "evals/gate_model.py", "return evidence.snapshot == target and evidence.reuse_target is None", "return evidence.reuse_target is None", "test_gates.py"),
    ("allow-fourth-round", "evals/gate_model.py", "or not 1 <= gate.round_number <= 3", "or not 1 <= gate.round_number", "test_gates.py"),
    ("unsupported-refutation", "evals/gate_model.py", 'if canonical.classification == "refuted-with-evidence" and not has_resolution:', 'if canonical.classification == "refuted-with-evidence" and False:', "test_gates.py"),
    ("ignore-failure-target-duplicates", "evals/gate_model.py", '("family", "procedure", "failure_target")', '("family", "procedure")', "test_gates.py"),
    ("ignore-unclosed-minor-findings", "evals/gate_model.py", 'if canonical.classification == "confirmed" and not has_resolution and not authorized_deferral:', 'if canonical.classification == "confirmed" and material and not has_resolution and not authorized_deferral:', "test_gates.py"),
    ("permit-material-deferral", "evals/gate_model.py", "authorized_deferral = not material and all(", "authorized_deferral = all(", "test_gates.py"),
    ("misclassify-duplicate-method-ids", "evals/gate_model.py", "or not _unique_ids(gate.owner_methods)", "or False", "test_gates.py"),
    ("drop-rounds-exhausted-reason", "evals/gate_model.py", 'reasons = gaps + (["rounds-exhausted"] if gate.round_number == 3 else [])', "reasons = gaps", "test_gates.py"),
    # Metrics
    ("drop-failed-attempts", "evals/metrics.py", "    for record in records:\n        _validate(record, study)", '    records = [record for record in records if record["status"] == "accepted"]\n    for record in records:\n        _validate(record, study)', "test_metrics.py"),
    ("replace-unknown-metrics-with-zero", "evals/metrics.py", 'values = [record["metrics"][name] for record in records if record["metrics"][name] is not None]', 'values = [record["metrics"][name] or 0 for record in records]', "test_metrics.py"),
    ("ignore-required-comparison-arms", "evals/metrics.py", 'limitations = [f"{arm}-arm-absent" for arm in REQUIRED_COMPARISON_ARMS if arm not in study["arms"]]', "limitations = []", "test_metrics.py"),
    # Package checks
    ("disable-privacy-patterns", "scripts/check_package.py", "found = [name for name, pattern in patterns.items() if re.search(pattern, text, re.IGNORECASE)]", "found = []", "test_package.py"),
    ("restore-alpha-only-version", "scripts/check_package.py", "not SEMVER.fullmatch(version)", 'not re.fullmatch(r"[0-9]+\\.[0-9]+\\.[0-9]+-alpha\\.[0-9]+", version)', "test_package.py"),
    ("restore-fixed-activation-count", "scripts/check_package.py", "len(activation_ids) < MIN_ACTIVATION_CASES", "len(activation_ids) != MIN_ACTIVATION_CASES", "test_package.py"),
    ("restore-overbroad-tilde-path", "scripts/check_package.py", r"(?<![\w~])~[A-Za-z_][A-Za-z0-9._\-]*/", r"~[A-Za-z0-9._\-]+/", "test_package.py"),
    ("accept-dot-segments-in-inventory-paths", "scripts/check_package.py", 'part not in {".", "..", ""}', 'part not in {""}', "test_package.py"),
    ("accept-empty-and-absolute-inventory-segments", "scripts/check_package.py", 'part not in {".", "..", ""}', 'part not in {".", ".."}', "test_package.py"),
    ("ignore-unlinked-resources", "scripts/check_package.py", 'issues.append(f"{SKILL}: resource-not-directly-linked:{relative}")', "pass", "test_package.py"),
    ("ignore-one-way-scenario-map", "scripts/check_package.py", 'issues.append("review/requirements.json: scenario-map-not-bidirectional")', "pass", "test_package.py"),
    ("accept-non-string-frontmatter-scalars", "scripts/check_package.py", "target[key] = _frontmatter_string(value)", "target[key] = json.loads(value) if value.startswith('\"') else value", "test_package.py"),
    ("ignore-public-version-drift", "scripts/check_package.py", 'issues.append(f"{name}: public-version-missing:{version}")', "pass", "test_package.py"),
    # Archive and installation
    ("skip-archive-content-hashes", "scripts/package_review.py", "if actual != manifest:", "if False:", "test_package.py"),
    ("accept-non-normalized-archive-metadata", "scripts/package_review.py", 'raise ValueError("non-normalized archive metadata")', "pass", "test_package.py"),
    ("ignore-altered-installed-files", "scripts/verify_install.py", "changed = sorted(name for name in source_files.keys() & installed_files.keys() if source_files[name] != installed_files[name])", "changed = []", "test_package.py"),
)


def run_mutation(root, inventory, mutation, workspace):
    name, relative, old, new, pattern = mutation
    with tempfile.TemporaryDirectory(prefix="sureforge-mutation-", dir=workspace) as directory:
        candidate = Path(directory) / "candidate"
        for filename in inventory:
            destination = candidate / filename
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(root / filename, destination)
        target = candidate / relative
        text = target.read_text(encoding="utf-8")
        if text.count(old) != 1:
            raise ValueError(f"ambiguous mutation target: {name}")
        changed = text.replace(old, new, 1)
        ast.parse(changed, filename=relative)
        target.write_text(changed, encoding="utf-8")
        process = subprocess.run(
            [sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests", "-p", pattern, "-v"],
            cwd=candidate, capture_output=True, text=True, timeout=300,
            env=dict(os.environ, SUREFORGE_MUTATION_AUDIT="1"),
        )
        output = process.stdout + process.stderr
        counts = re.search(r"Ran (\d+) tests?", output)
        failed = re.findall(r"^(?:FAIL|ERROR): (.+)$", output, re.MULTILINE)
        invalid = any(marker in output for marker in ("SyntaxError:", "ImportError:", "ModuleNotFoundError:"))
        status = "killed" if process.returncode != 0 and counts and failed and not invalid else "survived-or-invalid"
        return {
            "mutation": name, "file": relative, "test_module": pattern,
            "mutated_file_sha256": hashlib.sha256(changed.encode("utf-8")).hexdigest(),
            "status": status, "return_code": process.returncode,
            "tests_run": int(counts.group(1)) if counts else 0,
            "failing_tests": failed,
        }


def audit(root=ROOT, workspace=None, mutations=MUTATIONS):
    root = Path(root).resolve()
    before = source_manifest(root)
    inventory = load_json((root / "review/inventory.json").read_text(encoding="utf-8"))["files"]
    observations = []
    for mutation in mutations:
        observation = run_mutation(root, inventory, mutation, workspace)
        observations.append(observation)
        print(f"{observation['mutation']}: {observation['status']} ({observation['tests_run']} tests)", flush=True)
    unchanged = source_manifest(root) == before
    killed = sum(item["status"] == "killed" for item in observations)
    return {
        "kind": "seeded-implementation-fault-audit",
        "status": "passed" if unchanged and killed == len(observations) else "failed",
        "source_sha256": before["source_sha256"],
        "source_unchanged": unchanged,
        "mutations_attempted": len(observations),
        "mutations_killed": killed,
        "observations": observations,
        "limits": "Sensitivity of the deterministic tests to the listed faults only; not exhaustive mutation coverage, model behavior, independent review, or absence of defects.",
    }


def main():
    parser = argparse.ArgumentParser(description="Seed implementation faults into temporary copies and confirm the tests catch them.")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--report", type=Path, help="Write the JSON report to this new file outside the source tree.")
    parser.add_argument("--workspace", type=Path, help="Existing directory for temporary copies; defaults to the system temporary directory.")
    args = parser.parse_args()
    try:
        report = audit(args.root, args.workspace)
        if args.report:
            write_report(args.report, report, args.root)
    except (OSError, ValueError, subprocess.TimeoutExpired) as error:
        parser.exit(1, f"Mutation audit failed: {error}\n")
    print(json.dumps({key: value for key, value in report.items() if key != "observations"}, indent=2, sort_keys=True))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
