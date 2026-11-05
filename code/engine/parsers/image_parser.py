"""Screenshot parser: OCR via tesseract, cached under .cache/ocr. OCR facts are lower-confidence evidence."""
from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path
from typing import List, Tuple

from ..contracts import Coverage, Observation
from .document_parser import text_to_observations

CACHE_DIR = Path(".cache") / "ocr"


def ocr_text(path: str) -> str:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha1(Path(path).read_bytes()).hexdigest()
    cached = CACHE_DIR / f"{key}.txt"
    if cached.exists():
        return cached.read_text(encoding="utf-8")
    text = subprocess.run(["tesseract", path, "-", "--psm", "11"], capture_output=True, text=True, check=False).stdout
    cached.write_text(text, encoding="utf-8")
    return text


def parse_image(evidence_id: str, captured_at: str, path: str) -> Tuple[List[Observation], List[Coverage]]:
    text = ocr_text(path)
    return text_to_observations(evidence_id, captured_at, [text], "image", 0.6, path.split("/")[-1]), []
