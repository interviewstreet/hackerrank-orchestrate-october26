"""Build all startup tables, or load them from the SQLite cache when it is fresh."""
from __future__ import annotations

import logging

from ..logging_setup import stage
from . import cache
from .activities import build_activities
from .context import Context
from .files import build_files
from .identities import build_identity_rows
from .observations import build_observations

log = logging.getLogger(__name__)


def load_or_build(use_cache: bool = True) -> Context:
    with stage(log, "startup tables"):
        fp = cache.fingerprint()
        cached = cache.load(fp) if use_cache else None
        if cached is not None:
            files, scopes, identities, activities, observations, failures = cached
        else:
            files = build_files()
            identities = build_identity_rows()
            activities = build_activities()
            observations, scopes, failures = build_observations(files)
            cache.save(files, scopes, identities, activities, observations, failures, fp)
        ctx = Context.build(files, scopes, identities, activities, observations, failures)
        log.info("context: %d identifiers, %d activities, %d observations",
                 len(ctx.user_by_identifier), len(ctx.activities), len(ctx.observations))
        return ctx
