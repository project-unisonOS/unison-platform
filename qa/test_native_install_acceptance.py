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
AGENT_VDI_BASE = os.environ.get("AGENT_VDI_BASE_URL", "http://localhost:8093")
STORAGE_BASE = os.environ.get("STORAGE_BASE_URL", "http://localhost:8082")
UPDATES_BASE = os.environ.get("UPDATES_BASE_URL", "http://localhost:8094")
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


def _updates_available() -> bool:
    try:
        resp = requests.get(f"{UPDATES_BASE}/health", timeout=3)
        return resp.status_code == 200
    except Exception:  # noqa: BLE001
        return False


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


def test_vdi_download_returns_artifact_ids():
    _wait_http_ok(f"{AGENT_VDI_BASE}/readyz")
    _wait_http_ok(f"{RENDERER_BASE}/readyz")
    _wait_http_ok(f"{CONTEXT_BASE}/health")

    session_id = "milestone1-vdi-acceptance"
    resp = requests.post(
        f"{AGENT_VDI_BASE}/tasks/download",
        json={
            "person_id": MILESTONE1_PERSON_ID,
            "session_id": session_id,
            "url": "http://experience-renderer:8082/readyz",
            "filename": "renderer-readyz.txt",
        },
        timeout=15,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body.get("status") == "ok"
    file_ids = body.get("file_ids") or []
    assert isinstance(file_ids, list) and file_ids, body

    artifact_id = file_ids[0]
    storage_resp = requests.get(f"{STORAGE_BASE}/kv/vdi_artifacts/{artifact_id}", timeout=5)
    assert storage_resp.status_code == 200, storage_resp.text
    storage_body = storage_resp.json()
    assert storage_body.get("ok") is True, storage_body
    stored_value = storage_body.get("value") or {}
    assert stored_value.get("artifact_id") == artifact_id
    assert stored_value.get("filename") == "renderer-readyz.txt"
    metadata = stored_value.get("metadata") or {}
    assert metadata.get("person_id") == MILESTONE1_PERSON_ID
    assert metadata.get("session_id") == session_id
    assert metadata.get("source_url") == "http://experience-renderer:8082/readyz"
    assert isinstance(stored_value.get("content_b64"), str) and stored_value.get("content_b64")

    deadline = time.time() + 5
    last_events = []
    while time.time() < deadline:
        renderer_resp = requests.get(f"{RENDERER_BASE}/telemetry/actuation", timeout=5)
        assert renderer_resp.status_code == 200, renderer_resp.text
        items = (renderer_resp.json() or {}).get("items") or []
        last_events = items
        if any(
            item.get("action") == "download"
            and item.get("session_id") == session_id
            and item.get("status") == "ok"
            and artifact_id in (item.get("file_ids") or [])
            for item in items
            if isinstance(item, dict)
        ):
            break
        time.sleep(0.5)

    assert any(
        item.get("action") == "download"
        and item.get("session_id") == session_id
        and item.get("status") == "ok"
        and artifact_id in (item.get("file_ids") or [])
        for item in last_events
        if isinstance(item, dict)
    ), last_events


def test_updates_policy_and_plan_flow():
    if not _updates_available():
        pytest.skip("updates profile is not running on this stack")

    _wait_http_ok(f"{UPDATES_BASE}/health")

    check_resp = requests.post(f"{UPDATES_BASE}/v1/tools/updates.check", json={"arguments": {}}, timeout=5)
    assert check_resp.status_code == 200, check_resp.text
    check_body = check_resp.json() or {}
    assert check_body.get("ok") is True
    catalog = check_body.get("catalog") or {}
    manifest = catalog.get("manifest") or {}
    assert manifest.get("schema_version") == "unison.platform.release.manifest.v1"
    assert isinstance(manifest.get("release_version"), str) and manifest.get("release_version")
    resolved_images = manifest.get("images_resolved") or {}
    assert "updates" in resolved_images
    assert isinstance((resolved_images.get("updates") or {}).get("image_id"), str)
    assert (resolved_images.get("updates") or {}).get("image_id")

    get_resp = requests.post(f"{UPDATES_BASE}/v1/tools/updates.get_policy", json={"arguments": {}}, timeout=5)
    assert get_resp.status_code == 200, get_resp.text
    original_policy = (get_resp.json() or {}).get("policy") or {}
    original_auto_apply = original_policy.get("auto_apply", "manual")

    set_resp = requests.post(
        f"{UPDATES_BASE}/v1/tools/updates.set_policy",
        json={"arguments": {"policy_patch": {"auto_apply": "security_only"}}},
        timeout=5,
    )
    assert set_resp.status_code == 200, set_resp.text
    set_body = set_resp.json() or {}
    assert set_body.get("ok") is True
    assert (set_body.get("policy") or {}).get("auto_apply") == "security_only"

    plan_resp = requests.post(
        f"{UPDATES_BASE}/v1/tools/updates.plan",
        json={
            "arguments": {
                "person_id": MILESTONE1_PERSON_ID,
                "selection": {"platform_version": "alpha-next"},
                "constraints": {"approved": True},
            }
        },
        timeout=5,
    )
    assert plan_resp.status_code == 200, plan_resp.text
    plan_body = plan_resp.json() or {}
    assert plan_body.get("ok") is True
    assert plan_body.get("requires_confirmation") is True
    plan_id = plan_body.get("plan_id")
    assert isinstance(plan_id, str) and plan_id
    assert plan_body.get("source_manifest_version") == manifest.get("release_version")
    assert (plan_body.get("target_release") or {}).get("platform_version") == manifest.get("release_version")

    apply_resp = requests.post(
        f"{UPDATES_BASE}/v1/tools/updates.apply",
        json={"arguments": {"plan_id": plan_id, "person_id": MILESTONE1_PERSON_ID}},
        timeout=5,
    )
    assert apply_resp.status_code == 200, apply_resp.text
    apply_body = apply_resp.json() or {}
    assert apply_body.get("ok") is True
    job_id = apply_body.get("job_id")
    assert isinstance(job_id, str) and job_id
    assert apply_body.get("status") == "completed"

    status_resp = requests.post(
        f"{UPDATES_BASE}/v1/tools/updates.status",
        json={"arguments": {"job_id": job_id}},
        timeout=5,
    )
    assert status_resp.status_code == 200, status_resp.text
    status_body = status_resp.json() or {}
    assert status_body.get("ok") is True
    assert status_body.get("job_id") == job_id
    assert status_body.get("plan_id") == plan_id
    assert status_body.get("status") == "completed"
    result = status_body.get("result") or {}
    assert result.get("mode") == "dry-run"
    assert (result.get("target_release") or {}).get("platform_version") == manifest.get("release_version")
    rollback_target = result.get("rollback_target") or {}
    assert isinstance(rollback_target.get("platform_version"), str) and rollback_target.get("platform_version")

    rollback_resp = requests.post(
        f"{UPDATES_BASE}/v1/tools/updates.rollback",
        json={"arguments": {}},
        timeout=5,
    )
    assert rollback_resp.status_code == 200, rollback_resp.text
    rollback_body = rollback_resp.json() or {}
    assert rollback_body.get("ok") is True
    assert isinstance(rollback_body.get("history_count"), int)
    assert rollback_body.get("history_count") >= 1
    assert ((rollback_body.get("last_attempted_target") or {}).get("target_release") or {}).get("platform_version") == manifest.get("release_version")
    assert isinstance((rollback_body.get("target") or {}).get("platform_version"), str)
    assert (rollback_body.get("target") or {}).get("platform_version")

    restore_resp = requests.post(
        f"{UPDATES_BASE}/v1/tools/updates.set_policy",
        json={"arguments": {"policy_patch": {"auto_apply": original_auto_apply}}},
        timeout=5,
    )
    assert restore_resp.status_code == 200, restore_resp.text
