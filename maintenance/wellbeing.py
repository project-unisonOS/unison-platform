"""Create the allowlisted renderer projection from maintenance results."""

from __future__ import annotations


LABELS = {
    "cpu.saturation": "Processing",
    "memory.pressure": "Memory",
    "storage.used": "Storage",
    "service.error_rate": "Reliability",
    "backup.age_hours": "Backup",
    "model.first_token_ms": "Model responsiveness",
}


def wellbeing_projection(result: dict, *, observed_at: str) -> dict:
    observations = result.get("observations", [])
    recommendations = result.get("recommendations", [])
    severity_order = {"healthy": 0, "notice": 1, "warning": 2, "critical": 3}
    worst = max((severity_order.get(item.get("severity"), 0) for item in observations), default=0)
    status = ("healthy", "notice", "attention", "urgent")[worst]
    summary = {
        "healthy": "The measured system indicators are healthy.",
        "notice": "A minor system observation is available.",
        "attention": "One or more system indicators may benefit from attention.",
        "urgent": "A system indicator needs timely review.",
    }[status]
    return {
        "status": status,
        "summary": summary,
        "observed_at": observed_at,
        "dimensions": [
            {
                "label": LABELS.get(item["metric"], item["metric"]),
                "status": item["severity"],
                "detail": f"{item['metric']} is {item['value']} {item['unit']}",
            }
            for item in observations
        ],
        "recommendations": [
            {
                "recommendation_id": item.get("recommendation_id", ""),
                "title": item["title"],
                "explanation": " ".join(item["rationale"]),
                "authority": item["authority"],
                "requires_confirmation": item["requires_confirmation"],
                "alternatives": item.get("alternatives", []),
                "risk": item.get("risk", "unknown"),
            }
            for item in recommendations
        ],
        "maintenance_history": [
            {
                "receipt_id": item.get("receipt_id", ""),
                "result": item.get("result", "unknown"),
                "completed_at": item.get("completed_at"),
                "checkpoint_id": item.get("checkpoint_id"),
            }
            for item in result.get("receipts", [])
        ],
        "community_proposals": [
            {
                "subject": item.get("subject", ""),
                "statement": item.get("statement", ""),
                "source_count": item.get("source_count", 0),
                "authority": "test-proposal-only",
            }
            for item in result.get("community_proposals", [])
        ],
        "privacy": {"personal_content_collected": False},
        "autonomy": {
            "default": "recommend",
            "execution_available": bool(result.get("active_grant")),
            "grant_id": result.get("active_grant", {}).get("grant_id"),
            "revocable": True,
        },
    }
