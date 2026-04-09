"""Batch processing router: ZIP upload, run, status, download."""

import os
import io
import json
import logging
import uuid
import zipfile
import shutil
import asyncio
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, StreamingResponse

from ..config import (
    BATCH_DIR, MASK_DIR,
    MAX_BATCH_ZIP_SIZE, MAX_BATCH_IMAGES, SUPPORTED_IMAGE_EXTS,
    image_processor, model_manager,
)
from ..schemas import (
    BatchItem, BatchJob, ItemStatus, JobStatus,
    BatchUploadResponse, BatchWorldfileUploadResponse,
    BatchRunRequest, BatchStatusResponse,
)
from ...utils.gpt_boundary import GPTBoundaryExtractor
from ...utils.worldfile import WorldFile
from ...utils.geojson_exporter import GeoJSONExporter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/batch")

WORLD_FILE_EXTS = {".pgw", ".tfw", ".jgw", ".wld"}
JOBS_FILE = BATCH_DIR / "jobs.json"


# ── Persistence helpers ───────────────────────────────────────────────────────

def _load_jobs() -> dict[str, BatchJob]:
    """Load batch_jobs from jobs.json on startup. Missing/corrupt file → empty dict."""
    if not JOBS_FILE.exists():
        return {}
    try:
        raw = json.loads(JOBS_FILE.read_text(encoding="utf-8"))
        jobs: dict[str, BatchJob] = {}
        for batch_id, data in raw.items():
            try:
                jobs[batch_id] = BatchJob.model_validate(data)
            except Exception as e:
                logger.warning(f"Skipping corrupt job {batch_id}: {e}")
        logger.info(f"Loaded {len(jobs)} batch job(s) from {JOBS_FILE}")
        return jobs
    except Exception as e:
        logger.warning(f"Could not load jobs.json: {e}")
        return {}


def _save_jobs(jobs: dict[str, BatchJob]) -> None:
    """Persist batch_jobs to jobs.json atomically (write to .tmp then rename)."""
    try:
        BATCH_DIR.mkdir(parents=True, exist_ok=True)
        tmp = JOBS_FILE.with_suffix(".tmp")
        payload = {bid: job.model_dump() for bid, job in jobs.items()}
        tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        tmp.replace(JOBS_FILE)
    except Exception as e:
        logger.error(f"Failed to persist jobs.json: {e}")


# In-memory batch store — populated from disk on module load
batch_jobs: dict[str, BatchJob] = _load_jobs()


@router.get("/{batch_id}/items/{item_id}/image")
async def get_batch_item_image(batch_id: str, item_id: str):
    """Serve the original image for a batch item."""
    job = batch_jobs.get(batch_id)
    if not job:
        raise HTTPException(status_code=404, detail="Batch job not found.")
    item = next((i for i in job.items if i.item_id == item_id), None)
    if not item or not item.image_path:
        raise HTTPException(status_code=404, detail="Item image not found.")
    p = Path(item.image_path)
    if not p.exists():
        raise HTTPException(status_code=404, detail="Image file not found.")
    return FileResponse(str(p))


@router.post("/upload-zip", response_model=BatchUploadResponse)
async def upload_zip(file: UploadFile = File(...)):
    """Upload a ZIP of images for batch processing."""
    if not (file.filename or "").lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Only .zip files are accepted.")

    contents = await file.read()
    if len(contents) > MAX_BATCH_ZIP_SIZE:
        raise HTTPException(status_code=413, detail=f"ZIP file exceeds {MAX_BATCH_ZIP_SIZE // (1024*1024)} MB limit.")

    if not zipfile.is_zipfile(io.BytesIO(contents)):
        raise HTTPException(status_code=400, detail="Uploaded file is not a valid ZIP archive.")

    batch_id = str(uuid.uuid4())
    batch_img_dir = BATCH_DIR / batch_id / "images"
    batch_img_dir.mkdir(parents=True, exist_ok=True)

    items: list[BatchItem] = []
    with zipfile.ZipFile(io.BytesIO(contents)) as zf:
        image_members = [
            m for m in zf.namelist()
            if Path(m).suffix.lower() in SUPPORTED_IMAGE_EXTS and not m.startswith("__MACOSX")
        ]
        if not image_members:
            shutil.rmtree(BATCH_DIR / batch_id, ignore_errors=True)
            raise HTTPException(status_code=400, detail="ZIP contains no supported image files (jpg, jpeg, png, tiff, tif).")
        if len(image_members) > MAX_BATCH_IMAGES:
            shutil.rmtree(BATCH_DIR / batch_id, ignore_errors=True)
            raise HTTPException(status_code=400, detail=f"ZIP contains more than {MAX_BATCH_IMAGES} images.")

        for member in image_members:
            item_id = str(uuid.uuid4())
            original_filename = Path(member).name
            src_ext = Path(member).suffix.lower()

            # Browsers can't render TIFF — convert to PNG at ingest time.
            # The original_filename is preserved so world-file matching still works.
            if src_ext in ('.tif', '.tiff'):
                from PIL import Image as _PILImage
                import io as _io
                raw = zf.read(member)
                with _PILImage.open(_io.BytesIO(raw)) as im:
                    if im.mode != 'RGB':
                        im = im.convert('RGB')
                    dest = batch_img_dir / f"{item_id}.png"
                    im.save(str(dest), format='PNG')
            else:
                dest = batch_img_dir / f"{item_id}{src_ext}"
                dest.write_bytes(zf.read(member))

            items.append(BatchItem(item_id=item_id, original_filename=original_filename, image_path=str(dest)))

    job = BatchJob(batch_id=batch_id, status=JobStatus.uploaded, items=items, created_at=datetime.now(timezone.utc).isoformat())
    batch_jobs[batch_id] = job
    _save_jobs(batch_jobs)
    logger.info(f"Batch uploaded: batch_id={batch_id}, images={len(items)}")
    return BatchUploadResponse(batch_id=batch_id, filenames=[i.original_filename for i in items], total=len(items))


@router.post("/{batch_id}/upload-worldfiles-zip", response_model=BatchWorldfileUploadResponse)
async def upload_worldfiles_zip(batch_id: str, file: UploadFile = File(...)):
    """
    Upload a ZIP of world files (.pgw / .tfw / .jgw / .wld) for a batch job.
    Files are matched to images by base name (case-insensitive).
    Must be called after /upload-zip and before /run.
    """
    job = batch_jobs.get(batch_id)
    if not job:
        raise HTTPException(status_code=404, detail="Batch job not found.")
    if job.status not in (JobStatus.uploaded,):
        raise HTTPException(status_code=400, detail="World files can only be uploaded before the job is started.")

    if not (file.filename or "").lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Only .zip files are accepted.")

    contents = await file.read()
    if not zipfile.is_zipfile(io.BytesIO(contents)):
        raise HTTPException(status_code=400, detail="Uploaded file is not a valid ZIP archive.")

    wf_dir = BATCH_DIR / batch_id / "worldfiles"
    wf_dir.mkdir(parents=True, exist_ok=True)

    # Extract world files from ZIP
    saved: dict[str, Path] = {}  # lowercase stem → path
    with zipfile.ZipFile(io.BytesIO(contents)) as zf:
        wf_members = [
            m for m in zf.namelist()
            if Path(m).suffix.lower() in WORLD_FILE_EXTS and not m.startswith("__MACOSX")
        ]
        if not wf_members:
            raise HTTPException(status_code=400, detail="ZIP contains no world files (.pgw, .tfw, .jgw, .wld).")

        for member in wf_members:
            p = Path(member)
            dest = wf_dir / p.name
            dest.write_bytes(zf.read(member))
            saved[p.stem.lower()] = dest

    # Match world files to batch items by base name (case-insensitive)
    matched = 0
    unmatched_images: list[str] = []
    for item in job.items:
        stem = Path(item.original_filename).stem.lower()
        if stem in saved:
            item.worldfile_path = str(saved[stem])
            matched += 1
        else:
            item.worldfile_path = ""
            unmatched_images.append(item.original_filename)

    job.has_worldfiles = True
    _save_jobs(batch_jobs)
    logger.info(f"World files uploaded: batch_id={batch_id}, matched={matched}, unmatched={len(unmatched_images)}")
    return BatchWorldfileUploadResponse(
        batch_id=batch_id,
        matched=matched,
        unmatched=len(unmatched_images),
        unmatched_images=unmatched_images,
    )


async def _run_batch_job(batch_id: str):
    """Background task: sequentially segment + detect boundaries + generate GeoJSON for each item."""
    job = batch_jobs.get(batch_id)
    if not job:
        return

    batch_mask_dir = BATCH_DIR / batch_id / "masks"
    batch_mask_dir.mkdir(parents=True, exist_ok=True)
    batch_geojson_dir = BATCH_DIR / batch_id / "geojson"
    batch_geojson_dir.mkdir(parents=True, exist_ok=True)

    api_key = os.getenv("OPENAI_API_KEY", "")
    extractor = GPTBoundaryExtractor(api_key=api_key)

    for item in job.items:
        item.status = ItemStatus.processing
        try:
            img_path = Path(item.image_path)
            image_array = image_processor.load_image(str(img_path))
            original_bgr = cv2.cvtColor(image_array, cv2.COLOR_RGB2BGR)

            mask = model_manager.segment(image_array, job.model)
            mask_filename = f"{item.item_id}-mask.png"
            mask_path = batch_mask_dir / mask_filename
            image_processor.save_mask(mask, str(mask_path))
            item.mask_path = str(mask_path)

            mask_gray = mask if len(mask.shape) == 2 else cv2.cvtColor(mask, cv2.COLOR_RGB2GRAY)
            model_obj = model_manager.get_model(job.model)
            if hasattr(model_obj, 'instance_segment'):
                instance_masks = model_obj.instance_segment(image_array)
            else:
                instance_masks = [mask_gray]

            result = await extractor.process_async(original_bgr, instance_masks)
            item.polygons = result["polygons"]
            item.building_count = len(result["polygons"])

            # GeoJSON generation — only if a matching world file was provided
            if item.worldfile_path:
                try:
                    wf = WorldFile(item.worldfile_path)
                    exporter = GeoJSONExporter(wf)
                    geojson = exporter.mask_to_geojson(mask_gray)
                    stem = Path(item.original_filename).stem
                    geojson_path = batch_geojson_dir / f"{stem}.geojson"
                    geojson_path.write_text(json.dumps(geojson, indent=2))
                    item.geojson_path = str(geojson_path)
                    logger.info(f"GeoJSON written: {geojson_path}, features={len(geojson['features'])}")
                except Exception as geo_err:
                    item.geojson_error = f"GeoJSON failed: {geo_err}"
                    logger.warning(f"GeoJSON generation failed for {item.item_id}: {geo_err}")
            else:
                item.geojson_error = "No matching world file — GeoJSON not generated"

            item.status = ItemStatus.done
            logger.info(f"Batch item done: item_id={item.item_id}, buildings={len(result['polygons'])}")
        except Exception as e:
            item.status = ItemStatus.failed
            item.error = str(e)
            logger.error(f"Batch item failed: item_id={item.item_id}, error={e}")

        _save_jobs(batch_jobs)
        await asyncio.sleep(0)

    all_failed = all(i.status == ItemStatus.failed for i in job.items)
    job.status = JobStatus.failed if all_failed else JobStatus.complete
    _save_jobs(batch_jobs)
    logger.info(f"Batch job complete: batch_id={batch_id}, status={job.status}")


@router.post("/{batch_id}/run")
async def run_batch(batch_id: str, request: BatchRunRequest, background_tasks: BackgroundTasks):
    """Start sequential batch processing."""
    job = batch_jobs.get(batch_id)
    if not job:
        raise HTTPException(status_code=404, detail="Batch job not found.")
    if job.status != JobStatus.uploaded:
        raise HTTPException(status_code=400, detail=f"Job is already in state '{job.status}'.")

    available_models = model_manager.get_available_models()
    if request.model not in available_models:
        raise HTTPException(status_code=400, detail=f"Invalid model. Supported: {', '.join(available_models)}")

    job.model = request.model
    job.status = JobStatus.running
    _save_jobs(batch_jobs)
    background_tasks.add_task(_run_batch_job, batch_id)
    return {"status": "started"}


@router.get("/{batch_id}/status", response_model=BatchStatusResponse)
async def get_batch_status(batch_id: str):
    """Poll batch job progress."""
    job = batch_jobs.get(batch_id)
    if not job:
        raise HTTPException(status_code=404, detail="Batch job not found.")

    counts = {s: 0 for s in ItemStatus}
    for item in job.items:
        counts[item.status] += 1

    return BatchStatusResponse(
        batch_id=batch_id, status=job.status, total=len(job.items),
        done=counts[ItemStatus.done], failed=counts[ItemStatus.failed],
        pending=counts[ItemStatus.pending], processing=counts[ItemStatus.processing],
        items=job.items,
        has_worldfiles=job.has_worldfiles,
    )


@router.post("/{batch_id}/items/{item_id}/polygons")
async def update_item_polygons(batch_id: str, item_id: str, body: dict):
    """Save edited polygons for a single batch item."""
    job = batch_jobs.get(batch_id)
    if not job:
        raise HTTPException(status_code=404, detail="Batch job not found.")
    item = next((i for i in job.items if i.item_id == item_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found.")
    item.polygons = body.get("polygons", item.polygons)
    item.building_count = len(item.polygons)
    _save_jobs(batch_jobs)
    return {"status": "ok"}


@router.post("/{batch_id}/items/{item_id}/retry")
async def retry_batch_item(batch_id: str, item_id: str, background_tasks: BackgroundTasks):
    """Retry a failed batch item."""
    job = batch_jobs.get(batch_id)
    if not job:
        raise HTTPException(status_code=404, detail="Batch job not found.")
    item = next((i for i in job.items if i.item_id == item_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found.")
    if item.status != ItemStatus.failed:
        raise HTTPException(status_code=400, detail="Only failed items can be retried.")

    async def _retry():
        item.status = ItemStatus.processing
        item.error = ""
        try:
            api_key = os.getenv("OPENAI_API_KEY", "")
            extractor = GPTBoundaryExtractor(api_key=api_key)

            img_path = Path(item.image_path)
            image_array = image_processor.load_image(str(img_path))
            original_bgr = cv2.cvtColor(image_array, cv2.COLOR_RGB2BGR)

            mask = model_manager.segment(image_array, job.model)
            batch_mask_dir = BATCH_DIR / batch_id / "masks"
            mask_path = batch_mask_dir / f"{item.item_id}-mask.png"
            image_processor.save_mask(mask, str(mask_path))
            item.mask_path = str(mask_path)

            mask_gray = mask if len(mask.shape) == 2 else cv2.cvtColor(mask, cv2.COLOR_RGB2GRAY)
            model_obj = model_manager.get_model(job.model)
            if hasattr(model_obj, 'instance_segment'):
                instance_masks = model_obj.instance_segment(image_array)
            else:
                instance_masks = [mask_gray]

            result = await extractor.process_async(original_bgr, instance_masks)
            item.polygons = result["polygons"]
            item.building_count = len(result["polygons"])

            # Re-generate GeoJSON if world file is available
            if item.worldfile_path:
                try:
                    wf = WorldFile(item.worldfile_path)
                    exporter = GeoJSONExporter(wf)
                    geojson = exporter.mask_to_geojson(mask_gray)
                    batch_geojson_dir = BATCH_DIR / batch_id / "geojson"
                    batch_geojson_dir.mkdir(exist_ok=True)
                    stem = Path(item.original_filename).stem
                    geojson_path = batch_geojson_dir / f"{stem}.geojson"
                    geojson_path.write_text(json.dumps(geojson, indent=2))
                    item.geojson_path = str(geojson_path)
                    item.geojson_error = ""
                except Exception as geo_err:
                    item.geojson_error = f"GeoJSON failed: {geo_err}"
            else:
                item.geojson_error = "No matching world file — GeoJSON not generated"

            item.status = ItemStatus.done
        except Exception as e:
            item.status = ItemStatus.failed
            item.error = str(e)
        _save_jobs(batch_jobs)

    background_tasks.add_task(_retry)
    return {"status": "retrying"}


@router.get("/{batch_id}/download")
async def download_batch(batch_id: str, format: str = "json"):
    """Download all processed results as a ZIP. format: json | png | jpeg | geojson"""
    job = batch_jobs.get(batch_id)
    if not job:
        raise HTTPException(status_code=404, detail="Batch job not found.")

    done_items = [i for i in job.items if i.status == ItemStatus.done]
    if not done_items:
        raise HTTPException(status_code=400, detail="No successfully processed items to download.")

    if format not in ("json", "png", "jpeg", "geojson"):
        raise HTTPException(status_code=400, detail="Format must be json, png, jpeg, or geojson.")

    # GeoJSON download: only items that have a generated geojson file
    if format == "geojson":
        geojson_items = [i for i in done_items if i.geojson_path and Path(i.geojson_path).exists()]
        if not geojson_items:
            raise HTTPException(
                status_code=400,
                detail="No GeoJSON files available. Upload a world files ZIP before running the batch."
            )
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for item in geojson_items:
                stem = Path(item.original_filename).stem
                zf.write(item.geojson_path, arcname=f"{stem}.geojson")
        buf.seek(0)
        return StreamingResponse(
            buf, media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename=batch_{batch_id}_geojson.zip"}
        )

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for item in done_items:
            stem = Path(item.original_filename).stem

            if format == "json":
                normalised = []
                for p in item.polygons:
                    normalised.append({"points": p} if isinstance(p, list) else p)
                data = {"filename": item.original_filename, "building_count": item.building_count, "polygons": normalised}
                zf.writestr(f"{stem}_output.json", json.dumps(data, indent=2))
            else:
                img_path = Path(item.image_path)
                image_array = image_processor.load_image(str(img_path))
                render = cv2.cvtColor(image_array, cv2.COLOR_RGB2BGR)
                for building in item.polygons:
                    pts = building if isinstance(building, list) else (building.get("points") or building.get("coordinates") or []) if isinstance(building, dict) else []
                    if pts:
                        pts_arr = np.array(pts, dtype=np.int32).reshape((-1, 1, 2))
                        cv2.polylines(render, [pts_arr], isClosed=True, color=(0, 255, 0), thickness=2)
                ext = ".jpg" if format == "jpeg" else ".png"
                _, encoded = cv2.imencode(ext, render)
                zf.writestr(f"{stem}_output{ext}", encoded.tobytes())

    buf.seek(0)
    return StreamingResponse(buf, media_type="application/zip", headers={"Content-Disposition": f"attachment; filename=batch_{batch_id}_results.zip"})
