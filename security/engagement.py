"""Signed engagement records — the contract-gating layer in front of ScopeGuard.

Design intent
-------------
A Mission's `scope` must never be operator-typed free text for anything but
loopback/lab targets. For any real engagement, scope is *derived* from a
signed EngagementRecord: a small, canonical document (client, contract id,
authorized targets, start/end window) signed with an Ed25519 private key
that lives outside the ORACLE runtime entirely (ops/legal custody, a
hardware key, whatever your process requires — this module doesn't care).

ORACLE only ever holds the *public* key. That asymmetry is the whole point:
the runtime that executes the mission must be structurally unable to also
be the runtime that authorizes it. A shared-secret (HMAC) scheme fails this
property, since whoever can verify can also forge — which is why this does
not reuse security/signer.py's CommandSigner.

Nothing here executes anything. This module answers exactly one question:
"is there a currently-valid, signed authorization for this scope, issued by
someone who holds the authority key?" Everything downstream (ScopeGuard,
the policy engine, the audit chain) is unchanged and still enforces target
matching the way it always has — this just changes *where the scope list is
allowed to come from*.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
    load_pem_private_key,
    load_pem_public_key,
)


class EngagementError(Exception):
    """Raised for any invalid, expired, or unsigned engagement record."""


@dataclass(frozen=True)
class EngagementRecord:
    """The canonical, signable payload. Immutable by construction."""

    contract_id: str
    client: str
    authorized_scope: list[str]
    not_before: float
    not_after: float
    issued_by: str
    max_profile: str = "normal"  # ceiling on mission.profile: stealth|normal|aggressive
    notes: str = ""
    issued_at: float = field(default_factory=lambda: time.time())

    def canonical_bytes(self) -> bytes:
        # Sort keys, fixed separators: signature must be stable regardless
        # of dict ordering or whitespace.
        payload = {
            "contract_id": self.contract_id,
            "client": self.client,
            "authorized_scope": sorted(self.authorized_scope),
            "not_before": self.not_before,
            "not_after": self.not_after,
            "issued_by": self.issued_by,
            "max_profile": self.max_profile,
            "notes": self.notes,
            "issued_at": self.issued_at,
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")

    def is_active(self, *, now: float | None = None) -> bool:
        now = time.time() if now is None else now
        return self.not_before <= now <= self.not_after

    def to_dict(self) -> dict[str, Any]:
        return json.loads(self.canonical_bytes())


# ── Authoring side (lives OUTSIDE the ORACLE runtime in practice) ──────────

def generate_authority_keypair() -> tuple[bytes, bytes]:
    """Generate a new Ed25519 keypair for signing engagements.

    Returns (private_pem, public_pem). The private key must never be stored
    anywhere the ORACLE runtime itself reads from — treat it like a code
    signing key: ops/legal custody, a hardware token, or a separate signing
    service. Only the public key belongs in ORACLE's config.
    """
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    private_pem = private_key.private_bytes(
        Encoding.PEM, PrivateFormat.PKCS8, NoEncryption()
    )
    public_pem = public_key.public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)
    return private_pem, public_pem


def sign_engagement(record: EngagementRecord, private_key_pem: bytes) -> dict[str, Any]:
    """Produce a signed, transportable engagement artifact (JSON-able dict).

    Run this from a separate, offline authoring tool/process — not from
    anything the ORACLE runtime imports at execution time.
    """
    private_key = load_pem_private_key(private_key_pem, password=None)
    if not isinstance(private_key, Ed25519PrivateKey):
        raise EngagementError("engagement signing requires an Ed25519 private key")
    signature = private_key.sign(record.canonical_bytes())
    return {
        "record": record.to_dict(),
        "signature": signature.hex(),
    }


# ── Verification side (this is what the ORACLE runtime actually imports) ──

class EngagementVerifier:
    """Verifies signed engagement artifacts against a trusted public key.

    Holds only a public key. Cannot sign, cannot forge, cannot mint new
    valid engagements under any code path — by construction, not by policy.
    """

    def __init__(
        self,
        public_key_pem: bytes,
        *,
        revoked_contract_ids: "set[str] | frozenset[str] | None" = None,
    ):
        key = load_pem_public_key(public_key_pem)
        if not isinstance(key, Ed25519PublicKey):
            raise EngagementError("engagement verification requires an Ed25519 public key")
        self._public_key = key
        self._revoked = frozenset(revoked_contract_ids or ())

    @classmethod
    def from_file(
        cls,
        path: str | Path,
        *,
        revocation_file: str | Path | None = None,
    ) -> "EngagementVerifier":
        revoked = load_revoked_contract_ids(revocation_file) if revocation_file else frozenset()
        return cls(Path(path).read_bytes(), revoked_contract_ids=revoked)

    def verify(self, artifact: dict[str, Any]) -> EngagementRecord:
        """Verify signature + validity window. Raises EngagementError on any failure.

        This is deliberately fail-closed: any structural problem, expired
        window, or bad signature raises rather than returning a boolean, so
        a caller can't accidentally `if verify(...):` past a truthy
        exception object or otherwise treat "unverified" as "verified".
        """
        try:
            raw_record = artifact["record"]
            signature_hex = artifact["signature"]
        except (KeyError, TypeError) as exc:
            raise EngagementError(f"malformed engagement artifact: {exc}") from exc

        try:
            record = EngagementRecord(
                contract_id=raw_record["contract_id"],
                client=raw_record["client"],
                authorized_scope=list(raw_record["authorized_scope"]),
                not_before=float(raw_record["not_before"]),
                not_after=float(raw_record["not_after"]),
                issued_by=raw_record["issued_by"],
                max_profile=raw_record.get("max_profile", "normal"),
                notes=raw_record.get("notes", ""),
                issued_at=float(raw_record.get("issued_at", 0.0)),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise EngagementError(f"malformed engagement record: {exc}") from exc

        try:
            signature = bytes.fromhex(signature_hex)
        except ValueError as exc:
            raise EngagementError(f"malformed signature encoding: {exc}") from exc

        try:
            self._public_key.verify(signature, record.canonical_bytes())
        except InvalidSignature as exc:
            raise EngagementError(
                f"signature verification failed for contract {record.contract_id!r} "
                "— record does not match a signature issued by the trusted authority key"
            ) from exc

        # Revocation is checked last so a revoked-but-otherwise-valid
        # contract is rejected with a specific, auditable reason.
        if record.contract_id in self._revoked:
            raise EngagementError(
                f"engagement {record.contract_id!r} has been revoked by the authority"
            )

        if not record.is_active():
            now = time.time()
            if now < record.not_before:
                raise EngagementError(
                    f"engagement {record.contract_id!r} is not yet active "
                    f"(starts {record.not_before}, now {now})"
                )
            raise EngagementError(
                f"engagement {record.contract_id!r} has expired "
                f"(ended {record.not_after}, now {now})"
            )

        return record

    def verify_file(self, path: str | Path) -> EngagementRecord:
        artifact = json.loads(Path(path).read_text(encoding="utf-8"))
        return self.verify(artifact)


def load_revoked_contract_ids(path: str | Path) -> frozenset[str]:
    """Read a revocation list: one contract_id per line, '#' comments allowed.

    A missing file means no revocations. An unreadable file raises
    EngagementError, so a broken revocation list fails closed instead of
    silently allowing revoked contracts through.
    """
    p = Path(path)
    if not p.exists():
        return frozenset()
    try:
        text = p.read_text(encoding="utf-8")
    except OSError as exc:
        raise EngagementError(f"cannot read revocation list {str(p)!r}: {exc}") from exc
    ids = set()
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if line:
            ids.add(line)
    return frozenset(ids)
