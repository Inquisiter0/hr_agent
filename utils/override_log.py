# override_log.py — append-only audit trail (JSONL, no SQLite needed)
import json
import os
from datetime import datetime, timezone

LOG_FILE = "output/override_audit.jsonl"


def log_override(candidate: str, original: float, new: float, reason: str) -> None:
    os.makedirs("output", exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "candidate": candidate,
        "original_score": round(original, 2),
        "new_score": round(new, 2),
        "delta": round(new - original, 2),
        "reason": reason,
    }
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def read_log() -> list:
    if not os.path.exists(LOG_FILE):
        return []
    entries = []
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return entries
