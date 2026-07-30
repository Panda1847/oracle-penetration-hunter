# Security Policy

## Intended Use

ORACLE Penetration Hunter is designed **exclusively** for:

- Penetration testing engagements conducted under signed authorization and a
  defined rules-of-engagement / scope document
- Internal red team operations within your own organization
- Security research in isolated lab environments that you own or control
- CTF competitions and other environments where testing is explicitly permitted

**Do not** run ORACLE against any system, network, or application without
explicit, written authorization from the system owner. Unauthorized scanning,
exploitation, or reconnaissance against systems you do not own or have
permission to test may violate the Computer Fraud and Abuse Act (US), the
Computer Misuse Act (UK), or equivalent laws in your jurisdiction.

## Supported Versions

| Version | Supported |
|---|---|
| 4.x | ✅ |
| < 4.0 | ❌ |

## Reporting a Vulnerability in ORACLE Itself

If you discover a security vulnerability **in the ORACLE codebase** (e.g. a
flaw that would let ORACLE's scope enforcement be bypassed, credential
handling issues, insecure defaults, dependency vulnerabilities, etc.), please
report it responsibly:

1. **Do not** open a public GitHub issue for security vulnerabilities.
2. Email the maintainer directly at: `security@panda1847.com
   GitHub's private vulnerability reporting feature under the Security tab]`
3. Include a clear description, reproduction steps, and potential impact.
4. Allow a reasonable window for a fix before any public disclosure
   (we aim to acknowledge reports within 5 business days).

We'll credit responsible disclosures in the project's release notes unless
you'd prefer to remain anonymous.

## Scope Enforcement Design Note

ORACLE's scope-guard is a **defense-in-depth control**, not a substitute for
operator judgment or written authorization. Always verify your rules of
engagement independently before running any mission.
