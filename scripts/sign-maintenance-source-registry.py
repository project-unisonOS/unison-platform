#!/usr/bin/env python3
"""Sign the canonical maintenance source registry with an Ed25519 release key."""

from __future__ import annotations

import argparse
import base64
import json
import subprocess  # nosec B404: OpenSSL is the release signing boundary.
import tempfile
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--payload", type=Path, required=True)
    parser.add_argument("--private-key", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    signed = json.loads(args.payload.read_text(encoding="utf-8"))
    payload = json.dumps(
        signed, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()
    with tempfile.NamedTemporaryFile() as payload_file:
        payload_file.write(payload)
        payload_file.flush()
        signature = subprocess.run(  # nosec B603
            [
                "openssl", "pkeyutl", "-sign", "-inkey", str(args.private_key),
                "-rawin", "-in", payload_file.name,
            ],
            check=True,
            capture_output=True,
        ).stdout
    envelope = {"signed": signed, "signature": base64.b64encode(signature).decode()}
    args.out.write_text(json.dumps(envelope, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
