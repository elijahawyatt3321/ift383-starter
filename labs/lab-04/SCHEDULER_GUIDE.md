# Lab 4 scheduler guide

Choose **cron** or a **systemd user timer**. Complete only that option's
template in `schedule/`. Both recipes run the same safe dry-run command against
the course fixture. Do not use `sudo`.

First establish absolute paths:

```bash
REPO_ROOT="$(git rev-parse --show-toplevel)"
LAB_DIR="$(realpath "$REPO_ROOT/labs/lab-04")"
printf 'Repository: %s\nLab directory: %s\n' "$REPO_ROOT" "$LAB_DIR"
```

Use `/usr/bin/bash` for the scheduled shell. Confirm its location with
`command -v bash` and adjust only if your course VM reports a different path.

## Option A: cron

1. Check readiness and preserve any error:

   ```bash
   crontab -l
   ```

2. In `schedule/lab4-cron.txt`, replace the example date, time, and every
   `/ABSOLUTE/PATH/TO/REPOSITORY` segment. Choose a time a few minutes ahead.
3. Open `crontab -e`, paste the completed non-comment line, save, and exit.
4. Preserve the installed entry before the scheduled time:

   ```bash
   crontab -l > scheduler_status.txt
   ```

5. After it runs, append the scheduler log and remove the temporary entry with
   `crontab -e`:

   ```bash
   tail -n 20 scheduler-cron.log >> scheduler_status.txt
   ```

The template redirects both output streams to `scheduler-cron.log`. The
matching timestamp also appears in `run.log`, and that run replaces
`last_run.json` with its current JSON summary.

## Option B: systemd user timer

1. Check readiness:

   ```bash
   systemctl --user is-system-running
   ```

2. In `schedule/lab4-logmaint.service`, replace every
   `/ABSOLUTE/PATH/TO/REPOSITORY` segment. The timer template uses
   `OnActiveSec=2min`, so it starts once about two minutes after activation.
3. Install only your completed user units:

   ```bash
   mkdir -p "$HOME/.config/systemd/user"
   cp schedule/lab4-logmaint.service schedule/lab4-logmaint.timer \
     "$HOME/.config/systemd/user/"
   systemctl --user daemon-reload
   systemctl --user enable --now lab4-logmaint.timer
   systemctl --user list-timers lab4-logmaint.timer --no-pager
   ```

4. After the run, preserve status and matching journal lines, then disable the
   temporary timer:

   ```bash
   systemctl --user status lab4-logmaint.timer --no-pager > scheduler_status.txt
   journalctl --user -u lab4-logmaint.service --since '-10 minutes' --no-pager \
     >> scheduler_status.txt
   systemctl --user disable --now lab4-logmaint.timer
   ```

## Published fallback when a user scheduler is unavailable

Save the exact readiness command, its error, and its numeric status in
`scheduler_status.txt`. Then run the same absolute dry-run command once and
append its exit status. For example:

```bash
systemctl --user is-system-running > scheduler_status.txt 2>&1
readiness_status=$?
printf 'readiness_status=%s\n' "$readiness_status" >> scheduler_status.txt
/usr/bin/bash "$LAB_DIR/logmaint.sh" --dir "$LAB_DIR/fixture" --days 7 --dry-run \
  >> scheduler_status.txt 2>&1
fallback_status=$?
printf 'fallback_status=%s\n' "$fallback_status" >> scheduler_status.txt
```

Use this fallback only when the selected scheduler is genuinely unavailable on
your Fedora VM. Do not manufacture an error.
