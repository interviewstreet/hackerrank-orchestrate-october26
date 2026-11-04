import json

import pytest

from advisor.advisor import advise_case, advise_all
from advisor.explain import parse_and_validate, template_explanation
from advisor.llm_client import AnthropicClient, FakeClient, ModelUnavailable
from advisor.review import review_reasons
from engine.case_analyzer import analyze_case


def _req(ec, cid):
    return next(r for r in ec.ctx.sample_requests if r["case_id"] == cid)


def _lookalike(ec):
    r = dict(_req(ec, "case_01")); r["email"] = "amina.elmasri@gmai1.com"
    return r, analyze_case(r, ec)


def test_lookalike_identity_is_flagged_for_review(ec):
    r, res = _lookalike(ec)
    reasons = review_reasons(res, r, ec)
    assert any("UNRESOLVED" in x for x in reasons) and any("lookalike" in x for x in reasons)


def test_clear_cases_get_a_template_and_no_model_call(ec):
    client = FakeClient("{}")
    for r in ec.ctx.sample_requests[:10]:
        a = advise_case(analyze_case(r, ec), r, ec, client)
        assert a["source"] == "template" and a["explanation"]
    assert client.prompts == [] and client.usage.calls == 0


def test_model_advice_is_used_only_for_flagged_cases(ec):
    r, res = _lookalike(ec)
    client = FakeClient(json.dumps({"summary": "The address looks like a typo of a real customer; confirm identity before acting.",
                                    "review_needed": True, "review_reason": "possible lookalike"}))
    a = advise_case(res, r, ec, client)
    assert a["source"] == "model" and a["review_needed"] and client.usage.calls == 1
    assert res.deletion_status == "INCOMPLETE" and res.steps == []      # the model changed nothing


def test_model_cannot_invent_identifiers(ec):
    r = _req(ec, "case_26")
    res = analyze_case(r, ec)
    bad = json.dumps({"summary": "Also delete account_999999 per evidence_9999.", "review_needed": False, "review_reason": ""})
    assert parse_and_validate(bad, res) is None
    ok_id = res.steps[0]["resource_id"]
    good = json.dumps({"summary": f"{ok_id} was checked.", "review_needed": False, "review_reason": ""})
    assert parse_and_validate(good, res) is not None


@pytest.mark.parametrize("raw", ["not json", "{}", '{"summary": 5, "review_needed": true}', '{"summary": "x", "review_needed": "yes"}'])
def test_malformed_model_output_falls_back_to_template(ec, raw):
    r, res = _lookalike(ec)
    a = advise_case(res, r, ec, FakeClient(raw))
    assert a["source"] == "template" and a["model_note"]
    assert a["explanation"] == template_explanation(res)


def test_missing_key_means_template_only(ec, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    client = AnthropicClient()
    assert not client.available
    with pytest.raises(ModelUnavailable):
        client.complete("case_x", "s", "u")
    r, res = _lookalike(ec)
    assert advise_case(res, r, ec, client)["source"] == "template"


def test_call_limit_is_respected(ec):
    client = FakeClient(json.dumps({"summary": "ok", "review_needed": True, "review_reason": "r"}))
    reqs = []
    for i in range(3):
        r = dict(_req(ec, "case_01")); r["case_id"] = f"x{i}"; r["email"] = "amina.elmasri@gmai1.com"; reqs.append(r)
    out = advise_all(reqs, ec, client, limit=2)
    assert [a["source"] for a in out] == ["model", "model", "template"] and client.usage.calls == 2


def test_usage_log_counts_tokens(ec):
    r, res = _lookalike(ec)
    client = FakeClient(json.dumps({"summary": "ok", "review_needed": True, "review_reason": "r"}), tokens=(321, 45))
    advise_case(res, r, ec, client)
    u = client.usage.to_dict()
    assert u["calls"] == 1 and u["input_tokens"] == 321 and u["output_tokens"] == 45


def test_env_file_loads_without_overriding_real_variables(tmp_path, monkeypatch):
    from advisor.envfile import load_env
    f = tmp_path / ".env"
    f.write_text("# c\nANTHROPIC_API_KEY=abc\nEMPTY=\nKEEP=fromfile\n", encoding="utf-8")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("KEEP", "fromshell")
    monkeypatch.delenv("EMPTY", raising=False)
    assert load_env(f) == 1
    import os
    assert os.environ["ANTHROPIC_API_KEY"] == "abc" and os.environ["KEEP"] == "fromshell" and "EMPTY" not in os.environ
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
