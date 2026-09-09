import csv
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from decimal import Decimal
from html.parser import HTMLParser
from pathlib import Path

from evals.fixtures.order_totals import total_orders as broken_total_orders
from scripts.check_package import load_json, privacy_findings, source_manifest, validate_package
from scripts.package_review import build_bundle, verify_archive
from scripts.verify_install import compare_install


ROOT = Path(__file__).resolve().parents[1]


class PackageTests(unittest.TestCase):
    def setUp(self):
        self.workspace = tempfile.TemporaryDirectory(prefix="sureforge-test-")
        self.addCleanup(self.workspace.cleanup)
        self.base = Path(self.workspace.name)
        self.root = self.base / "candidate"
        inventory = load_json((ROOT / "review/inventory.json").read_text(encoding="utf-8"))["files"]
        self.root.mkdir()
        for relative in inventory:
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, target)

    def rewrite(self, relative, old, new):
        path = self.root / relative
        text = path.read_text(encoding="utf-8")
        self.assertIn(old, text)
        path.write_text(text.replace(old, new, 1), encoding="utf-8")

    def assert_rejected(self, token):
        report = validate_package(self.root)
        self.assertEqual(report["status"], "failed")
        self.assertTrue(any(token in issue for issue in report["issues"]), report["issues"])

    def test_complete_source_is_accepted(self):
        report = validate_package(self.root)
        self.assertEqual(report["status"], "passed", report["issues"])
        self.assertEqual(report["files_checked"], 44)

    def test_skill_name_mismatch_is_rejected(self):
        self.rewrite("skills/sureforge/SKILL.md", "name: sureforge", "name: WrongName")
        self.assert_rejected("skill-name")

    def test_version_drift_is_rejected(self):
        current = (self.root / "VERSION").read_text(encoding="utf-8").strip()
        self.rewrite("skills/sureforge/SKILL.md", f'version: "{current}"', 'version: "9.9.9-incorrect"')
        self.assert_rejected("version-mismatch")

    def test_missing_resource_is_rejected(self):
        (self.root / "skills/sureforge/assets/critic-brief.md").unlink()
        self.assert_rejected("missing-file")

    def test_license_drift_is_rejected(self):
        self.rewrite("skills/sureforge/LICENSE", "MIT License", "Changed License")
        self.assert_rejected("license-mismatch")

    def test_broken_link_and_anchor_are_rejected(self):
        self.rewrite("README.md", "(CONTRIBUTING.md)", "(absent.md)")
        self.assert_rejected("broken-link")
        self.rewrite("README.md", "(#verification)", "(#no-such-heading)")
        self.assert_rejected("broken-anchor")

    def test_traversal_link_is_rejected(self):
        self.rewrite("README.md", "(LICENSE)", "(../outside.txt)")
        self.assert_rejected("escaping-link")

    def test_unknown_file_is_not_silently_packaged(self):
        (self.root / "private-notes.txt").write_text("Do not distribute.\n", encoding="utf-8")
        self.assert_rejected("unlisted-file")

    def test_symlink_is_rejected_without_reading_its_target(self):
        secret = self.base / "outside.txt"
        secret.write_text("outside the distribution\n", encoding="utf-8")
        (self.root / "external.txt").symlink_to(secret)
        self.assert_rejected("symlink")

    def test_directory_symlink_is_rejected(self):
        (self.root / "external-directory").symlink_to(self.base, target_is_directory=True)
        self.assert_rejected("symlink")

    def test_duplicate_json_keys_are_not_silently_accepted(self):
        with self.assertRaises(ValueError):
            load_json('{"a": 1, "a": 2}')
        with self.assertRaises(ValueError):
            load_json('{"cost": NaN}')

    def test_missing_scenario_is_rejected(self):
        path = self.root / "evals/cases.json"
        data = load_json(path.read_text(encoding="utf-8"))
        data["cases"].pop()
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        self.assert_rejected("failure-scenarios")

    def test_missing_activation_case_is_rejected(self):
        path = self.root / "evals/activation.json"
        data = load_json(path.read_text(encoding="utf-8"))
        data["cases"].pop()
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        self.assert_rejected("activation-cases")

    def test_missing_requirement_mapping_is_rejected(self):
        path = self.root / "review/requirements.json"
        data = load_json(path.read_text(encoding="utf-8"))
        data["requirements"].pop()
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        self.assert_rejected("requirement-map")

    def test_false_unconfirmed_baseline_label_is_rejected(self):
        self.rewrite("evals/arms/current-instructions.txt", "RECONSTRUCTED BASELINE CANDIDATE", "VERIFIED BASELINE")
        self.assert_rejected("baseline-provenance")

    def test_privacy_patterns_and_explicit_private_terms(self):
        private_email = "private" + "@" + "example.test"
        home_path = "/" + "Users" + "/private-account/project"
        fake_token = "gh" + "p_" + "x" * 40
        for text in (private_email, home_path, fake_token):
            self.assertTrue(privacy_findings(text))
        self.assertTrue(privacy_findings("Private Marker", private_terms=("Private Marker",)))
        self.assertEqual(privacy_findings("Copyright (c) 2026 Da7-Tech"), [])

    def test_content_privacy_violation_is_rejected(self):
        path = self.root / "README.md"
        path.write_text(path.read_text(encoding="utf-8") + "private" + "@" + "example.test\n", encoding="utf-8")
        self.assert_rejected("email")

    def test_snapshot_changes_with_any_source_edit(self):
        before = source_manifest(self.root)
        self.rewrite("README.md", "An instruction-only", "A portable instruction-only")
        after = source_manifest(self.root)
        self.assertNotEqual(before["source_sha256"], after["source_sha256"])
        self.assertNotEqual(before["files"]["README.md"], after["files"]["README.md"])
        self.assertEqual(before["files"]["LICENSE"], after["files"]["LICENSE"])

    def test_archive_roundtrip_and_metadata(self):
        target = self.base / "review.zip"
        report = build_bundle(self.root, target)
        self.assertEqual(report["status"], "passed")
        self.assertEqual(verify_archive(target, self.root)["source_sha256"], source_manifest(self.root)["source_sha256"])
        with zipfile.ZipFile(target) as archive:
            self.assertEqual(archive.comment, b"")
            self.assertEqual(len(archive.infolist()), 45)
            for entry in archive.infolist():
                self.assertTrue(entry.filename.startswith("SureForge/") or entry.filename == "MANIFEST.json")
                self.assertEqual(entry.extra, b"")
                self.assertEqual(entry.comment, b"")
                self.assertEqual(entry.date_time, (2020, 1, 1, 0, 0, 0))
                self.assertEqual((entry.external_attr >> 16) & 0o777, 0o644)

    def test_archive_does_not_overwrite_existing_output(self):
        target = self.base / "review.zip"
        target.write_bytes(b"existing-user-data")
        with self.assertRaises(FileExistsError):
            build_bundle(self.root, target)
        self.assertEqual(target.read_bytes(), b"existing-user-data")

    def test_archive_tampering_is_detected(self):
        target = self.base / "review.zip"
        build_bundle(self.root, target)
        tampered = self.base / "tampered.zip"
        with zipfile.ZipFile(target) as original, zipfile.ZipFile(tampered, "w") as changed:
            for entry in original.infolist():
                data = original.read(entry.filename)
                if entry.filename == "SureForge/README.md":
                    data += b"tampered\n"
                changed.writestr(entry, data)
        with self.assertRaises(ValueError):
            verify_archive(tampered)

    def test_archive_extra_member_is_detected(self):
        target = self.base / "review.zip"
        build_bundle(self.root, target)
        with zipfile.ZipFile(target, "a") as archive:
            archive.writestr("../outside.txt", "unexpected")
        with self.assertRaises(ValueError):
            verify_archive(target)

    def test_archive_staleness_is_detected_against_source(self):
        target = self.base / "review.zip"
        build_bundle(self.root, target)
        self.rewrite("README.md", "An instruction-only", "A portable instruction-only")
        with self.assertRaises(ValueError):
            verify_archive(target, self.root)

    def test_install_compares_all_files(self):
        source = self.root / "skills/sureforge"
        installed = self.base / "installed"
        shutil.copytree(source, installed)
        self.assertEqual(compare_install(source, installed)["status"], "passed")
        target = installed / "assets/critic-brief.md"
        target.write_text("altered\n", encoding="utf-8")
        self.assertEqual(compare_install(source, installed)["status"], "failed")
        target.unlink()
        self.assertIn("assets/critic-brief.md", compare_install(source, installed)["missing"])

    def test_install_rejects_extra_files_and_symlinks(self):
        source = self.root / "skills/sureforge"
        installed = self.base / "installed"
        shutil.copytree(source, installed)
        (installed / "extra.txt").write_text("extra\n", encoding="utf-8")
        self.assertEqual(compare_install(source, installed)["status"], "failed")
        (installed / "linked.txt").symlink_to(source / "SKILL.md")
        self.assertEqual(compare_install(source, installed)["status"], "failed")

    def test_extracted_review_package_can_run_its_documented_checks(self):
        target = self.base / "review.zip"
        build_bundle(self.root, target)
        with zipfile.ZipFile(target) as archive:
            archive.extractall(self.base / "unpacked")
        report = validate_package(self.base / "unpacked/SureForge")
        self.assertEqual(report["status"], "passed", report["issues"])

    def test_control_characters_are_not_valid_inventory_paths(self):
        path = self.root / "review/inventory.json"
        data = load_json(path.read_text(encoding="utf-8"))
        data["files"].append("bad\nname.txt")
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        self.assert_rejected("invalid-inventory")

    def test_malformed_url_is_reported_without_crashing_the_validator(self):
        self.rewrite("README.md", "(LICENSE)", "(https://[broken)")
        self.assert_rejected("invalid-link")

    def test_synthetic_order_oracle_and_intentional_regression(self):
        text = (self.root / "evals/fixtures/orders.csv").read_text(encoding="utf-8")
        rows = list(csv.DictReader(text.splitlines()))
        unique = {row["order_id"]: row for row in rows}
        included = [row for row in unique.values() if row["status"] in {"paid", "refund"}]
        totals = {region: sum((Decimal(row["amount"]) for row in included if row["region"] == region), Decimal("0")) for region in ("North", "South")}
        self.assertEqual((len(rows), len(unique), len(included)), (7, 6, 5))
        self.assertEqual(totals, {"North": Decimal("100.00"), "South": Decimal("50.00")})
        self.assertEqual(sum(totals.values()), Decimal("150.00"))
        self.assertEqual(sum(Decimal(row["amount"]) == 0 for row in included), 1)
        self.assertEqual(broken_total_orders(rows), {"North": Decimal("120.00"), "South": Decimal("100.00")})
        self.assertEqual((self.root / "evals/fixtures/orders.csv").read_text(encoding="utf-8"), text)

    def test_synthetic_vendor_oracle(self):
        data = load_json((self.root / "evals/fixtures/vendors.json").read_text(encoding="utf-8"))
        costs = {vendor["name"]: vendor["setup"] + 12 * vendor["monthly"] for vendor in data["vendors"]}
        eligible = [vendor["name"] for vendor in data["vendors"] if costs[vendor["name"]] <= 3000 and vendor["data_export"] and vendor["response_hours"] <= 4]
        self.assertIs(data["synthetic"], True)
        self.assertEqual(costs, {"North": 2340, "South": 2980, "East": 1200})
        self.assertEqual(eligible, ["South"])

    def test_visual_fixture_source_inventory_and_intentional_defects(self):
        class InventoryParser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.units = {}
                self.links = []

            def handle_starttag(self, tag, attributes):
                values = dict(attributes)
                if tag == "section":
                    self.units[values["data-unit"]] = values["id"]
                if tag == "a":
                    self.links.append(values["href"])

        text = (self.root / "evals/fixtures/handbook.html").read_text(encoding="utf-8")
        parser = InventoryParser()
        parser.feed(text)
        self.assertEqual(set(parser.units), {"1", "2", "3", "4", "5"})
        missing = {link[1:] for link in parser.links if link.startswith("#") and link[1:] not in parser.units.values()}
        self.assertEqual(missing, {"recovery-missing"})
        self.assertIn("max-width: 300px; overflow: hidden", text)
        self.assertIn("table { width: 560px", text)

    def test_coverage_template_separates_freshness_and_result(self):
        text = (self.root / "skills/sureforge/assets/coverage-ledger.csv").read_text(encoding="utf-8")
        rows = list(csv.reader(text.splitlines()))
        self.assertEqual(len(rows), 1)
        self.assertEqual(len(rows[0]), 20)
        self.assertEqual(len(set(rows[0])), 20)
        self.assertTrue({"status", "result", "role", "required", "evidence_snapshot", "applicability_checked_at"} <= set(rows[0]))

    def test_public_tool_identity_is_not_mistaken_for_private_username(self):
        from unittest.mock import patch

        for public_name in ("devin", "SureForge", "Da7-Tech"):
            with self.subTest(public_name=public_name), patch("scripts.check_package.Path.home", return_value=Path(public_name)):
                report = validate_package(self.root)
                self.assertEqual(report["status"], "passed", report["issues"])
                explicit = validate_package(self.root, private_terms=(public_name,))
                self.assertEqual(explicit["status"], "failed")

    def set_version(self, version):
        current = (self.root / "VERSION").read_text(encoding="utf-8").strip()
        for relative in ("VERSION", "skills/sureforge/SKILL.md", "evals/study.json"):
            path = self.root / relative
            path.write_text(path.read_text(encoding="utf-8").replace(current, version), encoding="utf-8")

    def test_semver_stable_and_prerelease_versions_are_accepted(self):
        for version in ("0.1.0", "0.1.0-beta.1", "0.1.0-rc.1", "1.0.0", "1.2.3-alpha", "1.2.3-0.3.7", "1.2.3+build.01", "1.2.3-rc.1+build.01"):
            self.set_version(version)
            with self.subTest(version=version):
                result = validate_package(self.root)
                self.assertEqual(result["status"], "passed", result["issues"])

    def test_malformed_semver_versions_are_rejected(self):
        for version in ("1.0", "v1.0.0", "01.0.0", "1.01.0", "1.0.01", "1.0.0-01", "1.0.0-alpha.01", "1.0.0-", "1.0.0+", "1.0.0-a..b"):
            self.set_version(version)
            with self.subTest(version=version):
                self.assert_rejected("version-mismatch")

    def test_activation_set_can_grow_beyond_twenty(self):
        path = self.root / "evals/activation.json"
        data = load_json(path.read_text(encoding="utf-8"))
        for count in (21, 22):
            data["cases"].append(dict(data["cases"][0], id=f"A{count}", prompt=f"Use SureForge for synthetic substantial task {count}."))
            path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
            with self.subTest(count=count):
                result = validate_package(self.root)
                self.assertEqual(result["status"], "passed", result["issues"])

    def test_activation_ids_must_be_unique_and_canonical(self):
        path = self.root / "evals/activation.json"
        data = load_json(path.read_text(encoding="utf-8"))
        for identifier in ("A01", "A00", "A1", "A001", "invalid", None):
            data["cases"][-1]["id"] = identifier
            path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
            with self.subTest(identifier=identifier):
                self.assert_rejected("activation-cases")

    def test_study_repetition_count_requires_an_integer(self):
        path = self.root / "evals/study.json"
        data = load_json(path.read_text(encoding="utf-8"))
        data["repetitions_per_cell"] = 3.0
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        self.assert_rejected("study-design")

    def test_finder_metadata_does_not_change_the_source_identity(self):
        before = source_manifest(self.root)
        (self.root / "evals/fixtures/.DS_Store").write_bytes(b"\xff\x00synthetic-metadata")
        checked = validate_package(self.root)
        self.assertEqual(checked["status"], "passed", checked["issues"])
        self.assertEqual(checked["ignored_metadata_files"], ["evals/fixtures/.DS_Store"])
        self.assertEqual(source_manifest(self.root), before)
        target = self.base / "metadata-free.zip"
        build_bundle(self.root, target)
        with zipfile.ZipFile(target) as archive:
            self.assertFalse(any(name.endswith(".DS_Store") for name in archive.namelist()))

    def test_finder_metadata_symlink_is_still_rejected(self):
        target = self.base / "outside-metadata"
        target.write_bytes(b"outside")
        (self.root / ".DS_Store").symlink_to(target)
        self.assert_rejected("symlink")

    def test_installation_comparison_ignores_reported_finder_metadata(self):
        source = self.root / "skills/sureforge"
        installed = self.base / "installed"
        shutil.copytree(source, installed)
        (installed / ".DS_Store").write_bytes(b"\xff\x00metadata")
        result = compare_install(source, installed)
        self.assertEqual(result["status"], "passed", result)
        self.assertEqual(result["ignored_metadata_files"]["installed"], [".DS_Store"])

    def test_report_path_errors_are_concise_and_preserve_existing_data(self):
        existing = self.base / "existing.json"
        existing.write_text("existing evidence\n", encoding="utf-8")
        for module in ("scripts.check_package", "scripts.verify_install"):
            for report_path in (existing, self.base / "absent/report.json", self.root / "forbidden-report.json"):
                command = [sys.executable, "-B", "-m", module, "--report", str(report_path)]
                if module.endswith("verify_install"):
                    command.extend(("--installed", str(self.root / "skills/sureforge")))
                result = subprocess.run(command, cwd=self.root, capture_output=True, text=True, timeout=30)
                with self.subTest(module=module, report=report_path.name):
                    self.assertNotEqual(result.returncode, 0)
                    self.assertNotIn("Traceback", result.stderr)
                    self.assertEqual(len(result.stderr.strip().splitlines()), 1)
        self.assertEqual(existing.read_text(encoding="utf-8"), "existing evidence\n")
        self.assertFalse((self.root / "forbidden-report.json").exists())

    def test_additional_credential_and_obfuscated_email_shapes(self):
        probes = (
            "AK" + "IA" + "A" * 16,
            "AS" + "IA" + "B" * 16,
            "aws_secret_access_key=" + "A" * 40,
            "example" + " [at] " + "example" + " [dot] " + "test",
            "eyJhbGciOiJIUzI1NiJ9" + "." + "eyJzdWIiOiJzeW50aGV0aWMifQ" + "." + "c3ludGhldGljLXNpZ25hdHVyZQ",
        )
        for number, value in enumerate(probes):
            with self.subTest(probe=number):
                self.assertTrue(privacy_findings(value))
        self.assertEqual(privacy_findings("Generic user skills path: ~/.config/devin/skills/"), [])

    def test_non_latin_script_signal_is_not_claimed_as_language_detection(self):
        path = self.root / "README.md"
        original = path.read_text(encoding="utf-8")
        for name, codepoint in (("arabic", 0x0645), ("cyrillic", 0x0416), ("cjk", 0x4E2D), ("hebrew", 0x05D0)):
            path.write_text(original + chr(codepoint) + "\n", encoding="utf-8")
            with self.subTest(script=name):
                self.assert_rejected("non-latin-script-content")
        path.write_text(original + "A mathematical arrow: " + chr(0x2192) + "\n", encoding="utf-8")
        self.assertEqual(validate_package(self.root)["status"], "passed")

    def test_home_relative_paths_are_visible_nonblocking_review_hints(self):
        result = validate_package(self.root)
        self.assertEqual(result["status"], "passed", result["issues"])
        self.assertTrue(any("home-relative-path" in hint for hint in result["review_hints"]))

    def test_archive_only_cli_does_not_claim_current_source_comparison(self):
        target = self.base / "review.zip"
        build_bundle(self.root, target)
        (self.root / "unlisted-change.txt").write_text("source changed\n", encoding="utf-8")
        command = [sys.executable, "-B", "-m", "scripts.package_review", "--verify", str(target), "--archive-only"]
        result = subprocess.run(command, cwd=self.root, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = load_json(result.stdout)
        self.assertFalse(report["source_compared"])
        default = subprocess.run(command[:-1], cwd=self.root, capture_output=True, text=True, timeout=30)
        self.assertNotEqual(default.returncode, 0)

    def test_archive_only_is_not_a_build_option(self):
        command = [sys.executable, "-B", "-m", "scripts.package_review", "--output", str(self.base / "invalid.zip"), "--archive-only"]
        result = subprocess.run(command, cwd=self.root, capture_output=True, text=True, timeout=30)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.base / "invalid.zip").exists())

    def test_portable_documentation_names_observed_hosts_and_generic_paths(self):
        platforms = (self.root / "skills/sureforge/references/platforms.md").read_text(encoding="utf-8")
        self.assertNotIn("This authoring environment", platforms)
        self.assertNotIn("Devin behavior here", platforms)
        self.assertRegex(platforms, r"Devin CLI [0-9]+\.[0-9]+\.[0-9]+")
        self.assertRegex(platforms, r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
        self.assertIn(".cognition/skills/", platforms)
        for relative in ("README.md", "evals/README.md"):
            self.assertNotIn("../SureForge-local/", (self.root / relative).read_text(encoding="utf-8"))
        contract = (self.root / "review/CONTRACT.md").read_text(encoding="utf-8")
        criterion = next(line for line in contract.splitlines() if line.startswith("| SF-16 |"))
        self.assertIn("when it is the reviewed material or a necessary reference", criterion)

    def test_approximate_numbers_are_not_identifying_home_paths(self):
        path = self.root / "README.md"
        original = path.read_text(encoding="utf-8")
        for suffix in ("3/4 of cases", "1.0/day", "0.25/second"):
            text = "Approximate value: " + "~" + suffix
            with self.subTest(suffix=suffix):
                self.assertEqual(privacy_findings(text), [])
                path.write_text(original + text + "\n", encoding="utf-8")
                checked = validate_package(self.root)
                self.assertEqual(checked["status"], "passed", checked["issues"])

    def test_named_home_paths_require_a_standalone_tilde(self):
        for name in ("alice", "_service", "Alice.smith-1"):
            path = "~" + name + "/notes"
            with self.subTest(name=name):
                self.assertIn("identifying-home-path", privacy_findings(path))
                self.assertIn("identifying-home-path", privacy_findings("(" + path + ")"))
                self.assertEqual(privacy_findings("identifier" + path), [])
                self.assertEqual(privacy_findings("~" + path), [])
        self.assertEqual(privacy_findings("~" + "/.config/devin/skills/"), [])

    def test_frontmatter_subset_is_explicit_and_folded_yaml_is_not_misparsed(self):
        from scripts.check_package import parse_frontmatter

        guide = (self.root / "CONTRIBUTING.md").read_text(encoding="utf-8")
        self.assertIn("JSON-compatible double-quoted strings", guide)
        self.assertIn("Folded/literal blocks, lists", guide)
        with self.assertRaisesRegex(ValueError, "unsupported repository frontmatter syntax"):
            parse_frontmatter("---\nname: sureforge\ndescription: >\n  Folded text.\n---\nBody\n")


if __name__ == "__main__":
    unittest.main()
