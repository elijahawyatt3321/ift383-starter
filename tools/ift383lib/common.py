"""Shared repository, identity, and visible-check operations."""

from __future__ import annotations

import json
import os
import signal
import stat
import struct
import subprocess
import tempfile
import zlib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


COURSE = "IFT383"
ASSIGNMENT_PATHS = {
    "lab1": "labs/lab-01",
    "lab2": "labs/lab-02",
    "lab3": "labs/lab-03",
    "lab4": "labs/lab-04",
    "lab5": "labs/lab-05",
    "lab6": "labs/lab-06",
    "lab7": "labs/lab-07",
    "project": "final-project",
}
RECORD_NAMES = {**{f"lab{i}": "lab_record.yml" for i in range(1, 8)}, "project": "PROJECT_PLAN.yml"}
EVIDENCE_PATHS = {
    "lab2": (".submission-evidence/lab2-pr.png",),
    "lab7": (".submission-evidence/lab7-actions.png",),
    "project": (
        ".submission-evidence/project-actions.png",
        ".submission-evidence/project-walkthrough.mp4",
    ),
}
OUTAGE_MARKERS = {
    "lab7": ".submission-evidence/lab7-actions-outage.txt",
    "project": ".submission-evidence/project-actions-outage.txt",
}
PNG_LIMIT = 5 * 1024 * 1024
MP4_LIMIT = 60 * 1024 * 1024
VALIDATOR_TIMEOUT_SECONDS = 300
VALIDATOR_OUTPUT_LIMIT = 2 * 1024 * 1024
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
MAX_MEDIA_STRUCTURES = 10_000


class CourseError(RuntimeError):
    """An actionable error suitable for a student-facing CLI."""


@dataclass(frozen=True)
class CheckResult:
    result_id: str
    passed: bool
    message: str

    def as_dict(self) -> dict[str, str]:
        return {
            "id": self.result_id,
            "status": "pass" if self.passed else "fail",
            "message": self.message,
        }


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def course_root() -> Path:
    expected = Path(__file__).resolve().parents[2]
    actual = Path(run_git(expected, "rev-parse", "--show-toplevel")).resolve()
    if actual != expected:
        raise CourseError(
            "These tools must be inside the root of the cloned IFT 383 repository. "
            f"Expected {expected}, but Git reported {actual}."
        )
    return expected


def run_git(root: Path, *args: str) -> str:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=root,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except FileNotFoundError as exc:
        raise CourseError("Git is not installed. Run: sudo dnf install git") from exc
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "Git command failed").strip()
        raise CourseError(f"Git error while running {' '.join(args)}: {detail}") from exc
    return completed.stdout.strip()


def git_dir(root: Path) -> Path:
    return Path(run_git(root, "rev-parse", "--absolute-git-dir")).resolve()


def identity_path(root: Path) -> Path:
    return git_dir(root) / "ift383" / "student.json"


def save_identity(root: Path, canvas_login: str, display_name: str) -> Path:
    canvas_login = _clean_identity(canvas_login, "Canvas login")
    display_name = _clean_identity(display_name, "display name")
    path = identity_path(root)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    data = {
        "schema_version": 1,
        "course": COURSE,
        "canvas_login": canvas_login,
        "student_display_name": display_name,
        "configured_at_utc": utc_now(),
    }
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(temporary, 0o600)
    temporary.replace(path)
    os.chmod(path, 0o600)
    return path


def load_identity(root: Path) -> dict[str, Any]:
    path = identity_path(root)
    if not path.is_file():
        raise CourseError("Setup has not been completed. Run: python3 tools/setup.py")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CourseError("Local setup data is unreadable. Run: python3 tools/setup.py") from exc
    for key in ("canvas_login", "student_display_name"):
        if not isinstance(data.get(key), str) or not data[key].strip():
            raise CourseError("Local setup data is incomplete. Run: python3 tools/setup.py")
    return data


def _clean_identity(value: str, label: str) -> str:
    cleaned = value.strip()
    if not cleaned or len(cleaned) > 200 or any(ch in cleaned for ch in "\r\n\0"):
        raise CourseError(f"{label} must be 1-200 characters on one line.")
    return cleaned


def require_assignment(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in ASSIGNMENT_PATHS:
        allowed = ", ".join(ASSIGNMENT_PATHS)
        raise CourseError(f"Unknown assignment '{value}'. Use one of: {allowed}.")
    return normalized


def git_state(root: Path) -> dict[str, str]:
    branch = run_git(root, "symbolic-ref", "--quiet", "--short", "HEAD")
    if branch != "main":
        raise CourseError(f"Submission requires branch 'main'; current branch is '{branch}'.")
    status = run_git(root, "status", "--porcelain=v1", "--untracked-files=all")
    if status:
        preview = "\n".join(status.splitlines()[:12])
        raise CourseError(
            "Commit or remove all nonignored changes before submitting. Git reports:\n" + preview
        )
    return {
        "branch": branch,
        "head_sha": run_git(root, "rev-parse", "HEAD"),
        "tree_sha": run_git(root, "rev-parse", "HEAD^{tree}"),
    }


def run_visible_checks(
    root: Path,
    assignment: str,
    *,
    validator_root: Path | None = None,
    include_validator: bool = True,
) -> list[CheckResult]:
    assignment = require_assignment(assignment)
    base = root / ASSIGNMENT_PATHS[assignment]
    prefix = assignment.upper()
    results = [
        _directory_check(root, base, f"{prefix}.DIRECTORY"),
        _file_check(root, base / "README.md", f"{prefix}.README", reject_markers=False),
        _file_check(
            root,
            base / RECORD_NAMES[assignment],
            f"{prefix}.RECORD",
            reject_markers=True,
        ),
    ]
    if assignment in ("lab5", "lab6", "lab7"):
        results.append(_directory_check(root, root / "inventory-tool", f"{prefix}.INVENTORY_TOOL"))
    if assignment == "lab7":
        results.append(
            _file_check(
                root,
                root / ".github/workflows/inventory-tool.yml",
                "LAB7.ACTIVE_WORKFLOW",
                reject_markers=False,
            )
        )
    if assignment == "project":
        results.extend(
            [
                _directory_check(root, base / "src", "PROJECT.SOURCE_DIRECTORY"),
                _directory_check(root, base / "tests", "PROJECT.TEST_DIRECTORY"),
                _file_check(
                    root,
                    root / ".github/workflows/final-project.yml",
                    "PROJECT.ACTIVE_WORKFLOW",
                    reject_markers=False,
                ),
            ]
        )
    for index, relative in enumerate(EVIDENCE_PATHS.get(assignment, ()), start=1):
        path = root / relative
        is_actions_image = relative.endswith("actions.png")
        marker_relative = OUTAGE_MARKERS.get(assignment) if is_actions_image else None
        marker = root / marker_relative if marker_relative else None
        if marker is not None and not path.exists() and marker.is_file() and not marker.is_symlink():
            results.append(
                CheckResult(
                    f"{prefix}.EVIDENCE_{index}",
                    _valid_outage_marker(marker),
                    f"MANUAL REVIEW: instructor-confirmed Actions outage marker used: {marker_relative}",
                )
            )
        else:
            limit = MP4_LIMIT if relative.endswith(".mp4") else PNG_LIMIT
            results.append(_evidence_check(root, path, f"{prefix}.EVIDENCE_{index}", limit))
    if include_validator:
        execution_root = validator_root if validator_root is not None else root
        validator = execution_root / ASSIGNMENT_PATHS[assignment] / "validate_local.sh"
        results.append(
            _validator_check(
                execution_root,
                validator,
                f"{prefix}.LOCAL_VALIDATOR",
            )
        )
    return results


def existing_evidence(root: Path, assignment: str) -> Iterable[tuple[str, Path]]:
    for relative in EVIDENCE_PATHS.get(assignment, ()):
        source = root / relative
        if source.exists():
            if not _safe_path(root, source) or not source.is_file():
                raise CourseError(f"Evidence must be a regular file, not a link: {relative}")
            limit = MP4_LIMIT if relative.endswith(".mp4") else PNG_LIMIT
            size = source.stat().st_size
            if size == 0 or size > limit:
                limit_mib = limit // (1024 * 1024)
                raise CourseError(f"Evidence must be nonempty and no larger than {limit_mib} MiB: {relative}")
            if not _valid_evidence_signature(source):
                raise CourseError(f"Evidence contents do not match the required file type: {relative}")
            yield f"evidence/{source.name}", source
    marker_relative = OUTAGE_MARKERS.get(assignment)
    if marker_relative:
        marker = root / marker_relative
        actions_image_exists = any(
            (root / relative).exists()
            for relative in EVIDENCE_PATHS.get(assignment, ())
            if relative.endswith("actions.png")
        )
        if marker.is_file() and not actions_image_exists:
            if not _safe_path(root, marker) or not _valid_outage_marker(marker):
                raise CourseError(f"Outage marker is invalid or too large: {marker_relative}")
            yield f"evidence/{marker.name}", marker


def _safe_path(root: Path, path: Path) -> bool:
    root = Path(os.path.abspath(root))
    try:
        relative = Path(os.path.abspath(path)).relative_to(root)
    except (OSError, ValueError):
        return False
    current = root
    for part in relative.parts:
        current /= part
        try:
            mode = os.lstat(current).st_mode
        except FileNotFoundError:
            return True
        except OSError:
            return False
        if stat.S_ISLNK(mode):
            return False
    return True


def _directory_check(root: Path, path: Path, result_id: str) -> CheckResult:
    relative = path.relative_to(root).as_posix()
    passed = _safe_path(root, path) and path.is_dir()
    return CheckResult(result_id, passed, f"Directory {'found' if passed else 'missing'}: {relative}")


def _file_check(root: Path, path: Path, result_id: str, reject_markers: bool) -> CheckResult:
    relative = path.relative_to(root).as_posix()
    if not _safe_path(root, path) or not path.is_file() or path.stat().st_size == 0:
        return CheckResult(result_id, False, f"Required nonempty file missing: {relative}")
    if reject_markers:
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return CheckResult(result_id, False, f"Required text file is not UTF-8: {relative}")
        if "TODO" in text or "INSTRUCTOR_COMPLETION_REQUIRED" in text:
            return CheckResult(result_id, False, f"Complete all marked fields in: {relative}")
    return CheckResult(result_id, True, f"Required file ready: {relative}")


def _evidence_check(root: Path, path: Path, result_id: str, size_limit: int) -> CheckResult:
    relative = path.relative_to(root).as_posix()
    if not _safe_path(root, path) or not path.is_file() or path.stat().st_size == 0:
        return CheckResult(result_id, False, f"Required evidence missing: {relative}")
    if path.stat().st_size > size_limit:
        limit_mib = size_limit // (1024 * 1024)
        return CheckResult(result_id, False, f"Evidence exceeds {limit_mib} MiB: {relative}")
    if not _valid_evidence_signature(path):
        return CheckResult(
            result_id,
            False,
            f"Evidence contents do not match the required file type: {relative}",
        )
    return CheckResult(result_id, True, f"Required evidence ready: {relative}")


def _valid_evidence_signature(path: Path) -> bool:
    try:
        data = path.read_bytes()
    except OSError:
        return False
    suffix = path.suffix.lower()
    if suffix == ".png":
        return valid_png_bytes(data)
    if suffix == ".mp4":
        return valid_mp4_bytes(data)
    return False


def valid_png_bytes(data: bytes) -> bool:
    """Return whether PNG bytes satisfy the course grader's safe structure contract."""

    if not 0 < len(data) <= PNG_LIMIT or not data.startswith(PNG_SIGNATURE):
        return False
    offset = len(PNG_SIGNATURE)
    chunk_index = 0
    saw_idat = False
    saw_iend = False
    while offset < len(data):
        if chunk_index >= MAX_MEDIA_STRUCTURES or len(data) - offset < 12:
            return False
        length = struct.unpack(">I", data[offset : offset + 4])[0]
        chunk_type = data[offset + 4 : offset + 8]
        end = offset + 12 + length
        if end > len(data) or len(chunk_type) != 4 or not chunk_type.isalpha():
            return False
        chunk_data = data[offset + 8 : offset + 8 + length]
        expected_crc = struct.unpack(">I", data[offset + 8 + length : end])[0]
        if zlib.crc32(chunk_type + chunk_data) & 0xFFFFFFFF != expected_crc:
            return False
        if chunk_index == 0:
            if chunk_type != b"IHDR" or length != 13:
                return False
            width, height = struct.unpack(">II", chunk_data[:8])
            if not (
                1 <= width <= 20_000
                and 1 <= height <= 20_000
                and width * height <= 100_000_000
            ):
                return False
        elif chunk_type == b"IHDR":
            return False
        if chunk_type == b"IDAT":
            saw_idat = True
        if chunk_type == b"IEND":
            if length != 0 or end != len(data):
                return False
            saw_iend = True
        offset = end
        chunk_index += 1
    return saw_idat and saw_iend


def valid_mp4_bytes(data: bytes) -> bool:
    """Return whether MP4 bytes satisfy the course grader's safe structure contract."""

    size = len(data)
    if size < 24 or size > MP4_LIMIT:
        return False
    found: set[bytes] = set()
    offset = 0
    box_index = 0
    while offset < size:
        if box_index >= MAX_MEDIA_STRUCTURES or size - offset < 8:
            return False
        box_size = struct.unpack(">I", data[offset : offset + 4])[0]
        box_type = data[offset + 4 : offset + 8]
        header_size = 8
        if box_size == 1:
            if size - offset < 16:
                return False
            box_size = struct.unpack(">Q", data[offset + 8 : offset + 16])[0]
            header_size = 16
        elif box_size == 0:
            box_size = size - offset
        if box_size < header_size or box_size > size - offset:
            return False
        if box_index == 0:
            if box_type != b"ftyp" or box_size < header_size + 8:
                return False
            brand = data[offset + header_size : offset + header_size + 4]
            if len(brand) != 4 or any(byte < 0x20 or byte > 0x7E for byte in brand):
                return False
        found.add(box_type)
        offset += box_size
        box_index += 1
    return (
        offset == size
        and b"ftyp" in found
        and b"moov" in found
        and b"mdat" in found
    )


def _valid_outage_marker(path: Path) -> bool:
    try:
        size = path.stat().st_size
        if not 0 < size <= 64 * 1024:
            return False
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
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


def _validator_check(root: Path, path: Path, result_id: str) -> CheckResult:
    relative = path.relative_to(root).as_posix()
    if not _safe_path(root, path) or not path.is_file() or path.stat().st_size == 0:
        return CheckResult(result_id, False, f"Published local validator missing: {relative}")
    environment = os.environ.copy()
    for name in (
        "GIT_ALTERNATE_OBJECT_DIRECTORIES",
        "GIT_COMMON_DIR",
        "GIT_DIR",
        "GIT_INDEX_FILE",
        "GIT_OBJECT_DIRECTORY",
        "GIT_WORK_TREE",
    ):
        environment.pop(name, None)
    with tempfile.TemporaryFile() as output:
        try:
            process = subprocess.Popen(
                ["bash", str(path)],
                cwd=root,
                env=environment,
                stdin=subprocess.DEVNULL,
                stdout=output,
                stderr=subprocess.STDOUT,
                start_new_session=(os.name == "posix"),
            )
        except FileNotFoundError:
            return CheckResult(result_id, False, "Bash is unavailable on this Fedora VM.")
        try:
            returncode = process.wait(timeout=VALIDATOR_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            _stop_process_group(process)
            return CheckResult(
                result_id,
                False,
                f"Published local validator exceeded {VALIDATOR_TIMEOUT_SECONDS} seconds: {relative}",
            )
        output.seek(0)
        raw_output = output.read(VALIDATOR_OUTPUT_LIMIT + 1)
    if len(raw_output) > VALIDATOR_OUTPUT_LIMIT:
        return CheckResult(
            result_id,
            False,
            f"Published local validator exceeded the {VALIDATOR_OUTPUT_LIMIT}-byte output limit: {relative}",
        )
    text_output = raw_output.decode("utf-8", "replace")
    if returncode == 0:
        return CheckResult(result_id, True, f"Published local validator passed: {relative}")
    lines = [line.strip() for line in text_output.splitlines() if line.strip()]
    detail = lines[-1] if lines else f"exit status {returncode}"
    if len(detail) > 500:
        detail = detail[-500:]
    return CheckResult(
        result_id,
        False,
        f"Published local validator failed ({detail}). Run: bash {relative}",
    )


def _stop_process_group(process: subprocess.Popen[bytes]) -> None:
    if os.name == "posix":
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            return
        try:
            process.wait(timeout=0.2)
        except subprocess.TimeoutExpired:
            pass
        # The shell may exit before one of its children. Kill the session once
        # more so a child that ignored SIGTERM cannot outlive validation.
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        if process.poll() is None:
            process.wait()
        return
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=1)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()
