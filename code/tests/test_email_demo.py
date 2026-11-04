"""The demo script: approval prompt, rejection, missing settings, dry run. Resend is always faked."""
import socket

import pytest

import email_demo
from emailkit import FakeResend


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def refuse(*a, **k):
        raise AssertionError("a test tried to open a real network connection")
    monkeypatch.setattr(socket.socket, "connect", refuse)


ENV = {"RESEND_API_KEY": "re_fake", "RESEND_FROM_EMAIL": "onboarding@resend.dev"}


def run(argv, answers, env=ENV, transport=None):
    it = iter(answers)
    return email_demo.main(argv, input_fn=lambda prompt: next(it), env=env, transport=transport)


def test_typing_a_name_approves_and_sends_once(capsys):
    fake = FakeResend()
    assert run(["--to", "Me@Example.test"], ["Rachana"], transport=fake) == 0
    assert len(fake.calls) == 1 and fake.calls[0]["json"]["to"] == ["me@example.test"]
    assert fake.calls[0]["json"]["from"] == "onboarding@resend.dev"
    assert "State: SENT" in capsys.readouterr().out


def test_blank_answer_rejects_and_sends_nothing(capsys):
    fake = FakeResend()
    assert run(["--to", "me@example.test"], [""], transport=fake) == 1
    assert fake.calls == [] and "Nothing was sent" in capsys.readouterr().out


def test_missing_settings_explains_what_to_set(capsys):
    fake = FakeResend()
    assert run(["--to", "me@example.test"], [], env={}, transport=fake) == 2
    assert fake.calls == [] and "RESEND_API_KEY" in capsys.readouterr().out


def test_resend_refusal_is_shown_not_hidden(capsys):
    fake = FakeResend([(403, {"name": "validation_error", "message": "You can only send testing emails to your own email address"})])
    assert run(["--to", "other@example.test"], ["Rachana"], transport=fake) == 1
    assert "own email address" in capsys.readouterr().out


def test_prompts_for_recipient_and_rejects_bad_address(capsys):
    assert run([], ["not-an-email"], transport=FakeResend()) == 2


def test_dry_run_needs_no_credentials_and_sends_nothing_real(capsys):
    assert run(["--to", "me@example.test", "--dry-run"], ["Rachana"], env={}) == 0
    out = capsys.readouterr().out
    assert "[dry run]" in out and "nothing was sent" in out
