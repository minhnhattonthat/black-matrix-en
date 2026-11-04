"""check.py: the repo's one-command check (the pre-commit hook runs it). The text lint and the build's byte checks run in tests/test_build.py."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# no:faulthandler: unicorn's JIT takes access violations it handles itself, and pytest would print each as a fatal exception
sys.exit(subprocess.run([sys.executable, "-X", "utf8", "-m", "pytest", "-q", "-p", "no:faulthandler", "tests"], cwd=ROOT).returncode)
