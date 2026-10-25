"""Build all startup tables, or load them from the SQLite cache when it is fresh."""
from __future__ import annotations

import logging

from ..logging_setup import stage
from . import cache
from .activities import build_activities
from .context import Context
from .files import build_files
from .identities import build_identity_rows

log = logging.getLogger(__name__)


def build_observations(files):
    """Placeholder until milestone M2 adds the evidence parsers."""
    return [], {}


def load_or_build(use_cache: bool = True) -> Context:
    with stage(log, "startup tables"):
        fp = cache.fingerprint()
        cached = cache.load(fp) if use_cache else None
        if cached is not None:
            files, scopes, identities, activities, observations = cached
        else:
            files = build_files()
            identities = build_identity_rows()
            activities = build_activities()
            observations, scopes = build_observations(files)
            cache.save(files, scopes, identities, activities, observations, fp)
        ctx = Context.build(files, scopes, identities, activities, observations)
        log.info("context: %d identifiers, %d activities, %d observations",
                 len(ctx.user_by_identifier), len(ctx.activities), len(ctx.observations))
        return ctx
