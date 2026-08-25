#!/usr/bin/env python3
"""Create and self-validate one Canvas-ready IFT 383 submission ZIP."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import zipfile
from contextlib import contextmanager
from pathlib import Path, PurePosixPath
from typing import Any

from ift383lib import PACKAGER_VERSION, SCHEMA_VERSION
from ift383lib.common import (
    ASSIGNMENT_PATHS,
    COURSE,
    CourseError,
    course_root,
    existing_evidence,
    git_state,
    load_identity,
    require_assignment,
    run_git,
    run_visible_checks,
    utc_now,
    valid_mp4_bytes,
    valid_png_bytes,
)
from ift383lib.receipt import (
    build_execution_receipt,
    canonical_json,
    environment_metadata,
    fresh_nonce,
    installation_fingerprint,
    sha256_bytes,
    sha256_file,
    verify_execution_receipt,
)


ARCHIVE_ROOT = "IFT383_SUBMISSION"
SUBMISSION_ARCHIVE_LIMIT = 125 * 1024 * 1024
SUBMISSION_EXPANDED_LIMIT = 300 * 1024 * 1024
SUBMISSION_FILE_COUNT_LIMIT = 2500
SINGLE_ARCHIVE_FILE_LIMIT = 100 * 1024 * 1024
COMPRESSION_RATIO_LIMIT = 200
BUNDLE_LIMIT = 100 * 1024 * 1024
REPOSITORY_EXPANDED_LIMIT = 350 * 1024 * 1024
REPOSITORY_FILE_COUNT_LIMIT = 5000
REPOSITORY_SINGLE_FILE_LIMIT = 40 * 1024 * 1024
JSON_LIMIT = 1024 * 1024


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a validated Canvas submission ZIP.")
    parser.add_argument("assignment", choices=tuple(ASSIGNMENT_PATHS))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    assignment = require_assignment(args.assignment)
    root = course_root()
    identity = load_identity(root)
    state = git_state(root)
    output_dir = root / ".ift383-submissions"
    if output_dir.exists() and (output_dir.is_symlink() or not output_dir.is_dir()):
        raise CourseError(".ift383-submissions must be an ordinary directory inside the repository.")
    output_dir.mkdir(mode=0o700, exist_ok=True)
    safe_login = re.sub(r"[^A-Za-z0-9._-]+", "-", identity["canvas_login"]).strip("-") or "student"
    final_path = output_dir / f"IFT383_{assignment}_{safe_login}_{state['head_sha'][:12]}.zip"

    with tempfile.TemporaryDirectory(prefix="ift383-frozen-submission-") as temporary_name:
        temporary = Path(temporary_name)
        bundle = temporary / "repository.bundle"
        _inspect_committed_tree(root, state["head_sha"])
        run_git(root, "bundle", "create", str(bundle), "HEAD")
        if bundle.stat().st_size > BUNDLE_LIMIT:
            raise CourseError("The committed repository bundle exceeds the 100 MiB submission limit.")
        run_git(root, "bundle", "verify", str(bundle))
        _verify_frozen_bundle(root, bundle, state["head_sha"])
        frozen_digest = sha256_file(bundle)

        with _committed_validation_clone(bundle, state["head_sha"]) as validation_root:
            results = run_visible_checks(root, assignment, validator_root=validation_root)
        if sha256_file(bundle) != frozen_digest:
            raise CourseError("The frozen committed-state bundle changed during validation.")
        state_after_validation = git_state(root)
        if state_after_validation != state:
            raise CourseError("The live repository changed during validation. Run the submission again.")
        failed = [result for result in results if not result.passed]
        if failed:
            detail = "\n".join(f"  {item.result_id}: {item.message}" for item in failed)
            raise CourseError(
                "Visible checks failed. Run python3 tools/check.py " + assignment + " and fix:\n" + detail
            )

        evidence_sources = list(existing_evidence(root, assignment))
        evidence = [
            {"path": target, "size_bytes": source.stat().st_size, "sha256": sha256_file(source)}
            for target, source in evidence_sources
        ]
        evidence.sort(key=lambda item: item["path"])
        created = utc_now()
        submission = {
            "schema_version": SCHEMA_VERSION,
            "course": COURSE,
            "assignment": assignment,
            "canvas_login": identity["canvas_login"],
            "student_display_name": identity["student_display_name"],
            "head_sha": state["head_sha"],
            "tree_sha": state["tree_sha"],
            "bundle_sha256": sha256_file(bundle),
            "packager_version": PACKAGER_VERSION,
            "created_at_utc": created,
            "evidence": evidence,
        }
        artifact_hashes = [
            {
                "path": "repository.bundle",
                "size_bytes": bundle.stat().st_size,
                "sha256": submission["bundle_sha256"],
            },
            *evidence,
        ]
        artifact_hashes.sort(key=lambda item: item["path"])
        payload = {
            "submission_sha256": sha256_bytes(canonical_json(submission)),
            "checker_results": [
                {"id": result.result_id, "status": "pass"} for result in results
            ],
            "artifact_hashes": artifact_hashes,
            "assignment": assignment,
            "head_sha": state["head_sha"],
            "tree_sha": state["tree_sha"],
            "nonce": fresh_nonce(),
            "installation_fingerprint": installation_fingerprint(),
            "environment": environment_metadata(root),
            "created_at_utc": created,
        }
        receipt = build_execution_receipt(payload)
        temporary_zip = temporary / "submission.zip"
        _write_zip(temporary_zip, submission, receipt, bundle, evidence_sources)
        _validate_zip(temporary_zip, root)
        staging = output_dir / f".{final_path.name}.building-{os.getpid()}"
        if staging.exists() or staging.is_symlink():
            raise CourseError(f"Remove the unexpected staging path: {staging}")
        try:
            shutil.copy2(temporary_zip, staging)
            os.replace(staging, final_path)
        finally:
            if staging.exists() and not staging.is_symlink():
                staging.unlink()

    print("Submission created and validated successfully.")
    print(f"Upload this exact file to Canvas: {final_path}")
    print(
        "Only the most recent Canvas submission received by the deadline is used to calculate "
        "the grade. Earlier attempts are not combined or used to improve the grade. However, "
        "any submission attempt may be reviewed and reported when there is a suspected academic "
        "integrity violation."
    )
    print("The receipt provides continuity and tamper evidence; it is not proof of authorship.")
    if any("MANUAL REVIEW" in result.message for result in results):
        print("WARNING: An Actions outage marker was used. This submission requires manual review.")
    return 0


def _verify_frozen_bundle(root: Path, bundle: Path, expected_head: str) -> None:
    heads = run_git(root, "bundle", "list-heads", str(bundle)).splitlines()
    advertised = [line.split() for line in heads if line.split()]
    if advertised != [[expected_head, "HEAD"]]:
        raise CourseError("The frozen bundle must advertise only the captured HEAD commit.")


@contextmanager
def _committed_validation_clone(bundle: Path, expected_head: str):
    """Yield a clone of the frozen bundle, never a clone of the live repository."""

    with tempfile.TemporaryDirectory(prefix="ift383-committed-check-") as directory:
        clone = Path(directory) / "repository"
        try:
            subprocess.run(
                [
                    "git",
                    "clone",
                    "--quiet",
                    "--no-local",
                    "--no-tags",
                    "--single-branch",
                    "--no-checkout",
                    "--",
                    str(bundle),
                    str(clone),
                ],
                check=True,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except subprocess.CalledProcessError as exc:
            detail = (exc.stderr or exc.stdout or "clone failed").strip()
            raise CourseError(f"Could not create the isolated committed-state check: {detail}") from exc
        run_git(clone, "remote", "remove", "origin")
        run_git(clone, "checkout", "--quiet", "-B", "main", expected_head)
        cloned_head = run_git(clone, "rev-parse", "HEAD")
        if cloned_head != expected_head:
            raise CourseError("The isolated validation clone does not match the committed HEAD.")
        refs = run_git(clone, "for-each-ref", "--format=%(objectname) %(refname)").splitlines()
        if refs != [f"{expected_head} refs/heads/main"]:
            raise CourseError("The isolated validation clone contains unexpected Git references.")
        if run_git(clone, "remote"):
            raise CourseError("The isolated validation clone unexpectedly retained a remote.")
        alternates = Path(run_git(clone, "rev-parse", "--git-path", "objects/info/alternates"))
        if not alternates.is_absolute():
            alternates = clone / alternates
        if alternates.exists():
            raise CourseError("The isolated validation clone unexpectedly shares Git objects.")
        git_directory = Path(run_git(clone, "rev-parse", "--absolute-git-dir"))
        _inspect_repository_storage(git_directory)
        yield clone


def _inspect_committed_tree(root: Path, expected_head: str) -> None:
    try:
        completed = subprocess.run(
            ["git", "ls-tree", "-r", "-z", "-l", "--full-tree", expected_head],
            cwd=root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        detail = getattr(exc, "stderr", b"") or b"Could not inspect the committed tree."
        raise CourseError(detail.decode("utf-8", "replace").strip()) from exc
    count = 0
    total = 0
    seen: set[str] = set()
    for record in completed.stdout.split(b"\0"):
        if not record:
            continue
        try:
            metadata, raw_path = record.split(b"\t", 1)
            mode, object_type, _object_id, raw_size = metadata.split()
            path_text = raw_path.decode("utf-8")
            size = int(raw_size)
        except (UnicodeDecodeError, ValueError) as exc:
            raise CourseError("The committed repository tree contains an unsupported entry.") from exc
        relative = PurePosixPath(path_text)
        if relative.is_absolute() or not relative.parts or ".." in relative.parts:
            raise CourseError(f"The committed repository contains an unsafe path: {path_text!r}")
        normalized = relative.as_posix()
        if normalized in seen:
            raise CourseError(f"The committed repository repeats a path: {normalized!r}")
        seen.add(normalized)
        if object_type != b"blob" or mode not in {b"100644", b"100755"}:
            raise CourseError(
                "Only ordinary tracked files are accepted; remove links, submodules, or special "
                f"entries from: {normalized}"
            )
        count += 1
        if count > REPOSITORY_FILE_COUNT_LIMIT:
            raise CourseError("The committed repository contains more than 5,000 files.")
        if size > REPOSITORY_SINGLE_FILE_LIMIT:
            raise CourseError(f"A committed file exceeds the 40 MiB limit: {normalized}")
        total += size
        if total > REPOSITORY_EXPANDED_LIMIT:
            raise CourseError("The committed repository exceeds the 350 MiB expanded-size limit.")


def _inspect_repository_storage(root: Path) -> None:
    total = 0
    for current, directories, files in os.walk(root, followlinks=False):
        current_path = Path(current)
        for directory in directories:
            child = current_path / directory
            if child.is_symlink():
                raise CourseError("The reconstructed Git repository contains an unexpected link.")
        for filename in files:
            child = current_path / filename
            try:
                mode = os.lstat(child).st_mode
            except OSError as exc:
                raise CourseError("Could not inspect the reconstructed Git repository.") from exc
            if not stat.S_ISREG(mode):
                raise CourseError("The reconstructed Git repository contains a non-regular file.")
            total += child.stat().st_size
            if total > REPOSITORY_EXPANDED_LIMIT:
                raise CourseError("The reconstructed Git repository exceeds the 350 MiB size limit.")


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def _write_zip(
    path: Path,
    submission: dict[str, Any],
    receipt: dict[str, Any],
    bundle: Path,
    evidence_sources: list[tuple[str, Path]],
) -> None:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        archive.writestr(f"{ARCHIVE_ROOT}/submission.json", _json_bytes(submission))
        archive.write(bundle, f"{ARCHIVE_ROOT}/repository.bundle")
        archive.writestr(f"{ARCHIVE_ROOT}/execution_receipt.json", _json_bytes(receipt))
        for target, source in evidence_sources:
            archive.write(source, f"{ARCHIVE_ROOT}/{target}")


def _validate_zip(path: Path, root: Path) -> None:
    if path.stat().st_size > SUBMISSION_ARCHIVE_LIMIT:
        raise CourseError("Self-validation found a submission ZIP larger than 125 MiB.")
    required = {
        f"{ARCHIVE_ROOT}/submission.json",
        f"{ARCHIVE_ROOT}/repository.bundle",
        f"{ARCHIVE_ROOT}/execution_receipt.json",
    }
    with zipfile.ZipFile(path, "r") as archive:
        names: list[str] = []
        seen: set[str] = set()
        expanded = 0
        for info in archive.infolist():
            if info.flag_bits & 0x1:
                raise CourseError("Self-validation found an encrypted ZIP entry.")
            raw = info.filename
            if not raw or raw.endswith("/"):
                raise CourseError("Self-validation found an unexpected directory ZIP entry.")
            parts = PurePosixPath(raw).parts
            if not parts or ".." in parts or raw.startswith("/"):
                raise CourseError(f"Self-validation found an unsafe ZIP path: {raw}")
            normalized = PurePosixPath(raw).as_posix()
            if normalized in seen:
                raise CourseError(f"Self-validation found a duplicate ZIP path: {normalized}")
            seen.add(normalized)
            mode = (info.external_attr >> 16) & 0xFFFF
            if mode and stat.S_ISLNK(mode):
                raise CourseError(f"Self-validation found a ZIP link: {normalized}")
            if info.file_size > SINGLE_ARCHIVE_FILE_LIMIT:
                raise CourseError(f"Self-validation found an oversized ZIP entry: {normalized}")
            expanded += info.file_size
            if expanded > SUBMISSION_EXPANDED_LIMIT:
                raise CourseError("Self-validation found more than 300 MiB of expanded ZIP data.")
            if info.file_size and info.compress_size == 0:
                raise CourseError(f"Self-validation found an invalid compressed entry: {normalized}")
            if info.compress_size and info.file_size / info.compress_size > COMPRESSION_RATIO_LIMIT:
                raise CourseError(f"Self-validation found an excessive compression ratio: {normalized}")
            names.append(normalized)
            if len(names) > SUBMISSION_FILE_COUNT_LIMIT:
                raise CourseError("Self-validation found more than 2,500 ZIP entries.")
        if len(names) != len(set(names)) or not required.issubset(names):
            raise CourseError("Self-validation found missing or duplicate ZIP entries.")
        for name in names:
            parts = PurePosixPath(name).parts
            if not parts or parts[0] != ARCHIVE_ROOT or ".." in parts or name.startswith("/"):
                raise CourseError(f"Self-validation found an unsafe ZIP path: {name}")
            if name not in required and not name.startswith(f"{ARCHIVE_ROOT}/evidence/"):
                raise CourseError(f"Self-validation found an unexpected ZIP entry: {name}")
        submission_info = archive.getinfo(f"{ARCHIVE_ROOT}/submission.json")
        receipt_info = archive.getinfo(f"{ARCHIVE_ROOT}/execution_receipt.json")
        if submission_info.file_size > JSON_LIMIT or receipt_info.file_size > JSON_LIMIT:
            raise CourseError("Self-validation found JSON metadata larger than 1 MiB.")
        submission = json.loads(archive.read(submission_info))
        receipt = json.loads(archive.read(receipt_info))
        verify_execution_receipt(receipt)
        if submission.get("schema_version") != 1 or submission.get("course") != COURSE:
            raise CourseError("Self-validation found invalid submission schema or course metadata.")
        if receipt["payload"].get("submission_sha256") != sha256_bytes(canonical_json(submission)):
            raise CourseError("Self-validation found a submission metadata digest mismatch.")
        for key in ("assignment", "head_sha", "tree_sha", "created_at_utc"):
            if receipt["payload"].get(key) != submission.get(key):
                raise CourseError(f"Self-validation found inconsistent receipt field: {key}")
        bundle_bytes = archive.read(f"{ARCHIVE_ROOT}/repository.bundle")
        if len(bundle_bytes) > BUNDLE_LIMIT:
            raise CourseError("Self-validation found a repository bundle larger than 100 MiB.")
        if sha256_bytes(bundle_bytes) != submission.get("bundle_sha256"):
            raise CourseError("Self-validation found a repository bundle digest mismatch.")
        expected_artifacts = [
            {
                "path": "repository.bundle",
                "size_bytes": len(bundle_bytes),
                "sha256": submission["bundle_sha256"],
            },
            *submission.get("evidence", []),
        ]
        expected_artifacts.sort(key=lambda item: item["path"])
        if receipt["payload"].get("artifact_hashes") != expected_artifacts:
            raise CourseError("Self-validation found inconsistent artifact claims in the receipt.")
        checker_results = receipt["payload"].get("checker_results")
        if not isinstance(checker_results, list) or not checker_results or any(
            item.get("status") != "pass" or not isinstance(item.get("id"), str)
            for item in checker_results
        ):
            raise CourseError("Self-validation found invalid checker result claims.")
        for item in submission.get("evidence", []):
            zip_name = f"{ARCHIVE_ROOT}/{item['path']}"
            data = archive.read(zip_name)
            if len(data) != item["size_bytes"] or sha256_bytes(data) != item["sha256"]:
                raise CourseError(f"Self-validation found an evidence digest mismatch: {item['path']}")
            if not _valid_evidence_bytes(item["path"], data):
                raise CourseError(
                    f"Self-validation found evidence with invalid file contents: {item['path']}"
                )
        with tempfile.TemporaryDirectory(prefix="verify-") as directory:
            extracted = Path(directory) / "repository.bundle"
            extracted.write_bytes(bundle_bytes)
            run_git(root, "bundle", "verify", str(extracted))
            _verify_frozen_bundle(root, extracted, submission["head_sha"])
            bare = Path(directory) / "repository.git"
            try:
                subprocess.run(
                    [
                        "git",
                        "clone",
                        "--bare",
                        "--quiet",
                        "--no-local",
                        "--no-tags",
                        "--",
                        str(extracted),
                        str(bare),
                    ],
                    check=True,
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
            except subprocess.CalledProcessError as exc:
                raise CourseError(f"Self-validation could not reconstruct the bundle: {exc.stderr.strip()}") from exc
            _inspect_repository_storage(bare)
            cloned_head = run_git(bare, "rev-parse", "HEAD")
            cloned_tree = run_git(bare, "rev-parse", "HEAD^{tree}")
            if cloned_head != submission.get("head_sha") or cloned_tree != submission.get("tree_sha"):
                raise CourseError("Self-validation found that bundle HEAD/tree do not match metadata.")
            _inspect_committed_tree(bare, submission["head_sha"])


def _valid_evidence_bytes(path: str, data: bytes) -> bool:
    suffix = PurePosixPath(path).suffix.lower()
    if suffix == ".png":
        return valid_png_bytes(data)
    if suffix == ".mp4":
        return valid_mp4_bytes(data)
    if not path.endswith("-outage.txt") or not 0 < len(data) <= 64 * 1024:
        return False
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return False
    if "\x00" in text or any(
        ord(character) < 32 and character not in "\t\r\n" for character in text
    ):
        return False
    normalized = " ".join(text.casefold().split())
    return all(
        phrase in normalized
        for phrase in ("instructor-confirmed", "outage", "manual review required")
    )


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except CourseError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
