# Configuration

ORACLE is configured through a combination of a global config file, per-mission
scope files, and environment variables for secrets.

## Global Config

Location: `~/.oracle/config.yaml` (created on first run via `oracle init`)

```yaml
ai_advisory:
  enabled: true
  provider: "anthropic"        # or your configured local/remote model provider
  max_tokens_per_analysis: 4000

reconnaissance:
  default_rate_limit: "moderate"   # low | moderate | aggressive
  passive_only_by_default: true

reporting:
  default_format: "html"
  include_evidence_graph: true

logging:
  level: "info"
  path: "~/.oracle/logs/"
```

## Scope

The current CLI takes in-scope hosts directly via the `--scope` flag (space-separated
IPs/hosts). The scope file described below is a **recommended authorization record**
alongside that — and a strong candidate for direct CLI/config integration on the
roadmap. See the `[TODO]` note in [QUICKSTART.md](QUICKSTART.md#1-document-your-authorization-strongly-recommended)
before treating it as an enforced mechanism today.

| Field | Required | Description |
|---|---|---|
| `engagement` | ✅ | Human-readable engagement name |
| `authorized_by` | ✅ | Name of person who authorized testing |
| `targets` | ✅ | List of in-scope hosts/ranges/ports |
| `exclusions` | Recommended | Explicitly excluded hosts (gateways, shared infra) |
| `notes` | Optional | Free-text context for the evidence report |

## Environment Variables

```bash
export ORACLE_AI_API_KEY="..."       # if using a remote AI advisory provider
export ORACLE_LOG_LEVEL="debug"
export ORACLE_MISSION_DIR="./missions"
```

**Never commit real API keys or scope files with production targets to
version control.** See `.gitignore` for what's already excluded.

## Integrations

ORACLE orchestrates existing tools rather than replacing them. Configure
tool paths in the global config:

```yaml
integrations:
  nmap_path: "/usr/bin/nmap"
  # add your own scanner/tool paths here
```

`Integration points include Anthropic Claude 3.5 Sonnet, local Ollama models (llama3.2), and CVE databases like NVD and Vulners.
this section should list every tool ORACLE can currently orchestrate.]`
