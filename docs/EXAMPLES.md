# Examples

Real-world(ish) mission configurations to get you moving faster. Adapt these
to your actual lab environment and scope — never point them at anything you
don't have explicit authorization to test.

## Example 1 — Internal Lab Recon Baseline

```yaml
# examples/scope.example.yaml
engagement: "lab-baseline"
authorized_by: "Michael Lastovich"
authorization_date: "2026-07-29"
targets:
  - host: "192.168.56.0/24"
    ports: "1-1024"
exclusions:
  - "192.168.56.1"
notes: "Isolated VirtualBox host-only network. No external routing."
```

```bash
oracle scope add --file examples/scope.example.yaml
oracle mission start --name recon-baseline --scope lab-baseline --modules recon
```

## Example 2 — Web Application Scan (Lab Target)

```bash
oracle mission start \
  --name webapp-scan \
  --scope lab-baseline \
  --modules recon,scan \
  --target-type webapp \
  --rate-limit moderate
```

## Example 3 — Full Chain with AI Advisory

```bash
oracle mission start \
  --name full-chain-demo \
  --scope lab-baseline \
  --modules recon,scan,exploitation \
  --ai-advisory on \
  --require-approval  # operator approves each exploitation step
```

## Example 4 — Report from a Completed Mission

```bash
oracle report generate \
  --mission recon-baseline \
  --format html \
  --out reports/recon-baseline.html
```

`Example: `oracle --mission internal-audit --scope examples/scope.example.yaml --debug`
copy-pasteable examples run against your actual ESP32/Kali lab setup —
concrete, specific examples like "here's ORACLE finding a misconfigured
service on my S25 Ultra's ADB lab rig" are what make a security README
memorable rather than generic.]`
