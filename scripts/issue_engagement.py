#!/usr/bin/env python3
"""Author and sign an EngagementRecord. Run this OFFLINE, away from any
machine that runs the ORACLE agent/worker fleet.

The private key this produces/uses must never live next to a running
ORACLE deployment. If both live on the same box, the "runtime can't forge
its own authorization" guarantee is gone in practice even though the code
still enforces it in theory — the property this whole feature exists for
depends on operational custody of the key, not just the crypto.

Usage
-----
  # One-time: generate the authority keypair. Keep authority.key offline
  # (ops/legal custody, hardware token, secrets manager your ORACLE hosts
  # cannot read). Ship authority.pub to every ORACLE deployment.
    python3 scripts/issue_engagement.py genkey \\
        --out-private authority.key --out-public authority.pub

  # Per engagement: issue and sign a contract-backed scope.
    python3 scripts/issue_engagement.py issue \\
        --private-key authority.key \\
        --contract-id CONTRACT-2026-0142 \\
        --client "Acme Corp" \\
        --scope 192.168.56.0/24 --scope 10.20.0.0/16 \\
        --hours 8 \\
        --issued-by "ops-lead@yourco.example" \\
        --max-profile normal \\
        --out engagement_acme_0142.json
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from security.engagement import EngagementRecord, generate_authority_keypair, sign_engagement


def cmd_genkey(args):
    private_pem, public_pem = generate_authority_keypair()
    Path(args.out_private).write_bytes(private_pem)
    Path(args.out_private).chmod(0o600)
    Path(args.out_public).write_bytes(public_pem)
    print(f"Private key written to {args.out_private} (chmod 600) — keep this OFFLINE.")
    print(f"Public key written to {args.out_public} — this is what ORACLE deployments trust.")


def cmd_issue(args):
    private_key_pem = Path(args.private_key).read_bytes()
    now = time.time()
    not_before = now if args.not_before is None else args.not_before
    not_after = not_before + args.hours * 3600 if args.not_after is None else args.not_after

    record = EngagementRecord(
        contract_id=args.contract_id,
        client=args.client,
        authorized_scope=args.scope,
        not_before=not_before,
        not_after=not_after,
        issued_by=args.issued_by,
        max_profile=args.max_profile,
        notes=args.notes or "",
    )
    artifact = sign_engagement(record, private_key_pem)
    out_path = Path(args.out)
    out_path.write_text(json.dumps(artifact, indent=2, sort_keys=True), encoding="utf-8")
    print(f"Signed engagement written to {out_path}")
    print(f"  contract_id : {record.contract_id}")
    print(f"  client      : {record.client}")
    print(f"  scope       : {', '.join(record.authorized_scope)}")
    print(f"  window      : {time.ctime(not_before)}  ->  {time.ctime(not_after)}")
    print(f"  max_profile : {record.max_profile}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p_genkey = sub.add_parser("genkey", help="Generate a new authority Ed25519 keypair")
    p_genkey.add_argument("--out-private", required=True, metavar="PATH")
    p_genkey.add_argument("--out-public", required=True, metavar="PATH")
    p_genkey.set_defaults(func=cmd_genkey)

    p_issue = sub.add_parser("issue", help="Author and sign a new engagement record")
    p_issue.add_argument("--private-key", required=True, metavar="PATH")
    p_issue.add_argument("--contract-id", required=True)
    p_issue.add_argument("--client", required=True)
    p_issue.add_argument("--scope", action="append", required=True, metavar="CIDR_OR_HOST",
                          help="Repeatable — pass once per authorized target/range")
    p_issue.add_argument("--hours", type=float, default=8.0, help="Engagement duration from not-before (default: 8)")
    p_issue.add_argument("--not-before", type=float, default=None, help="Unix timestamp override (default: now)")
    p_issue.add_argument("--not-after", type=float, default=None, help="Unix timestamp override (default: not-before + hours)")
    p_issue.add_argument("--issued-by", required=True, help="Identity of the authorizing party")
    p_issue.add_argument("--max-profile", choices=["stealth", "normal", "aggressive"], default="normal")
    p_issue.add_argument("--notes", default="")
    p_issue.add_argument("--out", required=True, metavar="PATH")
    p_issue.set_defaults(func=cmd_issue)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
