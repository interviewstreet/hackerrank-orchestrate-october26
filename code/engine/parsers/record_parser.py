"""Plain-text record parser (shift handover / pipe-delimited result rows)."""
from __future__ import annotations

import re
from typing import List, Tuple

from ..contracts import Coverage, Observation
from .common import RESULT_TO_STATE, make_obs

ROW_RE = re.compile(r"^\s*-\s*(\S+)\s*\|\s*(\w+)\s*\|\s*(\S+)\s*\|\s*(\w+)\s*\|\s*(\w+)\s*\|\s*(.+?)\s*$")


def parse_txt(evidence_id: str, captured_at: str, path: str) -> Tuple[List[Observation], List[Coverage]]:
    obs: List[Observation] = []
    for n, line in enumerate(open(path, encoding="utf-8"), 1):
        m = ROW_RE.match(line)
        if not m:
            continue
        ts, system, rid, rtype, result, subject = m.groups()
        state = RESULT_TO_STATE.get(result.upper())
        if not state:
            continue
        o = make_obs(evidence_id, captured_at, {"resource_id": rid, "subject_reference": subject},
                     system_id=system, category=rtype, state=state, observed_at=ts, source_format="txt",
                     locator=f"line {n}", extra_attrs={"result": result.upper(), "identifiable": result.upper() == "IDENTIFIABLE"})
        if o:
            obs.append(o)
    return obs, []
