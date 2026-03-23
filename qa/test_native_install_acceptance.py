"""
Native install acceptance checks for the supported Milestone 1 path.

This suite is intentionally opt-in because it targets a real installed stack.

Enable with:
  RUN_NATIVE_INSTALL_ACCEPTANCE=1 python -m pytest qa/test_native_install_acceptance.py -v
"""

from __future__ import annotations

import os
import subprocess
import time

import pytest
import requests


RUN_NATIVE_INSTALL_ACCEPTANCE = os.environ.get("RUN_NATIVE_INSTALL_ACCEPTANCE", "0").lower() in {"1", "true", "yes", "on"}
UNISONCTL_BIN = os.environ.get("UNISONCTL_BIN", "unisonctl")
ORCHESTRATOR_BASE = os.environ.get("ORCHESTRATOR_BASE_URL", "http://localhost:8080")
RENDERER_BASE = os.environ.get("RENDERER_BASE_URL", "http://localhost:8092")
AUTH_BASE = os.environ.get("AUTH_BASE_URL", "http://localhost:8083")
CONTEXT_BASE = os.environ.get("CONTEXT_BASE_URL", "http://localhost:8081")
MILESTONE1_USERNAME = os.environ.get("MILESTONE1_ACCEPTANCE_USERNAME")
MILESTONE1_PASSWORD = os.environ.get("MILESTONE1_ACCEPTANCE_PASSWORD")
MILESTONE1_PERSON_ID = os.environ.get("MILESTONE1_ACCEPTANCE_PERSON_ID", "local-person")


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


def _wait_http_ok(url: str, *, timeout: float = 15.0) -> None:
    deadline = time.time() + timeout
    last_error = None
    while time.time() < deadline:
        try:
            resp = requests.get(url, timeout=3)
            if resp.status_code == 200:
                return
            last_error = f"status {resp.status_code}"
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)
        time.sleep(0.5)
    raise AssertionError(f"{url} did not become ready: {last_error}")


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


@pytest.mark.skipif(
    not (MILESTONE1_USERNAME and MILESTONE1_PASSWORD),
    reason="briefing acceptance requires MILESTONE1_ACCEPTANCE_USERNAME and MILESTONE1_ACCEPTANCE_PASSWORD",
)
def test_briefing_refresh_returns_cards_and_emits():
    _wait_http_ok(f"{ORCHESTRATOR_BASE}/health")
    _wait_http_ok(f"{RENDERER_BASE}/health")
    _wait_http_ok(f"{AUTH_BASE}/health")
    _wait_http_ok(f"{CONTEXT_BASE}/health")

    token_resp = requests.post(
        f"{AUTH_BASE}/token",
        data={
            "username": MILESTONE1_USERNAME,
            "password": MILESTONE1_PASSWORD,
            "grant_type": "password",
        },
        timeout=5,
    )
    assert token_resp.status_code == 200, token_resp.text
    token_body = token_resp.json()
    access_token = token_body.get("access_token")
    assert isinstance(access_token, str) and access_token

    ingest_resp = requests.post(
        f"{ORCHESTRATOR_BASE}/ingest",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "intent": "dashboard.refresh",
            "payload": {"person_id": MILESTONE1_PERSON_ID},
            "source": "milestone1-acceptance",
        },
        timeout=10,
    )
    assert ingest_resp.status_code == 200, ingest_resp.text
    ingest_body = ingest_resp.json()
    assert ingest_body.get("status") == "success"
    result = (ingest_body.get("result") or {}).get("response") or {}
    assert result.get("ok") is True
    cards = result.get("cards") or []
    assert isinstance(cards, list) and cards, ingest_body
    assert any("briefing" in [str(t).lower() for t in (card.get("tags") or [])] for card in cards if isinstance(card, dict))

    deadline = time.time() + 5
    last_items = []
    while time.time() < deadline:
        renderer_resp = requests.get(f"{RENDERER_BASE}/experiences", timeout=5)
        assert renderer_resp.status_code == 200, renderer_resp.text
        items = (renderer_resp.json() or {}).get("items") or []
        last_items = items
        if any(item.get("origin_intent") == "dashboard.refresh" for item in items if isinstance(item, dict)):
            break
        time.sleep(0.5)
    assert any(item.get("origin_intent") == "dashboard.refresh" for item in last_items if isinstance(item, dict)), last_items
