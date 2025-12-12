#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Target:
    key: str
    display: str
    audience: str
    target_platform: str
    not_for: str
    install_anchor: str
    assets: list[tuple[str, str]]


TARGETS: dict[str, Target] = {
    "wsl2": Target(
        key="wsl2",
        display="WSL2 (Developer)",
        audience="Developers on Windows using WSL2 for local development.",
        target_platform="Windows + WSL2",
        not_for="Linux VM users; bare-metal installs.",
        install_anchor="wsl2",
        assets=[
            ("unisonos-wsl2-dev.tar.gz", "WSL2 distro import tarball (use `wsl --import`)."),
        ],
    ),
    "linux-vm": Target(
        key="linux-vm",
        display="Linux VM (Developer)",
        audience="Developers who want an isolated VM-based UnisonOS environment.",
        target_platform="Linux VM (QCOW2/VMDK)",
        not_for="WSL2 installs; bare-metal installs.",
        install_anchor="linux-vm",
        assets=[
            ("unisonos-linux-vm-dev.qcow2", "QEMU/virt-manager compatible disk image."),
            ("unisonos-linux-vm-dev.vmdk", "VMware-compatible disk image (optional)."),
        ],
    ),
    "bare-metal": Target(
        key="bare-metal",
        display="Bare Metal Installer",
        audience="Developers/operators installing onto dedicated hardware.",
        target_platform="Bare metal (bootable ISO)",
        not_for="WSL2 installs; VM-based installs.",
        install_anchor="bare-metal",
        assets=[
            ("unisonos-bare-metal.iso", "Bootable installer ISO (flash to USB)."),
        ],
    ),
}


def render_template(template: str, mapping: dict[str, str]) -> str:
    out = template
    for key, value in mapping.items():
        out = out.replace(f"{{{{{key}}}}}", value)
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=True, choices=sorted(TARGETS.keys()))
    parser.add_argument("--docs-root", required=True)
    parser.add_argument("--template", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    target = TARGETS[args.target]
    install_url = f"{args.docs_root.rstrip('/')}/install#{target.install_anchor}"

    assets_bullets = "\n".join(
        f"- `{name}` — {desc}" for (name, desc) in target.assets
    )

    template_path = Path(args.template)
    out_path = Path(args.out)

    template = template_path.read_text(encoding="utf-8")
    body = render_template(
        template,
        {
            "TARGET_DISPLAY": target.display,
            "AUDIENCE": target.audience,
            "TARGET_PLATFORM": target.target_platform,
            "NOT_FOR": target.not_for,
            "ASSETS_BULLETS": assets_bullets,
            "INSTALL_URL": install_url,
        },
    ).strip() + "\n"

    out_path.write_text(body, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

