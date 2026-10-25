"""Synthetic tests for resolver, policy rows, citation, status rule and safety invariants."""

import unittest
from datetime import UTC, datetime, timedelta

import helpers  # noqa: F401  (puts code/ on sys.path)
import planner
from evidence.common import (
    ABSENT,
    ACTIVE,
    ACTIVITY_READBACK,
    BLOCKED,
    IDENTIFIABLE,
    OPEN,
    OPERATION_CLAIM,
    PRESENT,
    SNAPSHOT_ROW,
    STATE_READBACK,
    Identifiers,
    Observation,
    Scope,
)
from facts import FactStore
from links import Edge, Target
from policy import (
    COMPLIANT,
    MISSING_RETAINED,
    NOT_TARGET,
    UNPROVEN,
    VIOLATION,
    Decision,
    SafetyViolation,
    check_safety,
    content_category,
    evaluate,
)
from resolver import UNKNOWN, exists_rollup, resolve
from schema import Operation as Op
from schema import Status

T0 = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)
AUDIT = T0 + timedelta(days=10)
SUBJECT = Identifiers(emails={"ana@example.com"}, user_ids={"user_1"})
_n = 0


def obs(system, rid, *, at=T0, copy="primary", assertion=SNAPSHOT_ROW, file_id=None, available_at=None,
        record_type="", ids=None, exposed="same", **state):
    global _n
    _n += 1
    ids = ids if ids is not None else Identifiers(emails={"ana@example.com"}, user_ids={"user_1"})
    return Observation(obs_id=f"o{_n}", file_id=file_id or f"evidence_{_n}", source_kind="sql", family="test",
                       available_at=available_at or at, state_observed_at=at, system_id=system, resource_id=rid,
                       assertion=assertion, physical_copy=copy, record_type=record_type, link_ids=ids,
                       exposed_ids=ids if exposed == "same" else exposed, **state)


def scope(system, file_id, *, at=T0, copy="primary", subjects=None):
    return Scope(file_id=file_id, family="test", system_id=system, physical_copy=copy, available_at=at,
                 observed_at=at, subjects=subjects)


def run(observations, scopes=(), system="account_service", rid="account_1", cutoff=AUDIT):
    store = FactStore()
    store.add(list(observations), list(scopes))
    target = Target(system, rid, [Edge("identifier", "strong", "x", T0)])
    state = resolve(store, target, SUBJECT, cutoff)
    decision = evaluate(state, cutoff)
    return state, decision, planner.build_item(target, state, decision)


class ResolverTest(unittest.TestCase):
    def test_each_copy_is_resolved_separately(self):
        # case_05 shape: primary missing from a full snapshot, failover still holds the row.
        state, d, item = run([obs("account_service", "account_1", copy="failover_replica", file_id="evidence_54",
                                  exists=PRESENT)],
                             [scope("account_service", "evidence_54"),
                              scope("account_service", "evidence_54", copy="failover_replica")])
        self.assertEqual(state.copies["primary"].get("exists"), ABSENT)
        self.assertEqual(state.copies["failover_replica"].get("exists"), PRESENT)
        self.assertEqual((d.outcome, d.copy), (VIOLATION, "failover_replica"))
        self.assertEqual(item.evidence_id, "evidence_54")

    def test_absence_only_inside_declared_scope(self):
        # evidence_90 shape: a primary-only scope says nothing about the failover copy.
        state, _, _ = run([obs("account_service", "account_1", copy="failover_replica", exists=PRESENT)],
                          [scope("account_service", "evidence_90", at=T0 + timedelta(days=2))])
        self.assertEqual(state.copies["primary"].get("exists"), ABSENT)
        self.assertEqual(state.copies["failover_replica"].get("exists"), PRESENT)
        self.assertEqual(exists_rollup(state), PRESENT)

    def test_subject_scope_needs_a_subject_identifier(self):
        other = Identifiers(emails={"bob@example.com"})
        state, d, _ = run([], [scope("account_service", "evidence_7", subjects=other)])
        self.assertFalse(state.known)
        self.assertEqual(d.outcome, UNPROVEN)
        state, d, item = run([], [scope("account_service", "evidence_7", subjects=SUBJECT)])
        self.assertEqual((d.outcome, item.evidence_id), (COMPLIANT, "evidence_7"))

    def test_collection_scope_covers_only_its_own_collection(self):
        # r2-#2: a later attachment listing says nothing about a message in another collection.
        message = obs("support_platform", "support_1", file_id="evidence_1", exists=PRESENT,
                      record_type="SUPPORT_MESSAGE", treatment=IDENTIFIABLE)
        message.collection = "support_messages"
        listing = scope("support_platform", "evidence_2", at=T0 + timedelta(days=1), subjects=SUBJECT)
        listing.collection = "ticket_attachments"
        state, d, _ = run([message], [listing], system="support_platform", rid="support_1")
        self.assertEqual(state.copies["primary"].get("exists"), PRESENT)
        self.assertEqual(d.outcome, VIOLATION)
        listing.collection = "support_messages"   # the same collection: the listing proves absence
        state, _, _ = run([message], [listing], system="support_platform", rid="support_1")
        self.assertEqual(state.copies["primary"].get("exists"), ABSENT)
        listing.collection = "ticket_attachments"   # an unknown target collection is never covered
        state, d, _ = run([], [listing], system="support_platform", rid="support_1")
        self.assertFalse(state.known)

    def test_cutoff_is_inclusive(self):
        # case_11 shape: the file is captured exactly at audit_at and counts.
        row = obs("search_service", "search_1", at=AUDIT, exists=PRESENT)
        _, d, _ = run([row], system="search_service", rid="search_1", cutoff=AUDIT)
        self.assertEqual(d.outcome, VIOLATION)
        _, d, _ = run([obs("search_service", "search_1", at=AUDIT, exists=PRESENT)], system="search_service",
                      rid="search_1", cutoff=AUDIT - timedelta(seconds=1))
        self.assertEqual(d.outcome, UNPROVEN)

    def test_later_file_with_earlier_inner_time_is_excluded(self):
        row = obs("search_service", "search_1", at=T0, available_at=AUDIT + timedelta(hours=1), exists=PRESENT)
        _, d, _ = run([row], system="search_service", rid="search_1")
        self.assertEqual(d.outcome, UNPROVEN)

    def test_operation_claim_is_never_proof(self):
        claim = obs("account_service", "account_1", assertion=OPERATION_CLAIM, exists=ABSENT)
        state, d, item = run([claim])
        self.assertFalse(state.known)
        self.assertEqual(d.outcome, UNPROVEN)
        self.assertEqual(planner.decide_status([item]), Status.INCOMPLETE.value)

    def test_equal_tier_disagreement_is_conflict(self):
        a = obs("integration_service", "data_flow_1", assertion=STATE_READBACK, file_id="evidence_1",
                exists=PRESENT, flow_state=ACTIVE)
        b = obs("integration_service", "data_flow_1", assertion=STATE_READBACK, file_id="evidence_2",
                exists=PRESENT, flow_state="DISABLED")
        state, d, _ = run([a, b], system="integration_service", rid="data_flow_1")
        self.assertEqual(state.copies["primary"].get("flow_state"), "CONFLICT")
        self.assertEqual(d.outcome, UNPROVEN)

    def test_newest_observation_wins(self):
        row = obs("integration_service", "data_flow_1", at=T0, exists=PRESENT, flow_state="DISABLED")
        check = obs("integration_service", "data_flow_1", at=T0 + timedelta(hours=1), assertion=ACTIVITY_READBACK,
                    flow_state=ACTIVE)
        state, _, _ = run([row, check], system="integration_service", rid="data_flow_1")
        self.assertEqual(state.copies["primary"].get("flow_state"), ACTIVE)

    def test_newer_scoped_absence_supersedes_older_row(self):
        # A deletion after a snapshot: the later full snapshot no longer lists the row.
        row = obs("account_service", "account_1", at=T0, file_id="evidence_1", exists=PRESENT)
        later = scope("account_service", "evidence_2", at=T0 + timedelta(days=1))
        state, d, item = run([row], [later])
        self.assertEqual(state.copies["primary"].get("exists"), ABSENT)
        self.assertEqual((d.outcome, item.evidence_id), (COMPLIANT, "evidence_2"))

    def test_tier_breaks_ties_only_at_same_time(self):
        row = obs("integration_service", "data_flow_1", at=T0, exists=PRESENT, flow_state="DISABLED")
        check = obs("integration_service", "data_flow_1", at=T0, assertion=ACTIVITY_READBACK, flow_state=ACTIVE)
        state, _, _ = run([row, check], system="integration_service", rid="data_flow_1")
        self.assertEqual(state.copies["primary"].get("flow_state"), "DISABLED")

    def test_older_contradicting_observation_changes_nothing(self):
        # Metamorphic: adding an older statement with the opposite state must not change the result.
        base = [obs("search_service", "search_1", at=T0 + timedelta(days=2), file_id="evidence_5", exists=PRESENT)]
        scopes = [scope("search_service", "evidence_4", at=T0 + timedelta(days=1))]
        before = run(base, scopes, system="search_service", rid="search_1")
        older = [obs("search_service", "search_1", at=T0 - timedelta(days=5), assertion=STATE_READBACK,
                     file_id="evidence_3", exists=ABSENT)]
        older_scope = [scope("search_service", "evidence_2", at=T0 - timedelta(days=9))]
        after = run(base + older, scopes + older_scope, system="search_service", rid="search_1")
        for (s1, d1, i1), (s2, d2, i2) in [(before, after)]:
            self.assertEqual({c: v.values for c, v in s1.copies.items()}, {c: v.values for c, v in s2.copies.items()})
            self.assertEqual((d1.outcome, d1.copy, i1.evidence_id), (d2.outcome, d2.copy, i2.evidence_id))
            self.assertEqual(planner.plan([i1]), planner.plan([i2]))
        self.assertEqual(before[1].outcome, VIOLATION)


class PolicyRowTest(unittest.TestCase):
    """One test per rule row that a sample exercises."""

    def _one(self, system, rid, **kw):
        return run([obs(system, rid, **kw)], system=system, rid=rid)[1]

    def test_rule_01_user_profile_delete(self):
        d = self._one("account_service", "account_1", exists=PRESENT)
        self.assertEqual((d.rule_id, d.outcome, d.finding, d.remediation, d.verification),
                         ("rule_01", VIOLATION, Op.REPORT_REMAINING_RECORD, Op.DELETE_RECORD, Op.VERIFY_RECORD_ABSENT))

    def test_rule_03_search_entry_delete(self):
        d = self._one("search_service", "search_1", exists=PRESENT)
        self.assertEqual((d.rule_id, d.outcome, d.remediation), ("rule_03", VIOLATION, Op.DELETE_RECORD))

    def test_rule_05_support_message_redact(self):
        d = self._one("support_platform", "support_1", record_type="SUPPORT_MESSAGE", exists=PRESENT,
                      treatment=IDENTIFIABLE)
        self.assertEqual((d.rule_id, d.outcome, d.finding, d.remediation),
                         ("rule_05", VIOLATION, Op.REPORT_EXPOSED_PII, Op.REDACT_RECORD))

    def test_rule_06_support_attachment_delete(self):
        store_obs = obs("support_platform", "support_2", exists=PRESENT)
        store_obs.collection = "ticket_attachments"
        d = run([store_obs], system="support_platform", rid="support_2")[1]
        self.assertEqual((d.category, d.remediation), ("SUPPORT_ATTACHMENT", Op.DELETE_RECORD))

    def test_rule_07_analytics_user_id_is_attributable(self):
        d = self._one("analytics_platform", "analytics_1", exists=PRESENT, ids=Identifiers(user_ids={"user_1"}))
        self.assertEqual((d.rule_id, d.outcome, d.remediation), ("rule_07", VIOLATION, Op.ANONYMIZE_RECORD))

    def test_rule_07_analytics_without_identifiers_is_compliant(self):
        row = obs("analytics_platform", "analytics_1", exists=PRESENT, exposed=Identifiers())
        d = run([row], system="analytics_platform", rid="analytics_1")[1]
        self.assertEqual((d.outcome, d.verification), (COMPLIANT, Op.VERIFY_RECORD_ANONYMIZED))

    def test_rule_12_security_log_is_retained(self):
        d = self._one("security_service", "audit_record_1", exists=PRESENT)
        self.assertEqual((d.rule_id, d.outcome, d.finding, d.remediation, d.verification),
                         ("rule_12", COMPLIANT, None, None, Op.VERIFY_RECORD_PRESENT))

    def test_rule_06_attachment_is_deleted_only_when_proven_exclusive(self):
        def decide(edge_kind, *, exclusive=False, shared=()):
            store = FactStore()
            store.add([obs("object_storage", "object_1", exists=PRESENT, record_type="SUPPORT_ATTACHMENT")], [])
            target = Target("object_storage", "object_1", [Edge(edge_kind, "strong", "x", T0)],
                            exclusive=exclusive, shared_with=set(shared))
            return evaluate(resolve(store, target, SUBJECT, AUDIT), AUDIT)

        own = decide("identifier")   # the record carries only the subject's identifier
        self.assertEqual((own.outcome, own.remediation), (VIOLATION, Op.DELETE_RECORD))
        catalog = decide("catalog_link", exclusive=True)   # "belongs only to" in the catalog
        self.assertEqual((catalog.outcome, catalog.remediation), (VIOLATION, Op.DELETE_RECORD))
        for d in (decide("catalog_link"), decide("identifier", shared={"user_9"})):
            self.assertEqual((d.outcome, d.reason, d.finding, d.remediation, d.verification),
                             (UNPROVEN, "attachment not proven exclusive", None, None, None))

    def test_rule_13_legal_hold_needs_an_active_hold(self):
        def hold(**fields):
            return self._one("legal_service", "legal_hold_1", exists=PRESENT, fields=fields)

        active = hold(retained_until="2033-12-31T23:59:59Z")   # the dataset's form: an end date, no status
        self.assertEqual((active.outcome, active.verification), (COMPLIANT, Op.VERIFY_RECORD_PRESENT))
        self.assertEqual(hold(hold_status="ACTIVE").outcome, COMPLIANT)
        for status in ("INACTIVE", "released"):
            gone = hold(hold_status=status, retained_until="2033-12-31T23:59:59Z")
            self.assertEqual((gone.outcome, gone.remediation), (VIOLATION, Op.DELETE_RECORD))
        missing = hold()
        self.assertEqual((missing.outcome, missing.reason, missing.verification),
                         (UNPROVEN, "legal hold status missing", Op.VERIFY_RECORD_PRESENT))
        ended = hold(retained_until="2026-01-01T00:00:00Z")
        self.assertEqual((ended.outcome, ended.remediation), (VIOLATION, Op.DELETE_RECORD))
        # r2-#4: an explicit status governs; an active status with a past end date is a contradiction.
        contra = hold(hold_status="ACTIVE", retained_until="2026-01-01T00:00:00Z")
        self.assertEqual((contra.outcome, contra.reason, contra.finding, contra.remediation, contra.verification),
                         (UNPROVEN, "legal hold status contradicts its end date", None, None,
                          Op.VERIFY_RECORD_PRESENT))
        kept = hold(hold_status="ACTIVE", retained_until="2033-12-31T23:59:59Z")
        self.assertEqual((kept.outcome, kept.remediation), (COMPLIANT, None))

    def test_rule_12_missing_retained_record(self):
        _, d, item = run([], [scope("security_service", "evidence_3", subjects=SUBJECT)],
                         system="security_service", rid="audit_record_1")
        self.assertEqual(d.outcome, MISSING_RETAINED)
        self.assertEqual(planner.plan([item]), (Status.INCOMPLETE.value, [
            {"step_no": 1, "phase": "VERIFICATION", "system_id": "security_service", "resource_id": "audit_record_1",
             "operation": "VERIFY_RECORD_PRESENT", "state": "PRESENT", "evidence_id": ""}]))

    def test_rule_14_backup_restore_open(self):
        d = self._one("backup_service", "backup_1", exists=PRESENT, restore_state=OPEN)
        self.assertEqual((d.rule_id, d.outcome, d.remediation), ("rule_14", VIOLATION, Op.BLOCK_RESTORE))
        d = self._one("backup_service", "backup_1", exists=PRESENT, restore_state=BLOCKED)
        self.assertEqual((d.outcome, d.verification), (COMPLIANT, Op.VERIFY_RESTORE_BLOCKED))

    def test_rule_15_tombstone(self):
        clean = obs("identity_service", "tombstone_1", exists=PRESENT, ids=Identifiers(user_ids={"user_1"}))
        d = run([clean], system="identity_service", rid="tombstone_1")[1]
        self.assertEqual((d.rule_id, d.outcome, d.verification), ("rule_15", COMPLIANT, Op.VERIFY_RECORD_REDACTED))
        d = self._one("identity_service", "tombstone_1", exists=PRESENT)
        self.assertEqual((d.outcome, d.finding, d.remediation),
                         (VIOLATION, Op.REPORT_EXPOSED_PII, Op.REDACT_RECORD))

    def test_data_flow_active(self):
        d = self._one("integration_service", "data_flow_1", exists=PRESENT, flow_state=ACTIVE)
        self.assertEqual((d.outcome, d.finding, d.remediation),
                         (VIOLATION, Op.REPORT_ACTIVE_DATA_FLOW, Op.DISABLE_DATA_FLOW))

    def test_process_copy_that_is_not_absent_must_be_proven(self):
        # r2-#1: one DISABLED copy does not prove a present copy whose flow state is unknown.
        primary = obs("integration_service", "data_flow_1", exists=PRESENT, flow_state="DISABLED")
        replica = obs("integration_service", "data_flow_1", copy="read_replica", exists=PRESENT)
        d = run([primary, replica], system="integration_service", rid="data_flow_1")[1]
        self.assertEqual(d.outcome, UNPROVEN)
        # An absent replica runs no flow: an unknown state there does not block the proof.
        gone = obs("integration_service", "data_flow_1", copy="read_replica", exists=ABSENT)
        d = run([primary, gone], system="integration_service", rid="data_flow_1")[1]
        self.assertEqual((d.outcome, d.copy), (COMPLIANT, "primary"))
        backup = obs("backup_service", "backup_1", exists=PRESENT, restore_state=BLOCKED)
        backup_copy = obs("backup_service", "backup_1", copy="replica_eu_west", exists=PRESENT)
        d = run([backup, backup_copy], system="backup_service", rid="backup_1")[1]
        self.assertEqual(d.outcome, UNPROVEN)

    def test_out_of_rules_system_is_not_a_target(self):
        d = self._one("object_storage", "object_1", exists=PRESENT)
        self.assertEqual(d.outcome, NOT_TARGET)


class StatusAndSafetyTest(unittest.TestCase):
    def test_status_rule(self):
        _, _, bad = run([obs("search_service", "search_1", exists=PRESENT)], system="search_service", rid="search_1")
        _, _, good = run([], [scope("account_service", "evidence_9")])
        _, _, unknown = run([], system="account_service", rid="account_2")
        self.assertEqual(planner.decide_status([bad, good]), Status.INCOMPLETE.value)
        self.assertEqual(planner.decide_status([good]), Status.COMPLETE.value)
        # One unproven target keeps the case INCOMPLETE (every relevant copy must be proven).
        self.assertEqual(planner.decide_status([good, unknown]), Status.INCOMPLETE.value)
        self.assertEqual(planner.decide_status([unknown]), Status.INCOMPLETE.value)
        self.assertEqual(planner.decide_status([]), Status.INCOMPLETE.value)
        status, steps = planner.plan([good, unknown])
        self.assertEqual(status, Status.INCOMPLETE.value)
        self.assertEqual([(s["resource_id"], s["operation"], s["evidence_id"]) for s in steps],
                         [("account_1", "VERIFY_RECORD_ABSENT", ""), ("account_2", "VERIFY_RECORD_ABSENT", "")])
        _, steps = planner.plan([unknown])
        self.assertEqual([(s["operation"], s["evidence_id"]) for s in steps], [("VERIFY_RECORD_ABSENT", "")])

    def test_catalog_words_naming_two_categories_give_no_category(self):
        def decide(*texts):
            store = FactStore()
            store.add([obs("object_storage", "object_1", exists=PRESENT)], [])
            target = Target("object_storage", "object_1", [Edge("identifier", "strong", "x", T0)],
                            descriptions=list(texts))
            return evaluate(resolve(store, target, SUBJECT, AUDIT), AUDIT)

        self.assertEqual(decide("Attachment catalog confirmed object_1").category, "SUPPORT_ATTACHMENT")
        both = decide("Attachment catalog confirmed object_1", "Nightly backup set holds object_1")
        self.assertEqual((both.outcome, both.category, both.reason), (UNPROVEN, "", "ambiguous category"))
        self.assertEqual(content_category(["attachment in the nightly backup"]), "")

    def test_never_delete_or_anonymize_retained(self):
        for op in (Op.DELETE_RECORD, Op.ANONYMIZE_RECORD):
            d = Decision("SECURITY_AUDIT_LOG", "rule_12", VIOLATION, remediation=op)
            with self.assertRaises(SafetyViolation):
                check_safety(d, foreign_only=False, proof_assertions=[])
        expired = Decision("SECURITY_AUDIT_LOG", "rule_12", VIOLATION, remediation=Op.DELETE_RECORD,
                           hypothesis=["retention_expired_delete"])
        check_safety(expired, foreign_only=False, proof_assertions=[])

    def test_never_act_on_foreign_only_record(self):
        d = Decision("USER_PROFILE", "rule_01", VIOLATION, remediation=Op.DELETE_RECORD)
        with self.assertRaises(SafetyViolation):
            check_safety(d, foreign_only=True, proof_assertions=[])

    def test_operation_claim_never_cited(self):
        d = Decision("USER_PROFILE", "rule_01", COMPLIANT)
        with self.assertRaises(SafetyViolation):
            check_safety(d, foreign_only=False, proof_assertions=[OPERATION_CLAIM])

    def test_unknown_state_is_not_compliant(self):
        _, d, item = run([], system="account_service", rid="account_9")
        self.assertEqual((d.outcome, item.evidence_id), (UNPROVEN, ""))
        self.assertEqual(exists_rollup(run([])[0]), UNKNOWN)


if __name__ == "__main__":
    unittest.main()
