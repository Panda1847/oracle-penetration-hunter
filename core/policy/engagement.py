"""Signed engagement verification and local contract revocation."""
from __future__ import annotations
import base64, hashlib, hmac, json
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime, timezone
class EngagementError(ValueError): pass
@dataclass(frozen=True)
class Engagement:
    contract_id: str
    client: str
    scope: tuple[str, ...]
    max_profile: str
    issued_by: str
    expires_at: str
    signature: str = ""
class EngagementVerifier:
    def __init__(self, authority_public_key: str | bytes = "", revoked_contracts_path: str | Path | None = None, revoked_contract_ids=None):
        self.authority_public_key = authority_public_key.encode() if isinstance(authority_public_key, str) else authority_public_key
        self.revoked_contracts_path = Path(revoked_contracts_path) if revoked_contracts_path else None
        self.revoked_contract_ids = set(revoked_contract_ids or ())
        self.revoked_contract_ids.update(self._load_revocations())
    def _load_revocations(self):
        if not self.revoked_contracts_path or not self.revoked_contracts_path.exists(): return set()
        return {x.strip() for x in self.revoked_contracts_path.read_text(encoding="utf-8").splitlines() if x.strip() and not x.lstrip().startswith("#")}
    @staticmethod
    def _payload(contract):
        return {k: contract[k] for k in ("contract_id", "client", "scope", "max_profile", "issued_by", "expires_at") if k in contract}
    def verify(self, contract: dict, signature: str | None = None) -> Engagement:
        if not isinstance(contract, dict): raise EngagementError("engagement contract must be an object")
        contract_id = str(contract.get("contract_id", "")).strip()
        if not contract_id: raise EngagementError("engagement contract_id is required")
        if contract_id in self.revoked_contract_ids or contract_id in self._load_revocations(): raise EngagementError(f"engagement contract revoked: {contract_id}")
        expires = str(contract.get("expires_at", "")).strip()
        if not expires: raise EngagementError("engagement expires_at is required")
        try: expiry = datetime.fromisoformat(expires.replace("Z", "+00:00"))
        except ValueError as exc: raise EngagementError("engagement expires_at must be ISO-8601") from exc
        if expiry <= datetime.now(timezone.utc): raise EngagementError(f"engagement contract expired: {contract_id}")
        supplied = signature or contract.get("signature", "")
        if self.authority_public_key and supplied:
            material = json.dumps(self._payload(contract), sort_keys=True, separators=(",", ":")).encode()
            expected = base64.urlsafe_b64encode(hmac.new(self.authority_public_key, material, hashlib.sha256).digest()).decode().rstrip("=")
            if not hmac.compare_digest(str(supplied), expected): raise EngagementError("engagement signature invalid")
        elif self.authority_public_key: raise EngagementError("engagement signature required")
        scope = contract.get("scope", [])
        if not isinstance(scope, list) or not scope: raise EngagementError("engagement scope is required")
        return Engagement(contract_id, str(contract.get("client", "")), tuple(map(str, scope)), str(contract.get("max_profile", "normal")), str(contract.get("issued_by", "")), expires, str(supplied))
