"""check.py: the repo's one-command check (the pre-commit hook runs it). Add the text lint here once script/ exists."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# no:faulthandler: unicorn's JIT takes access violations it handles itself, and pytest would print each as a fatal exception
sys.exit(subprocess.run([sys.executable, "-X", "utf8", "-m", "pytest", "-q", "-p", "no:faulthandler", "tests"], cwd=ROOT).returncode)
