#!/usr/bin/env bash
set -euo pipefail

# Ensure models for a selected profile.
#
# This is intentionally best-effort for alpha: it prints actionable guidance when models/providers are missing.

PREFIX=${PREFIX:-/opt/unison-platform}
PROFILE=${UNISON_MODEL_PACK_PROFILE:-alpha/default}
MODEL_DIR=${UNISON_MODEL_DIR:-/var/lib/unison/models}
ALLOW_DOWNLOADS=${UNISON_ALLOW_MODEL_DOWNLOADS:-false}

manifest_path="${PREFIX}/model-packs/${PROFILE}.json"
if [ ! -f "${manifest_path}" ]; then
  echo "[model-packs] Unknown profile '${PROFILE}' (missing ${manifest_path})." >&2
  exit 1
fi

read_json() {
  python3 - "$manifest_path" <<'PY'
import json, sys
path = sys.argv[1]
data = json.load(open(path, "r", encoding="utf-8"))
def out(key, value):
  print(f"{key}={value}")
defaults = data.get("defaults") or {}
out("inference_provider", defaults.get("inference_provider") or "")
out("interaction_model", defaults.get("interaction_model") or "")
out("planner_provider", defaults.get("planner_provider") or "")
out("planner_model", defaults.get("planner_model") or "")
packs = data.get("required_model_packs") or []
ollama = data.get("ollama_models") or []
print("required_model_packs=" + ",".join(str(x) for x in packs))
print("ollama_models=" + ",".join(str(x) for x in ollama))
PY
}

if ! command -v python3 >/dev/null 2>&1; then
  echo "[model-packs] python3 is required to read ${manifest_path}." >&2
  exit 1
fi

eval "$(read_json)"

mkdir -p "${MODEL_DIR}"

echo "[model-packs] profile=${PROFILE}"
echo "[model-packs] model_dir=${MODEL_DIR}"
echo "[model-packs] inference_provider=${inference_provider:-}"
echo "[model-packs] interaction_model=${interaction_model:-}"
echo "[model-packs] planner_model=${planner_model:-}"

if [ -n "${required_model_packs:-}" ]; then
  echo "[model-packs] required_model_packs=${required_model_packs}"
  echo "[model-packs] Note: install packs with 'unison-models' (from unison-common)."
fi

if [ -n "${ollama_models:-}" ]; then
  echo "[model-packs] ollama_models=${ollama_models}"
  if command -v ollama >/dev/null 2>&1; then
    if [ "${ALLOW_DOWNLOADS}" = "true" ] || [ "${ALLOW_DOWNLOADS}" = "1" ]; then
      IFS=',' read -r -a models <<< "${ollama_models}"
      for m in "${models[@]}"; do
        m="$(echo "${m}" | xargs)"
        [ -z "${m}" ] && continue
        echo "[model-packs] ollama pull ${m}"
        ollama pull "${m}"
      done
    else
      echo "[model-packs] Ollama is installed but downloads are disabled (set UNISON_ALLOW_MODEL_DOWNLOADS=true to auto-pull)." >&2
    fi
  else
    echo "[model-packs] Ollama is not installed. Install it (or provide an Ollama endpoint) to use local Qwen models." >&2
    echo "[model-packs] See: https://ollama.com/download" >&2
  fi
fi

echo "[model-packs] done"

