#!/usr/bin/env python3
"""Assemble the reproducible, signed unsupported-preview release assets."""

import argparse
import hashlib
import json
import os
import shutil
import subprocess  # nosec B404
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_NAMES = {
    "auth": "UNISON_AUTH_IMAGE",
    "context": "UNISON_CONTEXT_IMAGE",
    "policy": "UNISON_POLICY_IMAGE",
    "orchestrator": "UNISON_ORCHESTRATOR_IMAGE",
    "intent-graph": "UNISON_INTENT_GRAPH_IMAGE",
    "context-graph": "UNISON_CONTEXT_GRAPH_IMAGE",
    "experience-renderer": "UNISON_RENDERER_IMAGE",
    "io-speech": "UNISON_SPEECH_IMAGE",
    "inference": "UNISON_INFERENCE_IMAGE",
    "storage": "UNISON_STORAGE_IMAGE",
    "redis": "UNISON_REDIS_IMAGE",
    "postgres": "UNISON_POSTGRES_IMAGE",
    "nats": "UNISON_NATS_IMAGE",
}
UPSTREAM = {
    "redis": "redis@sha256:e6c68d7d2f3e5a4e6d8bf2f777b8d4b8f7b52d2f985b254f153956dbfea457a1",
    "postgres": "postgres@sha256:1d288494853e244e7a78d87b3526e650e5221c622f9768ecac9313d0874a9c39",
    "nats": "nats@sha256:9c0a3a03f740db3584078c8fc9e7f276297766a6d5c80e89c55a7a8387f8c2c7",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(*args: str, env: dict | None = None) -> None:
    subprocess.run(args, check=True, cwd=ROOT, env=env)  # nosec B603


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    parser.add_argument("--metadata-dir", required=True, type=Path)
    parser.add_argument("--signing-key", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    correspondence = json.loads(
        (ROOT / "releases/preview-source-correspondence.v1.json").read_text()
    )
    images = dict(UPSTREAM)
    sources = {}
    recipes = {}
    for path in sorted(args.metadata_dir.glob("*.json")):
        item = json.loads(path.read_text())
        repo = item["repository"]
        expected_commit = correspondence["images"].get(repo)
        if expected_commit != item["source_commit"]:
            raise SystemExit(f"{repo}: source commit does not match correspondence record")
        digest = item["digest"]
        if not digest.startswith("sha256:") or len(digest) != 71:
            raise SystemExit(f"{repo}: invalid image digest")
        images[repo.removeprefix("unison-")] = f"ghcr.io/project-unisonos/{repo}@{digest}"
        sources[repo] = item["source_commit"]
        recipes[repo] = item["effective_dockerfile_sha256"]
    if set(sources) != set(correspondence["images"]):
        raise SystemExit("image metadata is incomplete")

    image_env = args.out_dir / f"unisonos-{args.version}-images.env"
    image_env.write_text(
        "".join(f"{ENV_NAMES[name]}={images[name]}\n" for name in sorted(images)),
        encoding="utf-8",
    )
    epoch = int(subprocess.check_output(
        ["git", "show", "-s", "--format=%ct", "HEAD"], cwd=ROOT, text=True
    ).strip())
    manifest = args.out_dir / f"unisonos-{args.version}-manifest.json"
    env = dict(os.environ, SOURCE_DATE_EPOCH=str(epoch))
    run(sys.executable, "scripts/generate_supported_manifest.py", "--version", args.version,
        "--images-env", str(image_env), "--out", str(manifest), env=env)
    bundle = args.out_dir / f"unisonos-{args.version}-x86_64.tar"
    run(sys.executable, "scripts/assemble_supported_bundle.py", "--manifest", str(manifest),
        "--images-env", str(image_env), "--signing-key", str(args.signing_key),
        "--out", str(bundle))

    source_record = {
        **correspondence,
        "release": args.version,
        "platform_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "effective_dockerfile_sha256": recipes,
        "resolved_images": dict(sorted(images.items())),
    }
    source_path = args.out_dir / f"unisonos-{args.version}-sources.json"
    source_path.write_text(json.dumps(source_record, indent=2, sort_keys=True) + "\n")
    packages = [{
        "SPDXID": f"SPDXRef-{name.replace('_', '-')}",
        "name": name,
        "downloadLocation": ref,
        "checksums": [{"algorithm": "SHA256", "checksumValue": ref.rsplit(":", 1)[1]}],
        "filesAnalyzed": False,
    } for name, ref in sorted(images.items())]
    sbom_path = args.out_dir / f"unisonos-{args.version}.spdx.json"
    sbom_path.write_text(json.dumps({
        "spdxVersion": "SPDX-2.3",
        "dataLicense": "CC0-1.0",
        "SPDXID": "SPDXRef-DOCUMENT",
        "name": f"UnisonOS {args.version} runtime images",
        "documentNamespace": f"https://unisonos.org/sbom/{args.version}",
        "creationInfo": {"created": "1970-01-01T00:00:00Z", "creators": ["Tool: assemble_preview_release.py"]},
        "packages": packages,
    }, indent=2, sort_keys=True) + "\n")
    provenance_path = args.out_dir / f"unisonos-{args.version}-provenance.json"
    provenance_path.write_text(json.dumps({
        "_type": "https://in-toto.io/Statement/v1",
        "subject": [{"name": bundle.name, "digest": {"sha256": sha256(bundle)}}],
        "predicateType": "https://slsa.dev/provenance/v1",
        "predicate": {
            "buildDefinition": {
                "buildType": "https://unisonos.org/build-types/preview-release/v1",
                "externalParameters": {"version": args.version},
                "resolvedDependencies": [
                    {"uri": f"https://github.com/project-unisonOS/{repo}",
                     "digest": {"gitCommit": commit}}
                    for repo, commit in sorted(sources.items())
                ],
            },
            "runDetails": {"builder": {"id": "https://github.com/project-unisonOS/unison-platform/actions"}},
        },
    }, indent=2, sort_keys=True) + "\n")
    shutil.copy2(ROOT / "releases/trust/preview-bundle-ed25519.pem",
                 args.out_dir / "unisonos-preview-bundle-ed25519.pem")
    policy = args.out_dir / f"unisonos-{args.version}-support.json"
    policy.write_text(json.dumps({
        "version": args.version,
        "status": "unsupported-preview",
        "hardware_validation": "pending",
        "production_use": False,
        "support_end": None,
    }, indent=2, sort_keys=True) + "\n")
    notes = args.out_dir / "RELEASE_NOTES.md"
    notes.write_text(
        f"# UnisonOS {args.version}\n\n"
        "This is an unsupported, pre-production preview for software-only evaluation. "
        "Physical appliance compatibility and recovery validation remain pending. "
        "Do not use it for production data.\n\n"
        f"Download `{bundle.name}`, `unisonos-preview-bundle-ed25519.pem`, and "
        f"`unisonos-{args.version}-manifest.json`. Verify every downloaded file with "
        "`SHA256SUMS` before installation.\n",
        encoding="utf-8",
    )
    core = sorted(p for p in args.out_dir.iterdir() if p.is_file())
    sums = args.out_dir / "SHA256SUMS"
    sums.write_text("".join(f"{sha256(p)}  {p.name}\n" for p in core))
    run("openssl", "pkeyutl", "-sign", "-rawin", "-inkey", str(args.signing_key),
        "-in", str(sums), "-out", str(args.out_dir / "SHA256SUMS.ed25519"))


if __name__ == "__main__":
    main()
