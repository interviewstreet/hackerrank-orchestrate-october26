from engine.identity_resolver import resolve_subject


def _req(ec, cid):
    return next(r for r in ec.ctx.sample_requests if r["case_id"] == cid)


def test_known_email_resolves_to_one_user(ec):
    r = _req(ec, "case_01")
    s = resolve_subject(ec.ctx, r["case_id"], r["email"], r["audit_at"])
    assert s.status == "RESOLVED" and s.user_id


def test_lookalike_email_is_not_merged_with_real_customer(ec):
    r = _req(ec, "case_01")
    s = resolve_subject(ec.ctx, r["case_id"], "amina.elmasri@gmai1.com", r["audit_at"])
    assert s.status == "UNRESOLVED" and not s.user_id


def test_email_case_and_whitespace_do_not_matter(ec):
    r = _req(ec, "case_15")
    a = resolve_subject(ec.ctx, r["case_id"], r["email"], r["audit_at"])
    b = resolve_subject(ec.ctx, r["case_id"], "  " + r["email"].upper() + " ", r["audit_at"])
    assert a.status == b.status == "RESOLVED" and a.user_id == b.user_id


def test_every_sample_email_resolves(ec):
    for r in ec.ctx.sample_requests:
        s = resolve_subject(ec.ctx, r["case_id"], r["email"], r["audit_at"])
        assert s.status == "RESOLVED", r["case_id"]
