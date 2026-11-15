# ORACLE key custody runbook

The engagement authority private key must never be present on a host that runs ORACLE. Only the public verification key (`authority.pub`) is deployed to ORACLE hosts. Keep the private key in an offline, access-controlled authority system.

## Rotation
1. Generate a new authority keypair in the authority system.
2. Publish the new `authority.pub` through approved configuration management.
3. Verify a test engagement with the new key before issuing production contracts.
4. Retire the old public key only after contracts signed by it have expired or been revoked.

## Revocation
Add the affected contract ID to the configured local revocation file, one ID per line, and restart/reload the verifier. The verifier rejects revoked contracts after signature and expiry validation. Preserve the revocation file as an audited change.
