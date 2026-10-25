"""Exception types. Each one is caught at a known boundary, never silently."""


class GhostError(Exception):
    """Base class for pipeline errors."""


class ParseError(GhostError):
    """An evidence file could not be parsed. Caught per file in tables/observations."""

    def __init__(self, evidence_id: str, message: str) -> None:
        super().__init__(f"{evidence_id}: {message}")
        self.evidence_id = evidence_id


class DatasetError(GhostError):
    """A required dataset file is missing or malformed. Fatal: the run stops."""


class ModelUnavailable(GhostError):
    """The model API failed after retries, or no key is configured."""
