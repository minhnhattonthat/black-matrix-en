"""check.py: the repo's one-command check (the pre-commit hook runs it). Add the text lint here once script/ exists."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.exit(subprocess.run([sys.executable, "-X", "utf8", "-m", "pytest", "-q", "tests"], cwd=ROOT).returncode)
