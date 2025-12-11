"""
Platform smoke tests:
- Health checks for core services
- Minimal voice/multimodal flow stub (renderer -> io-speech -> orchestrator -> inference)

Environment:
- TARGET_HOST (default: http://localhost)
- PORT_xxx overrides (default devstack/prod mapping)
"""

import os
import time

import requests

TARGET = os.environ.get("TARGET_HOST", "http://localhost")

PORTS = {
    "orchestrator": int(os.environ.get("PORT_ORCHESTRATOR", "8090")),
    "intent_graph": int(os.environ.get("PORT_INTENT_GRAPH", "8080")),
    "context": int(os.environ.get("PORT_CONTEXT", "8081")),
    "storage": int(os.environ.get("PORT_STORAGE", "8082")),
    "policy": int(os.environ.get("PORT_POLICY", "8083")),
    "auth": int(os.environ.get("PORT_AUTH", "8083")),
    "io_speech": int(os.environ.get("PORT_IO_SPEECH", "8084")),
    "io_core": int(os.environ.get("PORT_IO_CORE", "8085")),
    "io_vision": int(os.environ.get("PORT_IO_VISION", "8086")),
    "inference": int(os.environ.get("PORT_INFERENCE", "8087")),
    "renderer": int(os.environ.get("PORT_RENDERER", "8092")),
}


def url(port, path):
    return f"{TARGET}:{port}{path}"


def wait_for_health(port, path="/health", timeout=30):
    deadline = time.time() + timeout
    last_error = None
    while time.time() < deadline:
        try:
            resp = requests.get(url(port, path), timeout=3)
            if resp.status_code == 200:
                return True
            last_error = f"status {resp.status_code}"
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)
        time.sleep(1)
    raise AssertionError(f"Health check failed for {port}{path}: {last_error}")


def test_core_health():
    for svc in ["orchestrator", "context", "storage", "policy", "inference"]:
        assert wait_for_health(PORTS[svc]), f"{svc} did not become healthy"


def test_renderer_health():
    assert wait_for_health(PORTS["renderer"], "/health"), "renderer not healthy"


def test_io_health():
    for svc in ["io_speech", "io_core", "io_vision"]:
        assert wait_for_health(PORTS[svc]), f"{svc} did not become healthy"


def test_inference_stub():
    payload = {
        "intent": "summarize.doc",
        "prompt": "hello",
        "provider": "ollama",
        "model": "qwen2.5",
        "max_tokens": 10,
        "temperature": 0.1,
    }
    resp = requests.post(url(PORTS["inference"], "/inference/request"), json=payload, timeout=10)
    assert resp.status_code == 200, f"inference request failed: {resp.status_code} {resp.text}"
    data = resp.json()
    assert "response" in data or "result" in data, "unexpected inference response shape"
