# UnisonOS Model Packs (Alpha)

UnisonOS alpha releases keep base artifacts lean and distribute large model weights separately as **Model Packs**.

## Why model packs

- Keeps WSL/VM/ISO artifacts to a reasonable size.
- Supports offline/edge evaluation (packs can be downloaded once and copied via USB).
- Provides a stable, auditable “what models are installed” contract via `models.manifest.json`.

## Mechanism (Alpha 0.5.0)

Alpha `0.5.0` uses the existing **Model Pack** mechanism from `unison-common`:

- A model pack is a `.tgz` containing:
  - `models.manifest.json` (validated JSON schema + checksums)
  - payload files laid out relative to `UNISON_MODEL_DIR` (default `/var/lib/unison/models`)
- Install and verify via `unison-models` (from `unison-common`).

This repo also ships **pack selection manifests** under `model-packs/alpha/` to make defaults explicit
(interaction/planner models, ASR/TTS requirements, and sizing notes).

## Pack selection (manifests in this repo)

- `model-packs/alpha/default.json` — recommended for evaluator installs (Qwen default interaction, includes speech pack requirement).
- `model-packs/alpha/light.json` — minimal footprint (text-only; fewer local models).
- `model-packs/alpha/full.json` — larger footprint (adds bigger models where supported).

## Runtime behavior

- If `UNISON_MODEL_PACK_REQUIRED` is set, the orchestrator will gate Phase 1 boot and emit a clear recovery message if models are missing.
- Install helpers may optionally pull required Ollama models when allowed (see `installer/ensure-models.sh`).

