"""pytest loads this before any test module: code/ goes first on sys.path, code/evaluation/ last
(``evaluation/main.py`` must never shadow the pipeline's ``main``)."""

import os
import sys
from pathlib import Path

# Tests never call the network: every model result is replayed, even when a key is set.
os.environ["ZENMUX_OFFLINE"] = "1"

CODE_DIR = Path(__file__).resolve().parent.parent
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))
if str(CODE_DIR / "evaluation") not in sys.path:
    sys.path.append(str(CODE_DIR / "evaluation"))
