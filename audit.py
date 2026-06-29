import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

LOG_FILE = Path(__file__).parent / "audit_log.jsonl"


def write_entry(entry: dict) -> dict:
    """Append one structured entry to the audit log. Returns the saved record."""
    record = {
        "entry_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **entry,
    }
    with LOG_FILE.open("a") as f:
        f.write(json.dumps(record) + "\n")
    return record


def read_entries(
    limit: int = 50,
    offset: int = 0,
    content_id: str | None = None,
    event_type: str | None = None,
) -> dict:
    """Read entries from the log with optional filtering and pagination."""
    if not LOG_FILE.exists():
        return {"total": 0, "limit": limit, "offset": offset, "entries": []}

    with LOG_FILE.open() as f:
        entries = [json.loads(line) for line in f if line.strip()]

    if content_id:
        entries = [e for e in entries if e.get("content_id") == content_id]
    if event_type:
        entries = [e for e in entries if e.get("event_type") == event_type]

    total = len(entries)
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "entries": entries[offset : offset + limit],
    }
