import argparse
import json
from pathlib import Path

from scripts.check_package import IGNORED_METADATA_FILES, ROOT, collect_files, manifest_from_bytes, write_report


def compare_install(source, installed):
    source_files, source_issues, source_excluded = collect_files(Path(source))
    installed_files, installed_issues, installed_excluded = collect_files(Path(installed))
    issues = source_issues + installed_issues
    if any(Path(name).name not in IGNORED_METADATA_FILES for name in source_excluded + installed_excluded):
        issues.append("unexpected-excluded-directory-in-skill")
    if not source_files or "SKILL.md" not in source_files:
        issues.append("missing-source-skill")
    missing = sorted(set(source_files) - set(installed_files))
    extra = sorted(set(installed_files) - set(source_files))
    changed = sorted(name for name in source_files.keys() & installed_files.keys() if source_files[name] != installed_files[name])
    return {
        "status": "failed" if issues or missing or extra or changed else "passed",
        "files_compared": len(source_files),
        "skill_sha256": manifest_from_bytes(source_files, "skill-only")["source_sha256"],
        "missing": missing,
        "extra": extra,
        "changed": changed,
        "issues": sorted(set(issues)),
        "ignored_metadata_files": {
            "source": [name for name in source_excluded if Path(name).name in IGNORED_METADATA_FILES],
            "installed": [name for name in installed_excluded if Path(name).name in IGNORED_METADATA_FILES],
        },
        "limits": "Byte-for-byte distributable-file check excluding reported OS metadata; not host discovery, activation, or behavioral compatibility.",
    }


def main():
    parser = argparse.ArgumentParser(description="Compare an isolated skill installation with the complete source.")
    parser.add_argument("--source", type=Path, default=ROOT / "skills/sureforge")
    parser.add_argument("--installed", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    try:
        report = compare_install(args.source, args.installed)
        if args.report:
            write_report(args.report, report)
    except (OSError, ValueError) as error:
        parser.exit(1, f"Installation check failed: {error}\n")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
