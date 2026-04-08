"""Pydantic request/response schemas for the API."""

from enum import Enum
from pydantic import BaseModel


# ── Error ────────────────────────────────────────────────────────────────────

class ErrorResponse(BaseModel):
    detail: str
    timestamp: str
    path: str = ""


# ── Segmentation ─────────────────────────────────────────────────────────────

class UploadResponse(BaseModel):
    image_id: str
    image_url: str
    width: int
    height: int


class SegmentRequest(BaseModel):
    image_id: str
    model: str


class SegmentResponse(BaseModel):
    mask_url: str
    mask_base64: str
    processing_time: float
    model_used: str


class ModelInfo(BaseModel):
    name: str
    display_name: str
    description: str


class ModelsResponse(BaseModel):
    models: list[ModelInfo]


# ── Boundaries ───────────────────────────────────────────────────────────────

class BoundaryRequest(BaseModel):
    image_id: str
    model: str


class BoundaryResponse(BaseModel):
    buildings: list
    total_buildings: int
    processing_time: float


class GPTBoundaryRequest(BaseModel):
    image_id: str
    model: str  # yolov8m-custom | maskrcnn-custom


class GPTBoundaryResponse(BaseModel):
    gpt_overlay_b64: str
    opencv_overlay_b64: str
    building_count: int
    polygons: list
    processing_time_s: float
    fallback_count: int
    gpt_count: int = 0
    fallback_reasons: dict = {}
    image_url: str = ""


# ── Batch ────────────────────────────────────────────────────────────────────

class ItemStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    done = "done"
    failed = "failed"


class JobStatus(str, Enum):
    uploaded = "uploaded"
    running = "running"
    complete = "complete"
    failed = "failed"


class BatchItem(BaseModel):
    item_id: str
    original_filename: str
    image_path: str = ""
    mask_path: str = ""
    worldfile_path: str = ""       # path to matched .pgw file (empty if none)
    geojson_path: str = ""         # path to generated .geojson file (empty until done)
    geojson_error: str = ""        # per-item GeoJSON error (missing pgw, export failure)
    status: ItemStatus = ItemStatus.pending
    error: str = ""
    polygons: list = []
    building_count: int = 0


class BatchJob(BaseModel):
    batch_id: str
    status: JobStatus = JobStatus.uploaded
    model: str = ""
    items: list[BatchItem] = []
    created_at: str = ""
    has_worldfiles: bool = False   # True once a worldfiles ZIP has been uploaded


class BatchUploadResponse(BaseModel):
    batch_id: str
    filenames: list[str]
    total: int


class BatchWorldfileUploadResponse(BaseModel):
    batch_id: str
    matched: int        # images that have a matching world file
    unmatched: int      # images with no matching world file
    unmatched_images: list[str]  # filenames of unmatched images


class BatchRunRequest(BaseModel):
    model: str


class BatchStatusResponse(BaseModel):
    batch_id: str
    status: str
    total: int
    done: int
    failed: int
    pending: int
    processing: int
    items: list[BatchItem]
    has_worldfiles: bool = False
# ── GeoJSON Export ───────────────────────────────────────────────────────────

class WorldFileUploadResponse(BaseModel):
    image_id: str
    world_file_id: str
    message: str


class GeoJSONSegmentRequest(BaseModel):
    image_id: str
    world_file_id: str
    model: str
    min_area: float = 100.0
    simplify_tolerance: float = 1.0


class GeoJSONSegmentResponse(BaseModel):
    geojson: dict
    feature_count: int
    processing_time: float
    model_used: str
    crs_info: dict
