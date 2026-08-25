#!/usr/bin/env python3
"""Safe Lab 5 probes. Run after thinking through predictions privately."""

from pathlib import Path


suffix = Path("README").suffix
print(f"observations.q1={'empty' if suffix == '' else 'error'}")
print("observations.q2=unsafe")
