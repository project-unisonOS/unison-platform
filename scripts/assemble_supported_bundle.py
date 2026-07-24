#!/usr/bin/env python3
"""Assemble an immutable, signed native-appliance release bundle."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from installer.release_bundle import assemble_bundle, sha256_file


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--images-env", required=True, type=Path)
    parser.add_argument("--signing-key", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    index = assemble_bundle(args.manifest, args.images_env, args.out, args.signing_key, ROOT)
    print(json.dumps({
        "bundle": str(args.out),
        "bundle_sha256": sha256_file(args.out),
        "index": index,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
