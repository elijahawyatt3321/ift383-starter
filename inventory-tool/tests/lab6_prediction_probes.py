#!/usr/bin/env python3
"""Safe Lab 6 probes. Run after thinking through predictions privately."""

import importlib.util
import io
import logging
import tempfile
from contextlib import redirect_stdout
from pathlib import Path


with tempfile.TemporaryDirectory(prefix="ift383-import-probe-") as directory:
    module_path = Path(directory) / "probe_module.py"
    module_path.write_text("value = 1\nprint('ran')\n", encoding="utf-8")
    specification = importlib.util.spec_from_file_location("ift383_probe_module", module_path)
    if specification is None or specification.loader is None:
        raise SystemExit("could not create the bounded import probe")
    module = importlib.util.module_from_spec(specification)
    captured_stdout = io.StringIO()
    with redirect_stdout(captured_stdout):
        specification.loader.exec_module(module)
print(f"observations.q1={'yes' if captured_stdout.getvalue().strip() == 'ran' else 'no'}")

logger = logging.getLogger("ift383_prediction_probe")
logger.handlers.clear()
logger.setLevel(logging.WARNING)
captured: list[str] = []


class Capture(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        captured.append(record.getMessage())


logger.addHandler(Capture())
logger.info("informational")
print(f"observations.q2={'yes' if captured else 'no'}")
