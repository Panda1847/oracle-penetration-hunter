# Contributing to ORACLE Penetration Hunter

First off — thanks for considering a contribution. ORACLE gets better because
red teamers and researchers bring in the edge cases a solo maintainer never
sees.

## Ways to Contribute

- 🐛 **Bug reports** — Use the [bug report template](.github/ISSUE_TEMPLATE/bug_report.md)
- 💡 **Feature requests** — Use the [feature request template](.github/ISSUE_TEMPLATE/feature_request.md)
- 🔧 **New reconnaissance / scanning modules** — See `oracle/reconnaissance/` and `oracle/scanning/` for the module interface
- 📖 **Documentation** — Docs live in `docs/`; typo fixes and clarity improvements are always welcome
- 🧪 **Tests** — See `tests/`; new modules should ship with test coverage

## Development Setup

```bash
git clone https://github.com/Panda1847/oracle-penetration-hunter.git
cd oracle-penetration-hunter
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt   # linting/test tooling
```

## Before You Submit a Pull Request

1. **Open an issue first** for anything non-trivial, so we can align on
   approach before you invest time.
2. **Write tests** for new functionality where applicable.
3. **Run the linter and test suite locally:**
   ```bash
   ruff check .
   pytest
   ```
4. **Keep PRs focused.** One feature or fix per PR is much easier to review
   and merge than a large batch of unrelated changes.
5. **Describe the "why," not just the "what,"** in your PR description.

## Module Contribution Guidelines

New reconnaissance, scanning, or reporting modules should:

- Respect the scope-enforcement layer in `oracle/core` — no module should
  bypass scope checks directly.
- Log findings into the evidence graph rather than printing directly to
  stdout only.
- Include a short module-level docstring describing what it does and any
  external dependencies (tools, API keys, etc.) it requires.

## Code of Conduct

This project follows the [Code of Conduct](CODE_OF_CONDUCT.md). Please read
it before participating.

## Questions?

Open a [Discussion](../../discussions) or an issue tagged `question`.
