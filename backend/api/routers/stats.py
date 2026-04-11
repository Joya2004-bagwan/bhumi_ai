"""Stats router: aggregated metrics from jobs.json + structured event log."""

import json
import logging
from collections import defaultdict
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter

from ..config import BATCH_DIR, BASE_DIR

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")

JOBS_FILE = BATCH_DIR / "jobs.json"
EVENT_LOG = BASE_DIR / "logs" / "events.jsonl"


def _load_jobs() -> list[dict]:
    if not JOBS_FILE.exists():
        return []
    try:
        raw = json.loads(JOBS_FILE.read_text(encoding="utf-8"))
        return list(raw.values())
    except Exception:
        return []


def _load_events() -> list[dict]:
    if not EVENT_LOG.exists():
        return []
    events = []
    try:
        for line in EVENT_LOG.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                try:
                    events.append(json.loads(line))
                except Exception:
                    pass
    except Exception:
        pass
    return events


def _parse_ts(ts_str: str) -> datetime | None:
    try:
        dt = datetime.fromisoformat(ts_str)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


@router.post("/log-export")
async def log_export(body: dict):
    """Called by the frontend when a single-image file is downloaded client-side."""
    from ...utils.event_logger import log_event as _log
    fmt = (body.get("export_format") or "").lower().strip(".")
    _log("export",
         image_id=body.get("image_id", ""),
         filename=body.get("filename", ""),
         export_format=fmt or "unknown",
         building_count=body.get("building_count", 0),
         model=body.get("model", ""),
         source="single")
    return {"ok": True}


@router.get("/stats")
def get_stats():
    jobs = _load_jobs()
    events = _load_events()

    # ── Export format lookup ──────────────────────────────────────────────
    export_map: dict[str, str] = {}
    for e in events:
        if e.get("event") == "export":
            key = e.get("image_id") or e.get("filename", "")
            if key:
                export_map[key] = e.get("export_format", "—")
            fname = e.get("filename", "")
            if fname:
                export_map[fname] = e.get("export_format", "—")

    # ── Per-image rows ────────────────────────────────────────────────────
    image_rows: list[dict] = []

    for job in jobs:
        model = job.get("model", "")
        created_at = job.get("created_at", "")
        for item in job.get("items", []):
            if item.get("status") == "done":
                iid = item.get("item_id", "")
                fname = item.get("original_filename", "—")
                fmt = export_map.get(iid) or export_map.get(fname) or "—"
                image_rows.append({
                    "filename": fname,
                    "building_count": item.get("building_count", 0),
                    "model": model,
                    "ts": created_at,
                    "export_format": fmt,
                    "source": "batch",
                })

    upload_events = {e["image_id"]: e for e in events if e.get("event") == "upload" and "image_id" in e}
    boundary_events = [e for e in events if e.get("event") == "boundary_detect"]
    segment_events  = {e["image_id"]: e for e in events if e.get("event") == "segment" and "image_id" in e}

    # boundary_detect carries building_count — use as primary source.
    # Fall back to segment events (building_count=0) for images that were
    # segmented but boundary detection hasn't run yet.
    seen_single: dict[str, dict] = {}
    for ev in boundary_events:
        iid = ev.get("image_id", "")
        if iid:
            seen_single[iid] = ev

    # add segment-only images not already covered by a boundary event
    for iid, ev in segment_events.items():
        if iid not in seen_single:
            seen_single[iid] = {**ev, "building_count": ev.get("building_count", 0)}

    for ev in seen_single.values():
        iid = ev.get("image_id", "")
        upload = upload_events.get(iid, {})
        filename = upload.get("filename", iid[:8] + "…" if iid else "—")
        fmt = export_map.get(iid) or export_map.get(filename) or "—"
        image_rows.append({
            "filename": filename,
            "building_count": ev.get("building_count", 0),
            "model": ev.get("model", "—"),
            "ts": ev.get("ts", ""),
            "export_format": fmt,
            "source": "single",
        })

    image_rows.sort(key=lambda r: r.get("ts", ""), reverse=True)

    # ── Aggregates ────────────────────────────────────────────────────────
    total_images = len(image_rows)
    model_usage: dict[str, int] = defaultdict(int)
    proc_times: list[float] = []
    # per-image processing times for chart: [{filename, processing_time, ts}]
    proc_time_rows: list[dict] = []

    for job in jobs:
        model = job.get("model", "")
        for item in job.get("items", []):
            if item.get("status") == "done" and model:
                model_usage[model] += 1

    for e in events:
        if e.get("event") == "segment":
            if "processing_time" in e:
                try:
                    pt = float(e["processing_time"])
                    proc_times.append(pt)
                    upload = upload_events.get(e.get("image_id", ""), {})
                    proc_time_rows.append({
                        "filename": upload.get("filename", e.get("image_id", "")[:8] + "…"),
                        "processing_time": pt,
                        "ts": e.get("ts", ""),
                    })
                except Exception:
                    pass
            if e.get("model"):
                model_usage[e["model"]] += 1

    # sort proc_time_rows oldest first for chart
    proc_time_rows.sort(key=lambda r: r.get("ts", ""))

    avg_proc_time = round(sum(proc_times) / len(proc_times), 2) if proc_times else 0
    total_proc_time_s = round(sum(proc_times), 1)

    # ── Errors last 24h ───────────────────────────────────────────────────
    cutoff_24h = datetime.now(timezone.utc) - timedelta(hours=24)
    errors_24h = 0
    for e in events:
        if e.get("level") not in ("error", "warning"):
            continue
        dt = _parse_ts(e.get("ts", ""))
        if dt and dt >= cutoff_24h:
            errors_24h += 1

    # ── Time in app: span from first to last event ────────────────────────
    all_ts = [_parse_ts(e.get("ts", "")) for e in events]
    all_ts = [t for t in all_ts if t is not None]
    if len(all_ts) >= 2:
        first_event = min(all_ts)
        last_event  = max(all_ts)
        total_app_time_s = int((last_event - first_event).total_seconds())
        first_seen = first_event.isoformat()
        last_seen  = last_event.isoformat()
    elif len(all_ts) == 1:
        total_app_time_s = 0
        first_seen = all_ts[0].isoformat()
        last_seen  = all_ts[0].isoformat()
    else:
        total_app_time_s = 0
        first_seen = None
        last_seen  = None

    # ── Export breakdown ──────────────────────────────────────────────────
    export_breakdown: dict[str, int] = defaultdict(int)
    for e in events:
        if e.get("event") == "export":
            fmt = e.get("export_format", "other").lower()
            export_breakdown[fmt] += 1

    return {
        "total_images_processed": total_images,
        "avg_processing_time_s": avg_proc_time,
        "total_processing_time_s": total_proc_time_s,
        "total_app_time_s": total_app_time_s,
        "first_seen": first_seen,
        "last_seen": last_seen,
        "errors_last_24h": errors_24h,
        "model_usage": dict(model_usage),
        "image_rows": image_rows,
        "proc_time_rows": proc_time_rows,
        "export_breakdown": dict(export_breakdown),
    }
