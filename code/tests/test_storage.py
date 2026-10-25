from __future__ import annotations

from pathlib import Path

from erasecase.contracts import ModelCallRecord
from erasecase.storage import RunStore


def test_run_store_records_one_model_call(tmp_path: Path) -> None:
    database = tmp_path / "run.sqlite3"
    record = ModelCallRecord(
        call_id="call-1",
        stage="probe",
        requested_model="example/model",
        attempts=1,
        latency_ms=15,
        outcome="ok",
    )
    with RunStore(database) as store:
        store.record_model_call(record)
    with RunStore(database) as store:
        count = store._connection.execute("SELECT COUNT(*) FROM model_calls").fetchone()[0]
    assert count == 1
