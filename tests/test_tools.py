"""Unit and end-to-end tests for the local student tools."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import unittest
import zipfile
import zlib
from pathlib import Path
from unittest import mock


STARTER = Path(__file__).resolve().parents[1]
TOOLS = STARTER / "tools"
sys.path.insert(0, str(TOOLS))

import submit as submit_module  # noqa: E402
from ift383lib import common as common_module  # noqa: E402
from ift383lib.common import (  # noqa: E402
    CourseError,
    _evidence_check,
    _validator_check,
    existing_evidence,
    run_visible_checks,
    valid_mp4_bytes,
    valid_png_bytes,
)
from ift383lib.receipt import canonical_json, ensure_device_secret  # noqa: E402


def _png_chunk(chunk_type: bytes, payload: bytes) -> bytes:
    checksum = zlib.crc32(chunk_type + payload) & 0xFFFFFFFF
    return struct.pack(">I", len(payload)) + chunk_type + payload + struct.pack(">I", checksum)


def _valid_png_fixture() -> bytes:
    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0)
    scanline = zlib.compress(b"\x00\x00\x00\x00\x00")
    return (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", ihdr)
        + _png_chunk(b"IDAT", scanline)
        + _png_chunk(b"IEND", b"")
    )


def _mp4_box(box_type: bytes, payload: bytes = b"") -> bytes:
    return struct.pack(">I4s", 8 + len(payload), box_type) + payload


def _valid_mp4_fixture() -> bytes:
    return (
        _mp4_box(b"ftyp", b"isom\x00\x00\x00\x00")
        + _mp4_box(b"moov")
        + _mp4_box(b"mdat")
    )


class ToolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.repo = self.base / "course"
        shutil.copytree(
            STARTER,
            self.repo,
            ignore=shutil.ignore_patterns(".git", ".ift383-submissions", "__pycache__", "*.pyc"),
        )
        self.env = os.environ.copy()
        self.env["XDG_DATA_HOME"] = str(self.base / "xdg-data")
        self._run("git", "init", "-q", "-b", "main")
        self._run("git", "config", "user.name", "IFT Test")
        self._run("git", "config", "user.email", "ift-test@example.invalid")

    def _run(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            args,
            cwd=self.repo,
            env=self.env,
            check=check,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def _prepare_lab1(self, validator: str = "#!/usr/bin/env bash\nexit 0\n") -> None:
        (self.repo / "labs/lab-01/lab_record.yml").write_text(
            "assignment: lab1\ncompletion_record: complete\n", encoding="utf-8"
        )
        (self.repo / "labs/lab-01/validate_local.sh").write_text(validator, encoding="utf-8")
        self._run("git", "add", ".")
        self._run("git", "commit", "-q", "-m", "Complete Lab 1 fixture")

    def test_canonical_json_contract(self) -> None:
        value = {"z": 2, "student": "Áda", "a": [True, None]}
        expected = '{"a":[true,null],"student":"Áda","z":2}'.encode("utf-8")
        self.assertEqual(canonical_json(value), expected)

    def test_no_active_workflow_in_starter(self) -> None:
        self.assertFalse((STARTER / ".github/workflows").exists())
        self.assertTrue((STARTER / "workflow-starters/inventory-tool.yml").is_file())
        self.assertTrue((STARTER / "workflow-starters/final-project.yml").is_file())

    def test_required_evidence_and_outage_fallback(self) -> None:
        lab2 = self.repo / "labs/lab-02"
        (lab2 / "lab_record.yml").write_text("assignment: lab2\ncomplete: yes\n", encoding="utf-8")
        evidence = self.repo / ".submission-evidence"
        evidence.mkdir()
        (evidence / "lab2-pr.png").write_bytes(_valid_png_fixture())
        self.assertTrue(
            all(
                result.passed
                for result in run_visible_checks(self.repo, "lab2", include_validator=False)
            )
        )

        lab7 = self.repo / "labs/lab-07"
        (lab7 / "lab_record.yml").write_text("assignment: lab7\ncomplete: yes\n", encoding="utf-8")
        workflow = self.repo / ".github/workflows/inventory-tool.yml"
        workflow.parent.mkdir(parents=True)
        workflow.write_text("name: local test\n", encoding="utf-8")
        (evidence / "lab7-actions-outage.txt").write_text(
            "Instructor-confirmed outage; manual review required.\n", encoding="utf-8"
        )
        results = run_visible_checks(self.repo, "lab7", include_validator=False)
        self.assertTrue(all(result.passed for result in results))
        self.assertTrue(any("MANUAL REVIEW" in result.message for result in results))

    def test_evidence_structure_must_match_extension(self) -> None:
        evidence = self.repo / ".submission-evidence"
        evidence.mkdir()
        png = evidence / "lab2-pr.png"
        png.write_bytes(b"\x89PNG\r\n\x1a\ntruncated chunk")
        result = _evidence_check(self.repo, png, "TEST.PNG", 1024)
        self.assertFalse(result.passed)
        self.assertIn("file type", result.message)
        with self.assertRaisesRegex(CourseError, "file type"):
            list(existing_evidence(self.repo, "lab2"))

        png.write_bytes(_valid_png_fixture())
        self.assertTrue(_evidence_check(self.repo, png, "TEST.PNG", 1024).passed)
        self.assertTrue(
            submit_module._valid_evidence_bytes("evidence/lab2-pr.png", png.read_bytes())
        )
        mp4 = evidence / "walkthrough.mp4"
        mp4.write_bytes(_valid_mp4_fixture())
        self.assertTrue(_evidence_check(self.repo, mp4, "TEST.MP4", 1024).passed)
        self.assertTrue(
            submit_module._valid_evidence_bytes(
                "evidence/project-walkthrough.mp4", mp4.read_bytes()
            )
        )
        mp4.write_bytes(_mp4_box(b"ftyp", b"isom\x00\x00\x00\x00"))
        self.assertFalse(_evidence_check(self.repo, mp4, "TEST.MP4", 1024).passed)

    def test_malformed_and_truncated_media_are_rejected(self) -> None:
        corrupted_png = bytearray(_valid_png_fixture())
        corrupted_png[32] ^= 0x01
        self.assertFalse(valid_png_bytes(bytes(corrupted_png)))
        self.assertFalse(valid_png_bytes(_valid_png_fixture()[:-1]))
        self.assertFalse(
            submit_module._valid_evidence_bytes(
                "evidence/project-actions.png", bytes(corrupted_png)
            )
        )

        oversized_dimensions = (
            b"\x89PNG\r\n\x1a\n"
            + _png_chunk(b"IHDR", struct.pack(">IIBBBBB", 20_000, 20_000, 8, 6, 0, 0, 0))
            + _png_chunk(b"IDAT", b"")
            + _png_chunk(b"IEND", b"")
        )
        self.assertFalse(valid_png_bytes(oversized_dimensions))

        truncated_mp4 = _valid_mp4_fixture()[:-1]
        self.assertFalse(valid_mp4_bytes(truncated_mp4))
        self.assertFalse(
            submit_module._valid_evidence_bytes(
                "evidence/project-walkthrough.mp4", truncated_mp4
            )
        )
        self.assertFalse(valid_mp4_bytes(_mp4_box(b"ftyp", b"isom\x00\x00\x00\x00")))

    def test_outage_marker_must_match_grader_contract(self) -> None:
        evidence = self.repo / ".submission-evidence"
        evidence.mkdir()
        marker = evidence / "lab7-actions-outage.txt"

        marker.write_bytes(b"")
        with self.assertRaisesRegex(CourseError, "invalid or too large"):
            list(existing_evidence(self.repo, "lab7"))

        marker.write_bytes(b"\xff\xfe")
        with self.assertRaisesRegex(CourseError, "invalid or too large"):
            list(existing_evidence(self.repo, "lab7"))

        marker.write_text("GitHub was unavailable.\n", encoding="utf-8")
        with self.assertRaisesRegex(CourseError, "invalid or too large"):
            list(existing_evidence(self.repo, "lab7"))

        marker.write_text(
            "Instructor-confirmed outage; manual review required.\n", encoding="utf-8"
        )
        packaged = list(existing_evidence(self.repo, "lab7"))
        self.assertEqual(packaged, [("evidence/lab7-actions-outage.txt", marker)])

    def test_device_key_rejects_symlink(self) -> None:
        key = Path(self.env["XDG_DATA_HOME"]) / "ift383/device_key"
        key.parent.mkdir(parents=True)
        target = self.base / "attacker-controlled-key"
        target.write_bytes(b"x" * 32)
        try:
            key.symlink_to(target)
        except OSError as exc:
            self.skipTest(f"symlinks unavailable: {exc}")
        with mock.patch.dict(os.environ, {"XDG_DATA_HOME": self.env["XDG_DATA_HOME"]}):
            with self.assertRaisesRegex(CourseError, "regular file"):
                ensure_device_secret()

    def test_validator_timeout_kills_child_process_group(self) -> None:
        validator = self.repo / "labs/lab-01/timeout-validator.sh"
        validator.write_text(
            "#!/usr/bin/env bash\n"
            "trap '' TERM\n"
            "(trap '' TERM; sleep 0.5; touch late-marker) &\n"
            "wait\n",
            encoding="utf-8",
        )
        with mock.patch.object(common_module, "VALIDATOR_TIMEOUT_SECONDS", 0.05):
            result = _validator_check(self.repo, validator, "TEST.TIMEOUT")
        self.assertFalse(result.passed)
        self.assertIn("exceeded", result.message)
        time.sleep(0.7)
        self.assertFalse((self.repo / "late-marker").exists())

    def test_missing_committed_artifacts_cannot_be_generated_to_pass(self) -> None:
        self._run("git", "add", ".")
        self._run("git", "commit", "-q", "-m", "Starter validator fixture")

        lab2 = self._run("bash", "labs/lab-02/validate_local.sh", check=False)
        self.assertNotEqual(lab2.returncode, 0)
        self.assertIn("commit Git evidence", lab2.stdout + lab2.stderr)
        self.assertFalse((self.repo / "labs/lab-02/git_evidence.txt").exists())

        lab4 = self._run("bash", "labs/lab-04/validate_local.sh", check=False)
        self.assertNotEqual(lab4.returncode, 0)
        self.assertIn("commit the nonempty run.log", lab4.stdout + lab4.stderr)
        self.assertTrue((self.repo / "labs/lab-04/run.log").exists())

        fake_bin = self.base / "fake-bin"
        fake_bin.mkdir()
        fake_podman = fake_bin / "podman"
        fake_podman.write_text(
            "#!/usr/bin/env bash\n"
            "if [[ ${1:-} == run ]]; then printf '{}\\n'; fi\n"
            "exit 0\n",
            encoding="utf-8",
        )
        fake_podman.chmod(0o755)
        prior_path = self.env.get("PATH", "")
        self.env["PATH"] = f"{fake_bin}{os.pathsep}{prior_path}"
        lab7 = self._run("bash", "labs/lab-07/validate_local.sh", check=False)
        self.assertNotEqual(lab7.returncode, 0)
        self.assertIn("commit the matching result", lab7.stdout + lab7.stderr)
        self.assertFalse((self.repo / "labs/lab-07/container_output.txt").exists())

        project = self._run("bash", "final-project/validate_local.sh", check=False)
        self.assertNotEqual(project.returncode, 0)
        self.assertIn("local_validation.txt was generated", project.stdout + project.stderr)
        self.assertTrue((self.repo / "final-project/local_validation.txt").exists())

    def test_setup_check_and_submit_end_to_end(self) -> None:
        self._prepare_lab1()
        setup = self._run(
            "python3",
            "tools/setup.py",
            "--canvas-login",
            "ada123",
            "--name",
            "Ada Student",
        )
        self.assertIn("setup is complete", setup.stdout)
        key = Path(self.env["XDG_DATA_HOME"]) / "ift383/device_key"
        self.assertEqual(len(key.read_bytes()), 32)
        self.assertEqual(key.stat().st_mode & 0o777, 0o600)

        checked = self._run("python3", "tools/check.py", "lab1", "--json")
        check_data = json.loads(checked.stdout)
        self.assertTrue(check_data["passed"])
        self.assertEqual(
            [item["id"] for item in check_data["results"]],
            [
                "LAB1.DIRECTORY",
                "LAB1.README",
                "LAB1.RECORD",
                "LAB1.LOCAL_VALIDATOR",
            ],
        )

        submitted = self._run("python3", "tools/submit.py", "lab1")
        prefix = "Upload this exact file to Canvas: "
        upload_line = next(line for line in submitted.stdout.splitlines() if line.startswith(prefix))
        archive_path = Path(upload_line.removeprefix(prefix))
        self.assertTrue(archive_path.is_file())

        with zipfile.ZipFile(archive_path) as archive:
            names = set(archive.namelist())
            self.assertEqual(
                names,
                {
                    "IFT383_SUBMISSION/submission.json",
                    "IFT383_SUBMISSION/repository.bundle",
                    "IFT383_SUBMISSION/execution_receipt.json",
                },
            )
            submission = json.loads(archive.read("IFT383_SUBMISSION/submission.json"))
            receipt = json.loads(archive.read("IFT383_SUBMISSION/execution_receipt.json"))
            bundle = archive.read("IFT383_SUBMISSION/repository.bundle")

        self.assertEqual(submission["schema_version"], 1)
        self.assertEqual(submission["assignment"], "lab1")
        self.assertEqual(submission["canvas_login"], "ada123")
        self.assertEqual(submission["bundle_sha256"], hashlib.sha256(bundle).hexdigest())
        self.assertEqual(
            receipt["payload"]["submission_sha256"],
            hashlib.sha256(canonical_json(submission)).hexdigest(),
        )
        self.assertEqual(
            receipt["receipt_sha256"],
            hashlib.sha256(canonical_json(receipt["payload"])).hexdigest(),
        )
        self.assertRegex(receipt["payload"]["nonce"], r"^[0-9a-f]{64}$")
        self.assertRegex(receipt["payload"]["installation_fingerprint"], r"^[0-9a-f]{24}$")

    def test_frozen_bundle_rejects_extra_advertised_refs(self) -> None:
        self._prepare_lab1()
        self._run("git", "branch", "unrelated-branch")
        self._run("git", "tag", "unrelated-tag")
        bundle = self.base / "all-refs.bundle"
        self._run("git", "bundle", "create", str(bundle), "--all")
        head = self._run("git", "rev-parse", "HEAD").stdout.strip()
        with self.assertRaisesRegex(CourseError, "only the captured HEAD"):
            submit_module._verify_frozen_bundle(self.repo, bundle, head)

    def test_committed_validator_cannot_mutate_source_or_inject_packaged_refs(self) -> None:
        validator = """#!/usr/bin/env bash
set -eu
[[ $(git branch --show-current) == main ]]
[[ -z $(git remote) ]]
[[ ! -e $(git rev-parse --git-path objects/info/alternates) ]]
printf 'validator mutation\n' > labs/lab-01/README.md
git branch injected-validator
git tag injected-validator
exit 0
"""
        self._prepare_lab1(validator)
        original_readme = (self.repo / "labs/lab-01/README.md").read_bytes()
        expected_head = self._run("git", "rev-parse", "HEAD").stdout.strip()
        self._run("git", "branch", "source-only-branch")
        self._run("git", "tag", "source-only-tag")
        self._run(
            "python3",
            "tools/setup.py",
            "--canvas-login",
            "adversarial123",
            "--name",
            "Adversarial Fixture",
        )

        submitted = self._run("python3", "tools/submit.py", "lab1")
        prefix = "Upload this exact file to Canvas: "
        archive_path = Path(
            next(line for line in submitted.stdout.splitlines() if line.startswith(prefix)).removeprefix(
                prefix
            )
        )
        self.assertEqual((self.repo / "labs/lab-01/README.md").read_bytes(), original_readme)
        self.assertNotIn("injected-validator", self._run("git", "show-ref").stdout)

        bundle = self.base / "submitted.bundle"
        with zipfile.ZipFile(archive_path) as archive:
            bundle.write_bytes(archive.read("IFT383_SUBMISSION/repository.bundle"))
        advertised = self._run("git", "bundle", "list-heads", str(bundle)).stdout.splitlines()
        self.assertEqual(advertised, [f"{expected_head} HEAD"])

    def test_tracked_symlink_is_rejected_before_submission(self) -> None:
        self._prepare_lab1()
        link = self.repo / "labs/lab-01/tracked-link"
        try:
            link.symlink_to("README.md")
        except OSError as exc:
            self.skipTest(f"symlinks unavailable: {exc}")
        self._run("git", "add", "labs/lab-01/tracked-link")
        self._run("git", "commit", "-q", "-m", "Add unsafe tracked link")
        self._run(
            "python3",
            "tools/setup.py",
            "--canvas-login",
            "link123",
            "--name",
            "Link Fixture",
        )
        submitted = self._run("python3", "tools/submit.py", "lab1", check=False)
        self.assertEqual(submitted.returncode, 2)
        self.assertIn("Only ordinary tracked files", submitted.stderr)


if __name__ == "__main__":
    unittest.main()
