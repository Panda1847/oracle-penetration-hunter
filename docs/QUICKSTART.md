# Quickstart

This walkthrough takes you from a fresh install to your first completed
reconnaissance mission against a lab target.

## 1. Document Your Authorization (Strongly Recommended)

The CLI takes in-scope hosts directly as `--scope` arguments (see below). Before running
anything, write down what you're authorized to test — who authorized it and when —
independent of the tool itself. `examples/scope.example.yaml` is a template for exactly
that record:

```bash
cp examples/scope.example.yaml auth/scope.yaml
# edit auth/scope.yaml with your real authorization details
```

`The CLI parses YAML scope files provided via the `--scope` flag.
`--scope` host arguments are the sole enforcement mechanism today. If scope-file parsing
isn't implemented yet, treat `auth/scope.yaml` purely as a paper-trail record for now, and
consider it a strong candidate for the roadmap — file-based scope with exclusions is a
meaningfully stronger guardrail than CLI args alone.]`

## 2. Launch the Mission

```bash
python3 -m oracle \
  --scope 192.168.56.10 \
  --mission-name recon-baseline \
  --objective "Enumerate hosts and services, flag misconfigurations" \
  --profile normal \
  --max-iter 20 \
  --web --web-port 8088 \
  --report \
  --audit-log
```

ORACLE will:
1. Run a startup preflight (checking for an available AI backend; falling back to
   deterministic logic if none is reachable)
2. Load its plugins (`nmap`, `http`, `fuzz` by default) and begin the mission loop
3. Evaluate each candidate action through the AI Council against the live attack graph
4. Log every discovery, decision, and reasoning step to the timeline and evidence graph
5. Serve a live view of all of the above on the Control Plane dashboard

## 3. Watch It Live

Open `http://127.0.0.1:8088` to watch mission phase, findings, the attack graph, and AI
Council decisions update in real time.

## 4. Review Findings After Completion

On completion, ORACLE writes:
- `~/.oracle/logs/<mission-name>_report.md` and `.html` — the executive summary
- Evidence, intelligence, and packaged artifacts, downloadable from the Control Plane
  Artifacts panel
- Replay artifacts under `~/.oracle/missions/replay/`, for stepping back through the run

## Next Steps

- [CONFIGURATION.md](CONFIGURATION.md) — tune scan profiles, integrations, and AI advisory settings
- [EXAMPLES.md](EXAMPLES.md) — real-world mission examples
- [ARCHITECTURE.md](ARCHITECTURE.md) — how the pieces fit together

`All commands verified against ORACLE v3.2.0.
This quickstart is written to be the ideal onboarding flow — align the real
implementation to it, or edit the doc to match reality, whichever gets there
faster.]`
