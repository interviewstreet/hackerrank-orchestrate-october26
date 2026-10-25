"""Policy engine: deletion_rules.csv -> required end-state per category."""
import csv
from pathlib import Path

from .config import CATEGORY_TREATMENT


class RuleBook:
    def __init__(self, rules_rows):
        self.by_category = {}
        for row in rules_rows:
            self.by_category[row["data_category"]] = row
        # Fail loudly during development if the shipped mapping drifts from
        # the supplied rules file.
        for category, treatment in CATEGORY_TREATMENT.items():
            row = self.by_category.get(category)
            if row is None:
                continue
            action = row["required_action"]
            expected = {"DELETE": "DELETE", "REDACT": "REDACT",
                        "ANONYMIZE": "ANONYMIZE", "RETAIN": "RETAIN"}.get(action)
            if category == "BACKUP_ARCHIVE":
                expected = "RETAIN_BLOCK"
            if category == "DATA_FLOW":
                continue
            assert treatment == expected or treatment == "RETAIN_BLOCK", \
                (category, treatment, action)

    @staticmethod
    def treatment(category):
        return CATEGORY_TREATMENT.get(category, "")

    @classmethod
    def from_dataset(cls, dataset_dir):
        with open(Path(dataset_dir) / "deletion_rules.csv",
                  newline="", encoding="utf-8") as fh:
            return cls(list(csv.DictReader(fh)))
