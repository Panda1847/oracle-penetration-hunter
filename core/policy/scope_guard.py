"""Contract-gated scope guard wrapper.

A Mission's live-target scope may only come from one of two places:

  1. A verified, unexpired EngagementRecord (security/engagement.py),
     produced by ScopeGuard.from_engagement(). This is the only path for
     real/live targets and is what makes the audit chain's "we never ran
     outside what was contracted" claim actually true, not just asserted.

  2. An explicit, opt-in, loopback-only path (ScopeGuard.for_lab()), for
     local lab use where there is no contract to check against by definition.

The old bare `ScopeGuard(scope)` constructor is intentionally removed, not
deprecated — a silent free-text scope path defeats the entire point of this
module, and "still works but shouldn't be used" is exactly the kind of gap
that gets used by accident under deadline pressure.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from oracle.runtime.safety import SafetyValidator
from security.engagement import EngagementError, EngagementRecord, EngagementVerifier

_LOOPBACK_SCOPE = ["localhost", "127.0.0.1", "::1"]


class ScopeGuard:
    """Compatibility wrapper around the existing safety validator, now
    contract-gated: construct via from_engagement() or for_lab(), not
    directly.
    """

    def __init__(
        self,
        scope: list[str],
        *,
        strict: bool = True,
        engagement: EngagementRecord | None = None,
        _authorized: bool = False,
    ):
        if not _authorized:
            raise EngagementError(
                "ScopeGuard cannot be constructed directly with a raw scope list — "
                "use ScopeGuard.from_engagement(...) for live targets or "
                "ScopeGuard.for_lab() for loopback-only use. This is enforced in "
                "code, not just by convention: a free-text scope path defeats the "
                "auditable-authorization guarantee this class exists to provide."
            )
        # strict=True (default) fails closed when scope is empty; pass
        # strict=False only for deliberate, explicitly-unrestricted tooling.
        self.validator = SafetyValidator(scope, strict=strict)
        self.engagement = engagement

    @classmethod
    def from_engagement(
        cls,
        artifact: dict[str, Any] | str | Path,
        *,
        verifier: EngagementVerifier,
        requested_profile: str = "normal",
    ) -> "ScopeGuard":
        """The only supported path to a live-target ScopeGuard.

        `artifact` is either the parsed signed-engagement dict, or a path
        to one on disk. Raises EngagementError (not a bool, not None) on
        any expired/unsigned/malformed/mismatched-profile engagement, so a
        caller can't accidentally proceed past a failed check.
        """
        if isinstance(artifact, (str, Path)):
            record = verifier.verify_file(artifact)
        else:
            record = verifier.verify(artifact)

        _PROFILE_CEILING = {"stealth": 0, "normal": 1, "aggressive": 2}
        allowed = _PROFILE_CEILING.get(record.max_profile, 1)
        requested = _PROFILE_CEILING.get(requested_profile, 1)
        if requested > allowed:
            raise EngagementError(
                f"mission profile {requested_profile!r} exceeds the profile "
                f"authorized by contract {record.contract_id!r} "
                f"(ceiling: {record.max_profile!r})"
            )

        return cls(record.authorized_scope, strict=True, engagement=record, _authorized=True)

    @classmethod
    def for_lab(cls) -> "ScopeGuard":
        """Explicit, loopback-only, no-contract-required scope for local
        lab/demo use. Cannot be pointed at a live target — construction
        always pins scope to loopback regardless of what's passed in.
        """
        return cls(list(_LOOPBACK_SCOPE), strict=True, engagement=None, _authorized=True)

    def validate(self, action, command: str):
        return self.validator.validate(action, command)

    def in_scope(self, target: str) -> bool:
        return self.validator.in_scope(target)

    def scope_summary(self) -> str:
        return self.validator.scope_summary()

    def engagement_summary(self) -> str:
        if self.engagement is None:
            return "no engagement on file (lab/loopback-only mode)"
        rec = self.engagement
        return (
            f"contract {rec.contract_id} — client {rec.client!r} — "
            f"authorized {rec.not_before:.0f}..{rec.not_after:.0f} — "
            f"issued_by {rec.issued_by!r} — max_profile {rec.max_profile}"
        )
