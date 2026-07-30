# FAQ

**Is ORACLE a replacement for Metasploit / Burp Suite / Nmap?**
No — ORACLE orchestrates and augments your existing toolchain rather than
replacing it. It handles mission state, scope enforcement, evidence
tracking, and AI-assisted triage around the tools you already trust.

**Is it legal to use ORACLE?**
ORACLE itself is legal open-source software. Whether *your use* of it is
legal depends entirely on whether you have explicit authorization to test
the target. See [Responsible Use](../README.md#-responsible-use) and
[SECURITY.md](../SECURITY.md).

**Does the AI advisory layer take actions automatically?**
No. The advisory layer only surfaces suggestions and triage notes based on
the evidence graph. Every action that touches a target requires operator
initiation and passes through the scope guard.

**Can I use ORACLE without an internet connection / cloud AI provider?**
`Yes, ORACLE supports local models via Ollama. Set `advisor.backend: ollama` in your config.
if you do, this is a strong selling point worth expanding on, given your
lab-first / local AI integration setup.]`

**What platforms are supported?**
Primary development and testing target is Kali Linux. It should run on any
modern Linux distribution or macOS with Python 3.11+. Windows support is
`Currently in Beta v3.2.0.`.

**How is this different from just writing my own scripts?**
Scope enforcement and the evidence graph are the core value — most
homegrown recon scripts don't track findings in a structured, reproducible
way, which makes reporting slow and error-prone. ORACLE gives you that
structure without giving up the flexibility of your own tooling underneath.

**I found a bug. Where do I report it?**
Open an issue using the [bug report template](../.github/ISSUE_TEMPLATE/bug_report.md).
For security vulnerabilities in ORACLE itself, see [SECURITY.md](../SECURITY.md).

**Can I contribute a new module?**
Yes — see [CONTRIBUTING.md](../CONTRIBUTING.md#module-contribution-guidelines).
