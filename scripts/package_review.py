import argparse
import hashlib
import json
import re
import stat
import zipfile
from pathlib import Path

from scripts.check_package import ROOT, collect_files, load_json, manifest_from_bytes, safe_relative, source_manifest, validate_package, write_report


PREFIX = "SureForge/"
MANIFEST = "MANIFEST.json"
ARCHIVE_DATE = (2020, 1, 1, 0, 0, 0)


def _member(name):
    entry = zipfile.ZipInfo(name, date_time=ARCHIVE_DATE)
    entry.create_system = 3
    entry.external_attr = (stat.S_IFREG | 0o644) << 16
    entry.compress_type = zipfile.ZIP_DEFLATED
    entry.extra = b""
    entry.comment = b""
    return entry


def verify_archive(archive_path, source_root=None):
    with zipfile.ZipFile(archive_path) as archive:
        entries = archive.infolist()
        names = [entry.filename for entry in entries]
        if len(entries) > 500 or len(names) != len(set(names)) or MANIFEST not in names:
            raise ValueError("invalid archive inventory")
        if sum(entry.file_size for entry in entries) > 10_000_000:
            raise ValueError("archive exceeds review size limit")
        for entry in entries:
            if entry.filename != MANIFEST and (not entry.filename.startswith(PREFIX) or not safe_relative(entry.filename.removeprefix(PREFIX))):
                raise ValueError("unsafe archive path")
            mode = entry.external_attr >> 16
            if entry.is_dir() or stat.S_ISLNK(mode) or entry.file_size > 1_000_000:
                raise ValueError("unsafe archive member")
            if entry.date_time != ARCHIVE_DATE or entry.extra or entry.comment or entry.create_system != 3 or mode != (stat.S_IFREG | 0o644):
                raise ValueError("non-normalized archive metadata")
        if archive.comment:
            raise ValueError("unexpected archive comment")
        manifest = load_json(archive.read(MANIFEST).decode("utf-8"))
        if not isinstance(manifest, dict) or manifest.get("schema_version") != 1 or not isinstance(manifest.get("files"), dict):
            raise ValueError("invalid manifest structure")
        hashes = manifest["files"]
        if any(not safe_relative(name) or not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value) for name, value in hashes.items()):
            raise ValueError("invalid manifest members")
        if set(names) != {PREFIX + name for name in hashes} | {MANIFEST}:
            raise ValueError("archive and manifest inventory differ")
        payload = {name: archive.read(PREFIX + name) for name in hashes}
        version = payload.get("VERSION", b"").decode("utf-8").strip()
        actual = manifest_from_bytes(payload, version)
        if actual != manifest:
            raise ValueError("archive content or manifest hash mismatch")
    if source_root is not None:
        checked = validate_package(Path(source_root))
        if checked["status"] != "passed" or source_manifest(Path(source_root)) != manifest:
            raise ValueError("archive does not match a valid current source snapshot")
    return {
        "status": "passed", "source_sha256": manifest["source_sha256"],
        "files": len(manifest["files"]), "version": manifest["version"],
        "source_compared": source_root is not None,
        "archive_sha256": hashlib.sha256(Path(archive_path).read_bytes()).hexdigest(),
        "metadata": "normalized timestamps, regular-file permissions, no comments or extra fields",
        "limits": "Snapshot integrity, not a signature, independent review, behavioral evaluation, or publication approval.",
    }


def build_bundle(root, output):
    root, output = Path(root), Path(output)
    if output.resolve().is_relative_to(root.resolve()):
        raise ValueError("archive must be outside the blind source package")
    if not output.parent.is_dir():
        raise ValueError("archive parent directory must already exist")
    report = validate_package(root)
    if report["status"] != "passed":
        raise ValueError("source package failed validation")
    files, issues, _ = collect_files(root)
    manifest = manifest_from_bytes(files, files["VERSION"].decode("utf-8").strip())
    if issues or manifest["source_sha256"] != report["source_sha256"]:
        raise ValueError("source changed during validation")
    manifest_bytes = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")
    handle = output.open("xb")
    try:
        with handle, zipfile.ZipFile(handle, "w") as archive:
            for name, content in sorted(files.items()):
                archive.writestr(_member(PREFIX + name), content)
            archive.writestr(_member(MANIFEST), manifest_bytes)
        return verify_archive(output, root)
    except Exception:
        output.unlink(missing_ok=True)
        raise


def main():
    parser = argparse.ArgumentParser(description="Build or verify an unpublished neutral SureForge review archive.")
    context = parser.add_mutually_exclusive_group()
    context.add_argument("--root", type=Path, default=ROOT)
    context.add_argument("--archive-only", action="store_true", help="Verify archive integrity without claiming comparison with a current source directory.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--output", type=Path)
    mode.add_argument("--verify", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    if args.archive_only and not args.verify:
        parser.error("--archive-only requires --verify")
    try:
        report = build_bundle(args.root, args.output) if args.output else verify_archive(args.verify, None if args.archive_only else args.root)
        if args.report:
            write_report(args.report, report, args.root)
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        parser.exit(1, f"Review archive failed: {error}\n")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
