"""pytest loads this before any test module: code/ goes first on sys.path, code/evaluation/ last
(``evaluation/main.py`` must never shadow the pipeline's ``main``)."""

import sys
from pathlib import Path

CODE_DIR = Path(__file__).resolve().parent.parent
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))
if str(CODE_DIR / "evaluation") not in sys.path:
    sys.path.append(str(CODE_DIR / "evaluation"))
