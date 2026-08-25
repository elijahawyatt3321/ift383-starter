"""IFT383 submission schema v1 and cryptographic receipt helpers.

Canonical JSON is UTF-8 encoded ``json.dumps`` output with ``sort_keys=True``,
``separators=(",", ":")``, ``ensure_ascii=False``, and ``allow_nan=False``.
There is no trailing newline in data being hashed. ``submission_sha256`` hashes
the canonical submission object. ``receipt_sha256`` hashes only the canonical
``payload`` object in ``execution_receipt.json``.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import secrets
import stat
from pathlib import Path
from typing import Any

from .common import CourseError, run_git


DEVICE_PREFIX = b"IFT383-device-v1\0"


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def device_key_path() -> Path:
    data_home = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share"))
    return data_home / "ift383" / "device_key"


def ensure_device_secret() -> Path:
    path = device_key_path()
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    cloexec = getattr(os, "O_CLOEXEC", 0)
    try:
        descriptor = os.open(
            path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | nofollow | cloexec,
            0o600,
        )
    except FileExistsError:
        descriptor = None
    except OSError as exc:
        raise CourseError(f"Cannot create the local installation key safely: {path}") from exc
    if descriptor is not None:
        with os.fdopen(descriptor, "wb") as handle:
            os.fchmod(handle.fileno(), 0o600)
            handle.write(secrets.token_bytes(32))
            handle.flush()
            os.fsync(handle.fileno())
    _read_device_secret(path)
    return path


def installation_fingerprint() -> str:
    secret = _read_device_secret(ensure_device_secret())
    return hashlib.sha256(DEVICE_PREFIX + secret).hexdigest()[:24]


def _read_device_secret(path: Path) -> bytes:
    try:
        before = os.lstat(path)
    except OSError as exc:
        raise CourseError(f"Cannot inspect the local installation key: {path}") from exc
    if not stat.S_ISREG(before.st_mode):
        raise CourseError(f"Local installation key must be a regular file, not a link: {path}")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise CourseError(f"Cannot read the local installation key safely: {path}") from exc
    try:
        after = os.fstat(descriptor)
        if not stat.S_ISREG(after.st_mode) or (before.st_dev, before.st_ino) != (
            after.st_dev,
            after.st_ino,
        ):
            raise CourseError(f"Local installation key changed while it was being opened: {path}")
        os.fchmod(descriptor, 0o600)
        chunks = []
        remaining = 33
        while remaining:
            chunk = os.read(descriptor, remaining)
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        secret = b"".join(chunks)
    finally:
        os.close(descriptor)
    if len(secret) != 32:
        raise CourseError(f"Local installation key has an invalid length: {path}")
    return secret


def environment_metadata(root: Path) -> dict[str, str]:
    return {
        "os": platform.system(),
        "os_version": _os_version(),
        "python_version": platform.python_version(),
        "git_version": run_git(root, "--version"),
    }


def build_execution_receipt(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "payload": payload,
        "receipt_sha256": sha256_bytes(canonical_json(payload)),
    }


def verify_execution_receipt(receipt: dict[str, Any]) -> None:
    if receipt.get("schema_version") != 1 or not isinstance(receipt.get("payload"), dict):
        raise CourseError("Execution receipt does not match schema version 1.")
    expected = sha256_bytes(canonical_json(receipt["payload"]))
    if receipt.get("receipt_sha256") != expected:
        raise CourseError("Execution receipt digest does not match its canonical payload.")


def fresh_nonce() -> str:
    return secrets.token_hex(32)


def _os_version() -> str:
    try:
        values = {}
        for line in Path("/etc/os-release").read_text(encoding="utf-8").splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                values[key] = value.strip().strip('"')
        return values.get("VERSION_ID") or platform.release()
    except OSError:
        return platform.release()
