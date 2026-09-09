import argparse
import ast
import hashlib
import json
import os
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
SKILL = "skills/sureforge/SKILL.md"
PUBLIC_VERSION_DOCUMENTS = ("README.md", "CHANGELOG.md", "review/CONTRACT.md")
IGNORED_DIRECTORIES = frozenset({".git", ".venv", ".local", "__pycache__", ".pytest_cache"})
IGNORED_METADATA_FILES = frozenset({".DS_Store"})
REQUIREMENTS = frozenset(f"SF-{number:02d}" for number in range(1, 46))
FAILURES = frozenset(f"F{number:02d}" for number in range(1, 14))
MIN_ACTIVATION_CASES = 20
ACTIVATION_ID = re.compile(r"A(?:0[1-9]|[1-9][0-9]+)")
NUMERIC_VERSION = r"(?:0|[1-9][0-9]*)"
PRERELEASE_ID = rf"(?:{NUMERIC_VERSION}|[0-9]*[A-Za-z-][0-9A-Za-z-]*)"
SEMVER = re.compile(rf"{NUMERIC_VERSION}\.{NUMERIC_VERSION}\.{NUMERIC_VERSION}(?:-{PRERELEASE_ID}(?:\.{PRERELEASE_ID})*)?(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?")
LINK = re.compile(r"(?<!!)\[[^\]\n]+\]\(([^\s)]+)(?:\s+\"[^\"]*\")?\)")


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _constant(value):
    raise ValueError("non-finite JSON constant")


def load_json(text):
    return json.loads(text, object_pairs_hook=_pairs, parse_constant=_constant)


def safe_relative(name):
    if not isinstance(name, str) or not name or "\\" in name or ":" in name or any(ord(character) < 32 or ord(character) == 127 for character in name):
        return False
    return all(part not in {".", "..", ""} for part in name.split("/"))


def collect_files(root):
    files, issues, excluded = {}, [], []
    if root.is_symlink() or not root.is_dir():
        return files, ["root: invalid-directory"], excluded
    for directory, names, filenames in os.walk(root, followlinks=False):
        parent = Path(directory)
        for name in list(names):
            path = parent / name
            relative = path.relative_to(root).as_posix()
            if path.is_symlink():
                issues.append(f"{relative}: symlink")
                names.remove(name)
            elif name in IGNORED_DIRECTORIES:
                excluded.append(relative)
                names.remove(name)
        for name in filenames:
            path = parent / name
            relative = path.relative_to(root).as_posix()
            if path.is_symlink():
                issues.append(f"{relative}: symlink")
            elif not path.is_file():
                issues.append(f"{relative}: not-regular-file")
            elif name in IGNORED_METADATA_FILES:
                excluded.append(relative)
            elif path.stat().st_size > 1_000_000:
                issues.append(f"{relative}: oversized-file")
            else:
                files[relative] = path.read_bytes()
    return files, issues, sorted(excluded)


def privacy_findings(text, private_terms=()):
    patterns = {
        "email": r"[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}",
        "obfuscated-email": r"\b[A-Z0-9._%+\-]+\s*\[at\]\s*[A-Z0-9.\-]+\s*\[dot\]\s*[A-Z]{2,}\b",
        "identifying-home-path": r"/(?:Users|home)/[A-Za-z0-9._\-]+/|[A-Z]:\\Users\\[^\s\\]+|(?<![\w~])~[A-Za-z_][A-Za-z0-9._\-]*/",
        "credential-shaped-value": r"(?:gh[pousr]_|github_pat_|sk-)[A-Za-z0-9_\-]{20,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
        "aws-access-key-shaped-value": r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b",
        "aws-secret-key-shaped-value": r"\bAWS_SECRET_ACCESS_KEY[\"']?\s*[:=]\s*[\"']?[A-Za-z0-9/+=]{40}(?![A-Za-z0-9/+=])",
        "jwt-shaped-value": r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b",
        "phone-shaped-value": r"(?<!\w)\+\d[\d ()\-]{8,}\d(?!\w)",
    }
    found = [name for name, pattern in patterns.items() if re.search(pattern, text, re.IGNORECASE)]
    for term in private_terms:
        if term and re.search(r"(?<![A-Za-z0-9])" + re.escape(term) + r"(?![A-Za-z0-9])", text, re.IGNORECASE):
            found.append("private-identity")
    return sorted(set(found))


def content_review_hints(text):
    return ["home-relative-path"] if re.search(r"(?<!\w)~/", text) else []


def has_non_latin_letters(text):
    return any(not character.isascii() and unicodedata.category(character).startswith("L") and not unicodedata.name(character, "").startswith("LATIN ") for character in text)


YAML_NON_STRING_PLAIN = re.compile(
    r"~|null|true|false|yes|no|on|off|[-+]?(?:0|[1-9][0-9_]*)|[-+]?0x[0-9a-fA-F_]+|[-+]?0o[0-7_]+"
    r"|[-+]?(?:[0-9][0-9_]*)?\.[0-9_]*(?:[eE][-+]?[0-9]+)?|[-+]?[0-9][0-9_]*[eE][-+]?[0-9]+|[-+]?\.(?:inf|nan)",
    re.IGNORECASE,
)
YAML_INDICATORS = frozenset("[]{}|>'&*!%@`,?")


def _frontmatter_string(value):
    if value.startswith('"'):
        parsed = json.loads(value)
        if not isinstance(parsed, str):
            raise ValueError("unsupported repository frontmatter syntax")
        return parsed
    if value[0] in YAML_INDICATORS or value.endswith(":") or ": " in value or " #" in value or YAML_NON_STRING_PLAIN.fullmatch(value):
        raise ValueError("unsupported repository frontmatter syntax")
    return value


def parse_frontmatter(text):
    lines = text.splitlines()
    if not lines or lines[0] != "---" or "---" not in lines[1:]:
        raise ValueError("frontmatter delimiters")
    end = lines.index("---", 1)
    data, section = {}, None
    for line in lines[1:end]:
        if not line.strip():
            continue
        nested = line.startswith("  ")
        key, separator, raw = line.strip().partition(":")
        if not separator or not key or (nested and section != "metadata"):
            raise ValueError("unsupported repository frontmatter syntax")
        target = data.setdefault("metadata", {}) if nested else data
        if key in target:
            raise ValueError("duplicate frontmatter key")
        value = raw.strip()
        if not nested and key == "metadata" and not value:
            data[key] = {}
            section = key
            continue
        if not value:
            raise ValueError("empty frontmatter value")
        target[key] = _frontmatter_string(value)
        if not nested:
            section = key
    return data


def heading_ids(text):
    counts, ids = {}, set()
    fenced = False
    for line in text.splitlines():
        if line.startswith("```"):
            fenced = not fenced
        if fenced or not re.match(r"^#{1,6}\s", line):
            continue
        heading = re.sub(r"^#{1,6}\s+|\s+#+$", "", line).strip().lower()
        slug = re.sub(r"[^\w\- ]", "", heading).replace(" ", "-")
        number = counts.get(slug, 0)
        ids.add(slug if number == 0 else f"{slug}-{number}")
        counts[slug] = number + 1
    return ids


def _link_issues(relative, text, texts, root):
    issues = []
    for raw in LINK.findall(text):
        try:
            parsed = urlsplit(raw)
            decoded_path = unquote(parsed.path)
            if any(ord(character) < 32 or ord(character) == 127 for character in decoded_path):
                raise ValueError("invalid path character")
            if parsed.scheme in {"http", "https"} and parsed.netloc:
                continue
            if parsed.scheme or parsed.netloc:
                issues.append(f"{relative}: unsupported-link")
                continue
            destination = ((root / relative).parent / decoded_path if parsed.path else root / relative).resolve()
        except ValueError:
            issues.append(f"{relative}: invalid-link")
            continue
        if not destination.is_relative_to(root.resolve()):
            issues.append(f"{relative}: escaping-link")
            continue
        target = destination.relative_to(root.resolve()).as_posix()
        if target not in texts:
            issues.append(f"{relative}: broken-link:{target}")
        elif parsed.fragment and unquote(parsed.fragment) not in heading_ids(texts[target]):
            issues.append(f"{relative}: broken-anchor:{target}")
    return issues


def manifest_from_bytes(files, version):
    hashes = {name: hashlib.sha256(content).hexdigest() for name, content in sorted(files.items())}
    payload = json.dumps(hashes, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {"schema_version": 1, "version": version, "source_sha256": hashlib.sha256(payload).hexdigest(), "files": hashes}


def source_manifest(root):
    files, issues, _ = collect_files(Path(root))
    if issues:
        raise ValueError("unsafe source inventory")
    inventory = load_json(files["review/inventory.json"].decode("utf-8"))["files"]
    if any(not safe_relative(name) for name in inventory) or set(inventory) != set(files):
        raise ValueError("source inventory mismatch")
    return manifest_from_bytes(files, files["VERSION"].decode("utf-8").strip())


def _evaluation_issues(data, texts):
    issues = []
    mappings = data["review/requirements.json"]["requirements"]
    mapping_ids = [row["id"] for row in mappings]
    contract_ids = set(re.findall(r"^\| (SF-\d{2}) \|", texts["review/CONTRACT.md"], re.MULTILINE))
    if set(mapping_ids) != REQUIREMENTS or len(mapping_ids) != len(REQUIREMENTS) or contract_ids != REQUIREMENTS:
        issues.append("review/requirements.json: requirement-map")
    cases = data["evals/cases.json"]["cases"]
    case_ids = [row["id"] for row in cases]
    if set(case_ids) != FAILURES or len(case_ids) != len(FAILURES):
        issues.append("evals/cases.json: failure-scenarios")
    for case in cases:
        if len(case["assertions"]) < 3 or not case["fail_if"] or not case["positive_control"] or not set(case["requirements"]) <= REQUIREMENTS:
            issues.append(f"evals/cases.json: invalid-scenario:{case['id']}")
    for row in mappings:
        if not row["files"] or any(name not in texts for name in row["files"]) or not set(row["scenarios"]) <= FAILURES:
            issues.append(f"review/requirements.json: invalid-reference:{row['id']}")
    mapped_pairs = {(row["id"], case) for row in mappings for case in row["scenarios"]}
    case_pairs = {(requirement, case["id"]) for case in cases for requirement in case["requirements"]}
    if mapped_pairs != case_pairs:
        issues.append("review/requirements.json: scenario-map-not-bidirectional")
    activation = data["evals/activation.json"]["cases"]
    activation_ids = [row["id"] for row in activation]
    if len(activation_ids) < MIN_ACTIVATION_CASES or any(not isinstance(identifier, str) or not ACTIVATION_ID.fullmatch(identifier) for identifier in activation_ids) or len(set(activation_ids)) != len(activation_ids):
        issues.append("evals/activation.json: activation-cases")
    for row in activation:
        if type(row["activate"]) is not bool or (row["activate"] and row["tier"] not in {"light", "standard", "full"}) or (not row["activate"] and row["tier"] is not None):
            issues.append("evals/activation.json: invalid-activation-label")
    tasks = data["evals/tasks.json"]["tasks"]
    task_ids = [row["id"] for row in tasks]
    study = data["evals/study.json"]
    if set(task_ids) != {"T01", "T02", "T03", "T04", "T05"} or len(task_ids) != 5 or study["task_ids"] != task_ids:
        issues.append("evals/tasks.json: task-inventory")
    for row in tasks:
        if not row["prompt"] or not row["grading_oracles"] or any(name not in texts for name in row["files"]):
            issues.append(f"evals/tasks.json: task-input-or-oracle:{row['id']}")
    if study["arms"] != ["no-skill", "current-instructions", "sureforge"] or type(study["repetitions_per_cell"]) is not int or study["repetitions_per_cell"] != 3:
        issues.append("evals/study.json: study-design")
    if study["skill_version"] != texts["VERSION"].strip():
        issues.append("evals/study.json: version-mismatch")
    if study["baseline_status"] == "reconstructed-awaiting-owner-confirmation" and "RECONSTRUCTED BASELINE CANDIDATE" not in texts[study["baseline_file"]]:
        issues.append("evals/arms/current-instructions.txt: baseline-provenance")
    if data["evals/run-record.json"]["record_kind"] != "template-not-a-run":
        issues.append("evals/run-record.json: template-not-observation")
    return issues


def validate_package(root=ROOT, private_terms=()):
    root = Path(root)
    files, issues, excluded = collect_files(root)
    texts, data, hints = {}, {}, []
    username = Path.home().name
    public_identifiers = {"root", "runner", "user", "home", "devin", "sureforge", "da7-tech"}
    identities = tuple(private_terms) + ((username,) if username.casefold() not in public_identifiers else ())
    for relative, raw in files.items():
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            issues.append(f"{relative}: non-text-file")
            continue
        texts[relative] = text
        issues.extend(f"{relative}: {finding}" for finding in privacy_findings(text + "\n" + relative, identities))
        hints.extend(f"{relative}: {hint}" for hint in content_review_hints(text))
        if "\x00" in text or not text.endswith("\n"):
            issues.append(f"{relative}: text-format")
        if has_non_latin_letters(text):
            issues.append(f"{relative}: non-latin-script-content")
        if relative.endswith(".py"):
            try:
                ast.parse(text, filename=relative, feature_version=(3, 11))
            except SyntaxError:
                issues.append(f"{relative}: python-syntax")
        if relative.endswith(".json"):
            try:
                data[relative] = load_json(text)
            except ValueError:
                issues.append(f"{relative}: invalid-json")
    for relative, text in texts.items():
        if relative.endswith(".md"):
            issues.extend(_link_issues(relative, text, texts, root))
    try:
        inventory = data["review/inventory.json"]["files"]
        if not isinstance(inventory, list) or any(not safe_relative(name) for name in inventory) or len(inventory) != len(set(inventory)):
            issues.append("review/inventory.json: invalid-inventory")
        else:
            issues.extend(f"{name}: missing-file" for name in sorted(set(inventory) - set(files)))
            issues.extend(f"{name}: unlisted-file" for name in sorted(set(files) - set(inventory)))
        if texts["LICENSE"] != texts["skills/sureforge/LICENSE"] or not texts["LICENSE"].startswith("MIT License\n") or "Copyright (c) 2026 Da7-Tech" not in texts["LICENSE"]:
            issues.append("LICENSE: license-mismatch")
        try:
            metadata = parse_frontmatter(texts[SKILL])
        except ValueError as error:
            issues.append(f"{SKILL}: frontmatter-syntax:{error}")
            metadata = {}
        if metadata.get("name") != "sureforge" or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", str(metadata.get("name", ""))):
            issues.append(f"{SKILL}: skill-name")
        description = metadata.get("description")
        if not isinstance(description, str) or not 1 <= len(description) <= 1024:
            issues.append(f"{SKILL}: description")
        if set(metadata) != {"name", "description", "license", "metadata"} or metadata.get("license") != "MIT":
            issues.append(f"{SKILL}: nonportable-frontmatter")
        custom = metadata.get("metadata", {})
        version = texts["VERSION"].strip()
        if custom.get("version") != version or not SEMVER.fullmatch(version):
            issues.append(f"{SKILL}: version-mismatch")
        if custom.get("author") != "Da7-Tech" or not all(isinstance(k, str) and isinstance(v, str) for k, v in custom.items()):
            issues.append(f"{SKILL}: metadata")
        for name in PUBLIC_VERSION_DOCUMENTS:
            if not re.search(r"(?<![0-9A-Za-z\-])(?<![0-9A-Za-z]\.)" + re.escape(version) + r"(?![0-9A-Za-z\-])(?!\.[0-9A-Za-z])", texts[name]):
                issues.append(f"{name}: public-version-missing:{version}")
        if len(texts[SKILL].splitlines()) >= 500 or len(texts[SKILL].split()) > 2500:
            issues.append(f"{SKILL}: entry-point-too-long")
        for name in files:
            if name.startswith("skills/sureforge/references/") or name.startswith("skills/sureforge/assets/"):
                relative = name.removeprefix("skills/sureforge/")
                if relative not in LINK.findall(texts[SKILL]):
                    issues.append(f"{SKILL}: resource-not-directly-linked:{relative}")
            if name.startswith("skills/sureforge/") and Path(name).suffix not in {".md", ".csv", ".json", ".txt", ""}:
                issues.append(f"{name}: executable-in-installed-skill")
        issues.extend(_evaluation_issues(data, texts))
    except (KeyError, TypeError, ValueError, AttributeError):
        issues.append("package: missing-or-invalid-required-structure")
    manifest = manifest_from_bytes(files, texts.get("VERSION", "unknown").strip())
    return {
        "status": "failed" if issues else "passed",
        "files_checked": len(files),
        "skill_words": len(texts.get(SKILL, "").split()),
        "skill_lines": len(texts.get(SKILL, "").splitlines()),
        "source_sha256": manifest["source_sha256"],
        "issues": sorted(set(issues)),
        "review_hints": sorted(set(hints)),
        "excluded_directories": [name for name in excluded if Path(name).name not in IGNORED_METADATA_FILES],
        "ignored_metadata_files": [name for name in excluded if Path(name).name in IGNORED_METADATA_FILES],
        "limits": "Mechanical checks, selected privacy patterns, and a non-Latin-script signal only; not complete privacy/language detection, model behavior, or independent review.",
    }


def write_report(path, report, source_root=ROOT):
    path = Path(path)
    if path.resolve().is_relative_to(Path(source_root).resolve()):
        raise ValueError("write reports outside the blind source package")
    if not path.parent.is_dir():
        raise ValueError("report parent directory must already exist")
    payload = dict(report, observed_at=datetime.now(timezone.utc).isoformat())
    with path.open("x", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")


def main():
    parser = argparse.ArgumentParser(description="Validate the SureForge distribution without running agents.")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    try:
        report = validate_package(args.root)
        if args.report:
            write_report(args.report, report, args.root)
    except (OSError, ValueError) as error:
        parser.exit(1, f"Package check failed: {error}\n")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
