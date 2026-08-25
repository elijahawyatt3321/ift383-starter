# IFT 383 Semester Repository

This is your private working repository for all seven labs and the final project. Canvas is the official submission system. The included tools run locally and use only Python's standard library, Git, and files in this repository. They do not call an API, upload anything, or contact an instructor grading system.

## Create and clone your private repository once

Run these commands inside the Fedora Linux VM you installed on your own computer for this course. The public course template is `eric-asu/ift383-starter`.

```bash
sudo dnf install -y git gh python3 python3-pytest vim-enhanced podman
gh auth login --web --git-protocol https
gh auth setup-git
gh repo create ift383-course --private \
  --template eric-asu/ift383-starter \
  --clone
cd ift383-course
python3 tools/setup.py
```

Follow the browser sign-in shown by `gh auth login`. The `--private` option is required. You create only one repository and use it for the entire course; course staff do not need routine access.

If the repository already exists because you replaced the VM, use `gh repo clone YOUR-GITHUB-USERNAME/ift383-course` instead of `gh repo create`, then rerun `python3 tools/setup.py` inside the clone.

## Fedora VM: one-time preparation

After setup, confirm that Git and Python 3 are available:

```bash
git --version
python3 --version
```

Setup stores your Canvas login/ASURITE UserID and display name outside tracked course files, then includes those two values as identity metadata in each generated Canvas ZIP. It creates one random installation secret at `~/.local/share/ift383/device_key` with owner-only permissions. The secret itself is never submitted. Do not delete or share it.

Never commit a password, access token, recovery code, private key, or personal dataset. If you accidentally commit a credential, revoke or rotate it immediately and contact the instructor; deleting the file later does not remove it from Git history or from a submitted bundle.

## Each assignment

Use the short assignment IDs `lab1` through `lab7`, or `project`.

1. Complete the assignment and commit all work.
2. Run its visible checks:

   ```bash
   python3 tools/check.py lab1
   ```

3. Fix any reported failures, commit again, and confirm `git status` is clean.
4. Create the Canvas upload:

   ```bash
   python3 tools/submit.py lab1
   ```

5. Upload the exact ZIP path printed by the command to the matching Canvas assignment.

The submission command requires the `main` branch, reruns the visible checks, verifies a full Git bundle, and validates the ZIP before reporting success. It never submits uncommitted work.

## Required evidence locations

When the assignment instructions require evidence, save it at the exact path below before submitting:

- Lab 2 pull request: `.submission-evidence/lab2-pr.png`
- Lab 7 Actions run: `.submission-evidence/lab7-actions.png`
- Final project Actions run: `.submission-evidence/project-actions.png`
- Final project walkthrough: `.submission-evidence/project-walkthrough.mp4`

The submission tool requires these files for the listed assignments and includes them separately in the outer Canvas ZIP. The local evidence directory is intentionally ignored by Git, so do not try to commit it; the receipt hashes the exact submitted files.

PNG evidence is limited to 5 MiB and the walkthrough MP4 is limited to 60 MiB. During an instructor-confirmed GitHub Actions outage only, the instructor may direct you to use `.submission-evidence/lab7-actions-outage.txt` or `.submission-evidence/project-actions-outage.txt` instead of the corresponding Actions PNG. That fallback is packaged with a prominent manual-review warning; it is never a silent substitute. The Lab 2 image and final-project walkthrough remain required.

## Workflows stay inactive until they are taught

There is intentionally no `.github/workflows/` directory at the beginning of the course. During Lab 7, follow its assignment instructions to copy:

```bash
mkdir -p .github/workflows
cp workflow-starters/inventory-tool.yml .github/workflows/inventory-tool.yml
```

During the final project, copy:

```bash
cp workflow-starters/final-project.yml .github/workflows/final-project.yml
```

## What the receipt means

The ZIP contains the exact Git commit and tree, a verified full-history bundle, check result IDs, artifact hashes, a fresh random nonce, and a pseudonymous installation fingerprint. These provide continuity and tamper evidence. They do **not** prove authorship or identify physical hardware. A changed fingerprint is a review flag only; resetting or replacing a VM is legitimate and is never automatic misconduct or an automatic point loss.

## Canvas attempt policy

Only the most recent Canvas submission received by the deadline is used to calculate the grade. Earlier attempts are not combined or used to improve the grade. However, any submission attempt may be reviewed and reported when there is a suspected academic integrity violation.
