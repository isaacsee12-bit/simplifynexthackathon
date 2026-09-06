import sys
from pathlib import Path

# Preserve the backend's local imports when loaded from the repository root.
sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from main import app
