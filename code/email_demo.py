"""Send ONE demo email through the real approval workflow, from your terminal.

    python code/email_demo.py --to you@example.com            # real send (needs RESEND_API_KEY + RESEND_FROM_EMAIL)
    python code/email_demo.py --to you@example.com --dry-run  # same steps, no network, nothing is sent

It reads .env from the repo root (real environment variables win), uses a throwaway database, shows you the draft,
and sends only if you type your name to approve it.
With the free sender onboarding@resend.dev, Resend delivers only to the email address your Resend account uses.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Mapping, Optional

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from advisor.envfile import load_env                                    # noqa: E402
from integrations.email import (EmailConfig, EmailService, EmailStore, ResendClient,  # noqa: E402
                                ResendError)
from integrations.email.models import normalize_recipient              # noqa: E402

BODY = ("Hello,\n\nThis is a demo email from ERASIGHT, the deletion-audit assistant.\n\n"
        "It was drafted, approved by a named person, and sent through the approval workflow. "
        "If you can read this, the Resend integration works.\n\nRegards,\nERASIGHT demo")


def _dry_transport(method, url, headers, body, timeout):
    payload = json.loads(body)
    print("\n[dry run] would POST to Resend:")
    print(f"  from: {payload['from']}\n  to: {payload['to']}\n  subject: {payload['subject']}")
    print(f"  Idempotency-Key: {headers['Idempotency-Key']}")
    return 200, b'{"id":"dry_run_no_email_sent"}'


def main(argv=None, *, input_fn: Callable[[str], str] = input, env: Optional[Mapping[str, str]] = None,
         transport=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--to", help="recipient (with the free sender: your own Resend account email)")
    ap.add_argument("--dry-run", action="store_true", help="do everything except contact Resend")
    a = ap.parse_args(argv)

    if env is None:
        load_env(HERE.parent / ".env")
    cfg = EmailConfig.from_env(env)
    if a.dry_run:
        cfg = EmailConfig(api_key=cfg.api_key or "dry-run", from_email=cfg.from_email or "onboarding@resend.dev",
                          webhook_secret=cfg.webhook_secret, db_path=":memory:")
        transport = transport or _dry_transport
    elif not cfg.can_send:
        print("Missing settings. Put these in .env (repo root) or your environment:\n"
              "  RESEND_API_KEY=re_...\n  RESEND_FROM_EMAIL=onboarding@resend.dev\n"
              "Or run with --dry-run to see the flow without sending.")
        return 2

    try:
        to = normalize_recipient(a.to or input_fn("Send the demo email to which address? "))
    except ValueError as e:
        print(f"Invalid recipient: {e}")
        return 2
    if "resend.dev" in cfg.from_email.lower() and not a.dry_run:
        print("Note: with the free sender, Resend only delivers to the email address of your Resend account.")

    tmp = tempfile.TemporaryDirectory()
    store = EmailStore(":memory:" if a.dry_run else str(Path(tmp.name) / "demo_outbox.db"))
    svc = EmailService(store, ResendClient(cfg.api_key, cfg.from_email, transport=transport), cfg)
    try:
        case_id = "demo_" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")       # new key each run: Resend dedupes by key
        rec, _ = svc.create_draft(case_id, to, "ERASIGHT demo email", BODY, actor="demo-script")
        svc.submit_for_approval(rec.id, "demo-script")
        print(f"\nDRAFT  from: {cfg.from_email}\n       to: {to}\n  subject: {rec.subject}\n\n{rec.body_text}\n")
        who = input_fn("Type your name to APPROVE and send (press Enter to reject): ").strip()
        if not who:
            svc.reject(rec.id, "demo-script", "rejected at the prompt")
            print("Rejected. Nothing was sent.")
            return 1
        svc.approve(rec.id, who)
        out = svc.send(rec.id, who)
        print(f"\nState: {out.state}")
        if out.state == "SENT":
            print(f"Resend email id: {out.resend_id}" + ("  (dry run, nothing was sent)" if a.dry_run else
                  "\nCheck the inbox (and spam) of " + to))
            return 0
        print(f"Send failed: {out.last_error}")
        return 1
    except ResendError as e:
        print(f"Resend error: {e}")
        return 1
    finally:
        store.close()
        tmp.cleanup()


if __name__ == "__main__":
    raise SystemExit(main())
