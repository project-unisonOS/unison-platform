# Adaptive maintenance

The adaptive-maintenance implementation provides dependency-free analysis,
discovery, calibration, and narrowly bounded execution boundaries.

It can:

- collect a redacted device profile and content-free operational indicators;
- classify initial CPU, memory, storage, service, backup, and model health;
- normalize evidence only from a versioned source registry;
- map authoritative advisories to exact installed component versions;
- ignore community discovery content when constructing the exposure graph;
- rank security, software, capacity, and compatible hardware recommendations;
- forecast storage exhaustion from an explicitly supplied local aggregate;
- prefer software and configuration alternatives before hardware purchases; and
- write an allowlisted System wellbeing projection for the renderer.

The default policy is Recommend. AM-4 execution is available only through the
separately privileged Appliance Lifecycle boundary and an exact, revocable
grant. It enforces a maintenance window, budgets, signed artifacts, checkpoints,
health gates, receipts, circuit breakers, and rollback. Community content is
restricted to test proposals and can never authorize an action.

Full-stack eligibility covers OS packages, containers, drivers, model runtimes,
models, capabilities, and data/configuration. Firmware remains blocked until
vendor recovery passes on the exact physical hardware. Pilot promotion also
remains blocked until the physical matrix, real opt-in pilot, and human
promotion gates pass.

See [adaptive-maintenance-operations.md](adaptive-maintenance-operations.md)
for the support boundary and incident procedures.

## Integrated maintenance cycle

`maintenance.lifecycle.MaintenanceLifecycle` is the persistent authority bridge
to the Phase 9 update transaction. It checks the exact grant before Lifecycle
creates its checkpoint, verifies and stages the signed bundle, activates the
candidate, applies bounded health checks, and promotes or restores the
last-known-good release. Maintenance records the resulting Phase 9 state in a
separate receipt.

`maintenance.state.MaintenanceState` preserves grants, owner decisions, action
budgets, recommendation deferrals, receipts, source runs, cooldowns, and
circuit breakers with atomic mode-0600 writes. Restarting the service does not
reset any authority or safety budget.

System wellbeing queues authenticated owner grant, revoke, defer, and cancel
decisions into a local mode-0600 command directory. The maintenance service
validates them independently. A renderer request cannot invoke Lifecycle.

The supported bundle includes the maintenance modules, one-shot service,
systemd timer, service hardening profile, and source registry. The registry is
signed during bundle assembly with the release Ed25519 key. Runtime collection
fails closed if its signature changes.

The initial read-only schedule covers Unison releases, Ubuntu security notices,
GitHub reviewed advisories, and Hacker News new-story identifiers. Hacker News
is discovery-only. Collectors enforce HTTPS, signed host allowlists, redirect
checks, byte limits, JSON parsing, content hashes, and mode-0600 snapshots.

Run the deterministic acceptance suite:

```bash
python3 scripts/test_adaptive_maintenance.py
python3 scripts/test_adaptive_maintenance_operations.py
python3 scripts/test_adaptive_maintenance_integration.py
```

Inspect the current host without collecting personal content:

```bash
python3 scripts/unison-maintenance.py
```

Evaluate a synthetic scenario and write the renderer projection:

```bash
python3 scripts/unison-maintenance.py \
  --scenario scenario.json \
  --wellbeing-out wellbeing.json
```
