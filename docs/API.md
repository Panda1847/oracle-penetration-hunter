# API Reference

ORACLE can be used as a CLI tool or imported as a Python library for custom
automation.

## CLI Usage (Current)

ORACLE's current interface is a single flag-based invocation rather than subcommands:

```bash
python3 -m oracle \
  --scope <host> [<host> ...] \
  --mission-name <name> \
  --objective "<free-text mission objective>" \
  --profile normal \
  --max-iter <n> \
  --web --web-port 8088 \
  --report \
  --audit-log
```

| Flag | Description |
|---|---|
| `--scope` | One or more in-scope hosts/IPs for this mission |
| `--mission-name` | Human-readable identifier for this run |
| `--objective` | Free-text description of what the mission should accomplish |
| `--profile` | Execution profile (e.g. `normal`) controlling pacing/aggressiveness |
| `--max-iter` | Maximum planner iterations before the mission stops |
| `--web` / `--web-port` | Enable the live Control Plane dashboard on the given port |
| `--report` | Generate the Markdown + HTML executive summary on completion |
| `--audit-log` | Write a full audit log of mission actions and decisions |

Run `python3 -m oracle --help` for the complete, authoritative flag list.

`[TODO: A subcommand-style interface (`oracle mission start`, `oracle scope add`,
`oracle report generate`, etc.) would likely be a friendlier UX for new users than a
single long flag invocation — worth considering for the roadmap. Until then, keep this
doc in sync with the real flags in your argument parser.]`

## Python API

```python
from oracle.core.mission import Mission
from oracle.core.scope import Scope

scope = Scope.from_file("auth/scope.yaml")
mission = Mission(name="recon-baseline", scope=scope)

mission.add_module("reconnaissance.passive_dns")
mission.add_module("scanning.service_scan")

results = mission.run()
print(results.evidence_graph.summary())
```

## Extending ORACLE

To add a custom module, implement the `OracleModule` interface (see
[ARCHITECTURE.md](ARCHITECTURE.md#module-interface)) and register it:

```python
from oracle.core.registry import register_module

@register_module("reconnaissance.my_custom_recon")
class MyCustomRecon:
    name = "my_custom_recon"
    requires = []

    def run(self, target, context):
        ...
        return findings
```

`This API reference describes the core interfaces for plugins and the internal engine.
experience. Validate every function signature against your actual codebase
before publishing — inaccurate API docs erode trust faster than no docs at
all.]`
