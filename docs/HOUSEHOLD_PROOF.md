# Two-assistant household proof profile

This is a bounded engineering proof for two independently consenting adults on
one Ubuntu 24.04 x86_64 appliance. It is not a child, dependent, caregiving,
incapacity, or emergency-access model.

Start the representative profile from the appliance checkout:

```bash
docker compose \
  -f compose/compose.yaml \
  -f compose/household-proof.yaml \
  up -d
```

The profile retains one multi-principal core and applies hard per-assistant
queue/concurrency budgets. It does not create one container per person. Auth,
context, storage, and audit persistence remain appliance-local. The synthetic
enrollment and validation commands live in the `unison-workspace` Phase 4
runbook so no real household data is required.

Stop the proof without deleting its evidence volumes:

```bash
docker compose \
  -f compose/compose.yaml \
  -f compose/household-proof.yaml \
  down
```

