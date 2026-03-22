"""
Native install acceptance checks for the supported Milestone 1 path.

This suite is intentionally opt-in because it targets a real installed stack.

Enable with:
  RUN_NATIVE_INSTALL_ACCEPTANCE=1 python -m pytest qa/test_native_install_acceptance.py -v
"""

from __future__ import annotations

import os
import subprocess

import pytest
import requests


RUN_NATIVE_INSTALL_ACCEPTANCE = os.environ.get("RUN_NATIVE_INSTALL_ACCEPTANCE", "0").lower() in {"1", "true", "yes", "on"}
UNISONCTL_BIN = os.environ.get("UNISONCTL_BIN", "unisonctl")
ORCHESTRATOR_BASE = os.environ.get("ORCHESTRATOR_BASE_URL", "http://localhost:8080")
RENDERER_BASE = os.environ.get("RENDERER_BASE_URL", "http://localhost:8092")
AUTH_BASE = os.environ.get("AUTH_BASE_URL", "http://localhost:8083")


pytestmark = pytest.mark.skipif(
    not RUN_NATIVE_INSTALL_ACCEPTANCE,
    reason="native install acceptance is opt-in and targets a real installed stack",
)


def _run_unisonctl(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [UNISONCTL_BIN, *args],
        check=False,
        capture_output=True,
        text=True,
    )


def test_unisonctl_doctor_passes():
    result = _run_unisonctl("doctor")
    assert result.returncode == 0, result.stdout + result.stderr


def test_unisonctl_health_passes():
    result = _run_unisonctl("health")
    assert result.returncode == 0, result.stdout + result.stderr


def test_startup_status_reaches_expected_shape():
    resp = requests.get(f"{ORCHESTRATOR_BASE}/startup/status", timeout=5)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert isinstance(body, dict)
    assert "state" in body
    assert "onboarding_required" in body or body.get("state") in {"starting", "unavailable"}


def test_renderer_onboarding_status_reaches_expected_shape():
    resp = requests.get(f"{RENDERER_BASE}/onboarding-status", timeout=5)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["ok"] is True
    assert isinstance(body.get("steps"), list)
    assert isinstance(body.get("remediation"), list)
    assert "ready_to_finish" in body


def test_auth_bootstrap_status_reaches_expected_shape():
    resp = requests.get(f"{AUTH_BASE}/bootstrap/status", timeout=5)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert isinstance(body, dict)
    assert "bootstrap_required" in body
    assert "enabled" in body
