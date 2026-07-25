# Adaptive maintenance

The AM-0 through AM-3 implementation provides a dependency-free,
non-privileged maintenance analysis boundary.

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

It cannot install, restart, patch, purchase, or change the appliance. Execution
belongs to the separately privileged Appliance Lifecycle boundary and is planned
for AM-4. The default policy is Recommend. Authoritative evidence must arrive
with verified source authentication; the development registry itself must be
signed before a product profile can consume it.

Run the deterministic acceptance suite:

```bash
python3 scripts/test_adaptive_maintenance.py
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
