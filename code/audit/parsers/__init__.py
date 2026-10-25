"""Load every manifest evidence file once into a FactStore."""
from pathlib import Path

from ..facts import FactStore
from ..loaders import parse_ts
from . import sql_parser, json_parser, log_parser, text_parser
from .pdf_parser import parse_pdf_file
from .image_parser import parse_image_file


def build_fact_store(dataset_dir, evidence_rows):
    dataset_dir = Path(dataset_dir)
    store = FactStore()
    stats = {}
    for row in evidence_rows:
        file_id = row["file_id"]
        rel = row["file_path"]
        path = dataset_dir / rel
        manifest_ts = parse_ts(row.get("captured_at"))
        count = 0
        store.current_manifest = manifest_ts
        try:
            if not path.exists():
                stats[file_id] = 0
                continue
            suffix = path.suffix.lower()
            if suffix == ".sql":
                count = sql_parser.parse_sql_text(
                    path.read_text(encoding="utf-8", errors="ignore"),
                    file_id, store, manifest_ts)
            elif suffix == ".json":
                count = json_parser.parse_json_text(
                    path.read_text(encoding="utf-8", errors="ignore"),
                    file_id, store, manifest_ts)
            elif suffix == ".log":
                count = log_parser.parse_log_text(
                    path.read_text(encoding="utf-8", errors="ignore"),
                    file_id, store, manifest_ts)
            elif suffix == ".txt":
                count = text_parser.parse_text_content(
                    path.read_text(encoding="utf-8", errors="ignore"),
                    file_id, store, manifest_ts)
            elif suffix == ".pdf":
                count = parse_pdf_file(path, file_id, store, manifest_ts)
            elif suffix == ".png":
                count = parse_image_file(path, file_id, store, manifest_ts)
        except Exception as exc:  # one bad file must not kill the run
            print(f"WARNING: failed to parse {rel}: {exc}")
            count = 0
        stats[file_id] = count
    return store, stats
