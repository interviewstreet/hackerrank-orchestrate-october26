"""State reconstruction at audit_at and policy comparison.

For every (system, resource) linked to the subject we take the latest
evidence-backed (non-claim) fact at or before audit_at. Facts at the same
latest instant from several renderings of the same snapshot are merged:
PRESENT wins over ABSENT (replication drift: a copy still present in a
replica is a remaining record), and exposure is OR-ed.
"""
from dataclasses import dataclass

from .policy import RuleBook


@dataclass
class ResourceState:
    system_id: str
    resource_id: str
    category: str
    verdict: str        # VIOLATION_* | OK_* | SKIP
    evidence_id: str
    observed_at: object = None


VIOLATION_KINDS = {"VIOLATION_REMAINING", "VIOLATION_EXPOSED",
                   "VIOLATION_FLOW", "VIOLATION_RESTORE"}


def _intersects(fact, ids):
    return bool(fact.emails & ids["emails"] or fact.hashes & ids["hashes"]
                or fact.phones & ids["phones"]
                or fact.user_ids & ids["user_ids"])


class StateReconstructor:
    def __init__(self, store, rulebook=None):
        self.store = store
        self.rulebook = rulebook or RuleBook.__new__(RuleBook)

    # -- linking ---------------------------------------------------------
    @staticmethod
    def _eligible(fact, audit_at):
        """A fact may be used if its own (inner) timestamp is <= audit_at.

        Inner timestamps are the snapshot/log-line times; a bundle exported
        or a log collected a day later can still contain a snapshot taken
        before the audit. *Citation* is stricter (see resource_state): the
        cited file itself must have been captured by audit_at whenever such
        a file can prove the same state.
        """
        if fact.is_claim or fact.observed_at is None:
            return False
        return fact.observed_at <= audit_at

    def linked_resource_ids(self, ids, audit_at, links):
        linked = {}
        for fact in self.store.facts:
            if not self._eligible(fact, audit_at):
                continue
            if _intersects(fact, ids):
                linked[fact.resource_id] = True
        for (ts, resource_id, email, user_id, _aid) in links:
            if ts is not None and ts > audit_at:
                continue
            if (email and email in ids["emails"]) or \
                    (user_id and user_id in ids["user_ids"]):
                linked[resource_id] = True
        return linked

    # -- state -----------------------------------------------------------
    def resource_state(self, resource_id, audit_at):
        facts = [f for f in self.store.facts_for_resource(resource_id)
                 if self._eligible(f, audit_at)]
        if not facts:
            return None
        latest_ts = max(f.observed_at for f in facts)
        latest = [f for f in facts if f.observed_at == latest_ts]
        # Prefer a fact that actually carries a category/system, and for
        # citation prefer a file captured by audit_at over a later export
        # that merely contains an equally-timed snapshot.
        manifest_ok = [f for f in latest
                       if f.manifest_at is not None
                       and f.manifest_at <= audit_at]
        base = (manifest_ok or latest)[-1]
        presence = "PRESENT" if any(f.presence == "PRESENT" for f in latest) \
            else "ABSENT"
        exposed = any(f.exposed for f in latest if f.presence == "PRESENT")
        attributable = any(f.attributable for f in latest
                           if f.presence == "PRESENT")
        enabled_vals = [f.enabled for f in latest if f.enabled is not None]
        enabled = True if any(enabled_vals) else (
            False if enabled_vals else None)
        restore_vals = [f.restore_allowed for f in latest
                        if f.restore_allowed is not None]
        restore = True if any(restore_vals) else (
            False if restore_vals else None)
        merged = ResourceState(base.system_id, resource_id, base.category,
                               "", base.source_id, latest_ts)
        verdict = self._verdict(base.category, presence, exposed,
                                attributable, enabled, restore)
        merged.verdict = verdict
        merged._exposed = exposed
        # Citation: latest file captured by audit_at that on its own proves
        # the same verdict; fall back to the latest proving file overall.
        support = [f for f in facts
                   if self._verdict(f.category, f.presence, f.exposed,
                                    f.attributable, f.enabled,
                                    f.restore_allowed) == verdict]
        manifest_ok = [f for f in support
                       if f.manifest_at is not None
                       and f.manifest_at <= audit_at]
        if manifest_ok:
            merged.evidence_id = max(manifest_ok,
                                     key=lambda f: f.observed_at).source_id
        elif support:
            merged.evidence_id = max(support,
                                     key=lambda f: f.observed_at).source_id
        return merged

    @staticmethod
    def _verdict(category, presence, exposed, attributable, enabled, restore):
        treatment = RuleBook.treatment(category)
        if treatment == "DELETE":
            return "VIOLATION_REMAINING" if presence == "PRESENT" else "OK_ABSENT"
        if treatment == "REDACT":
            if presence == "ABSENT":
                return "OK_ABSENT"
            return "VIOLATION_EXPOSED" if exposed else "OK_REDACTED"
        if treatment == "ANONYMIZE":
            if presence == "ABSENT":
                return "OK_ABSENT"
            return "VIOLATION_EXPOSED" if (exposed or attributable) \
                else "OK_ANONYMIZED"
        if treatment == "RETAIN":
            return "OK_PRESENT" if presence == "PRESENT" else "SKIP"
        if treatment == "RETAIN_BLOCK":
            if presence != "PRESENT" or restore is None:
                return "SKIP"
            return "VIOLATION_RESTORE" if restore else "OK_BLOCKED"
        if treatment == "DISABLE":
            if presence != "PRESENT" or enabled is None:
                return "SKIP"
            return "VIOLATION_FLOW" if enabled else "OK_DISABLED"
        return "SKIP"

    # -- assignment of identifier-free compliant resources ---------------
    def _assign_unlinked(self, ids, audit_at, states):
        """Assign an anonymized/absent/redacted resource with no identifiers
        left, found in the case's primary evidence file, when the subject
        has no linked resource of that system yet.

        Such a record can no longer be linked by its own fields (that is
        the point of anonymization). Assignment is by elimination inside
        the one file that already proves other resources of this subject:
        exactly the situation of a 404 profile lookup or an anonymized
        analytics profile sitting next to the subject's audit record.
        It only fires when exactly one such candidate exists for the
        system, so it can never guess between two people's records.
        """
        covered = {s.system_id for s in states}
        source_count = {}
        source_times = {}
        for fact in self.store.facts:
            if not self._eligible(fact, audit_at):
                continue
            if _intersects(fact, ids):
                source_count[fact.source_id] = source_count.get(fact.source_id, 0) + 1
                source_times.setdefault(fact.source_id, []).append(fact.observed_at)
        if not source_count:
            return states
        primary = max(source_count,
                      key=lambda s: (source_count[s], max(source_times[s])))
        candidates = {}
        for fact in self.store.facts:
            if fact.source_id != primary or not self._eligible(fact, audit_at):
                continue
            if fact.emails or fact.user_ids or fact.phones or fact.hashes:
                continue  # identifier-bearing: belongs to someone identifiable
            state = self.resource_state(fact.resource_id, audit_at)
            if state is None or not state.verdict.startswith("OK_"):
                continue
            if state.system_id in covered:
                continue
            candidates.setdefault(state.system_id, set()).add(
                state.resource_id)
        resource_by_system = {}
        for fact in self.store.facts:
            if fact.source_id != primary:
                continue
            resource_by_system.setdefault(fact.resource_id, fact)
        for system_id, resource_ids in candidates.items():
            if len(resource_ids) != 1:
                continue  # ambiguous: never guess between candidates
            states.append(self.resource_state(next(iter(resource_ids)),
                                              audit_at))
            covered.add(state.system_id)
        return states

    # -- per-case ---------------------------------------------------------
    def evaluate_case(self, ids, audit_at, links):
        states = []
        for resource_id in self.linked_resource_ids(ids, audit_at, links):
            state = self.resource_state(resource_id, audit_at)
            if state is not None and state.verdict != "SKIP":
                states.append(state)
        states = self._assign_unlinked(ids, audit_at, states)
        states.sort(key=lambda s: (s.system_id, s.resource_id))
        return states
