"""Create a login token for one person who may draft, approve or send email.

    python code/email_operator_token.py --name Rachana                 # prints the token and the EMAIL_OPERATORS line
    python code/email_operator_token.py --name Rachana --env-file .env # also adds the line to your .env

The token is shown ONCE on your screen and is never saved anywhere; keep it in a password manager and type it into the
EraSight email screen. Only its SHA-256 hash goes into .env, so the file alone cannot be used to log in.
Run it again for the same name to replace that person's token. Standard library only.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from integrations.email.operators import (NAME_RE, OperatorConfigError, hash_token, new_token,  # noqa: E402
                                          upsert_operator_line)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--name", required=True, help="the person's name as it should appear in the audit trail")
    ap.add_argument("--env-file", help="path of the .env file to update (created if missing)")
    args = ap.parse_args()
    if not NAME_RE.match(args.name):
        print("Name must be 1-60 characters: letters, digits, space, dot, underscore or hyphen.")
        return 1
    token = new_token()
    digest = hash_token(token)
    if args.env_file:
        path = Path(args.env_file)
        try:
            text = path.read_text(encoding="utf-8") if path.exists() else ""
            path.write_text(upsert_operator_line(text, args.name, digest), encoding="utf-8", newline="")
        except (OSError, OperatorConfigError) as e:
            print(f"Could not update {path}: {e}")
            return 1
        print(f"Added {args.name} to EMAIL_OPERATORS in {path}.")
    else:
        print("Add this line to your .env (replace an existing EMAIL_OPERATORS line, or join the entries with commas):")
        print(f"EMAIL_OPERATORS={args.name}:{digest}")
    print()
    print(f"Login token for {args.name} (shown once, keep it private):")
    print(token)
    return 0


if __name__ == "__main__":
    sys.exit(main())
