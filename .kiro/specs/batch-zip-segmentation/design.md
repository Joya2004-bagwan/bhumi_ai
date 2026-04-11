# Design Document: Batch ZIP Segmentation

## Overview

This feature extends the existing aerial image segmentation app with a batch processing workflow. Users upload a ZIP archive of aerial images, select a segmentation model, run building boundary detection across all images sequentially, review and edit per-image polygons, and download all results as a ZIP.

The design reuses the existing single-image pipeline (`POST /upload` → `POST /segment` → `POST /boundaries`) and the canvas-based polygon editor from `gptBoundaryDetector.js`. New backend endpoints handle ZIP ingestion, batch orchestration, and result packaging. A new frontend module `batchProcessor.js` drives the batch UI.

### Key Design Decisions

- **Sequential processing**: Images are processed one at a time on the backend to avoid GPU memory contention across the existing model adapters.
- **Polling for progress**: The frontend polls a `GET /api/batch/{batch_id}/status` endpoint rather than using WebSockets, keeping the transport layer simple and consistent with the existing fetch-based API.
- **In-memory batch state**: Batch job state is held in a server-side Python dict keyed by `batch_id`. This is sufficient for a single-user local tool; no database is required.
- **JSON-only output format**: Per the confirmed requirements, the download ZIP contains one JSON file per image using the agreed schema (`filename`, `building_count`, `polygons`). PNG/JPEG rendered output is also supported via the same download endpoint with a `format` query parameter.
- **Max images per ZIP**: 50 images per batch to prevent runaway processing times.

---

## Architecture

```mermaid
flowchart TD
    subgraph Frontend [Frontend - Vite Vanilla JS :3000]
        BP[batchProcessor.js]
        PE[Polygon Editor\n(reused from gptBoundaryDetector.js)]
        BP --> PE
    end

    subgraph Backend [Backend - FastAPI :8000]
        BU[POST /api/batch/upload-zip]
        BR[POST /api/batch/{batch_id}/run]
        BS[GET  /api/batch/{batch_id}/status]
        BD[GET  /api/batch/{batch_id}/download]
        RI[POST /api/batch/{batch_id}/items/{item_id}/retry]
        STATE[(In-memory\nbatch state dict)]
        BU --> STATE
        BR --> STATE
        BS --> STATE
        BD --> STATE
        RI --> STATE
    end

    subgraph Existing [Existing Pipeline]
        UP[POST /upload]
        SEG[POST /segment]
        BND[POST /boundaries]
    end

    BP -->|1. upload ZIP| BU
    BP -->|2. run batch| BR
    BP -->|3. poll status| BS
    BP -->|4. download| BD
    BR -->|reuses per-image| UP
    BR -->|reuses per-image| SEG
    BR -->|reuses per-image| BND
```

The batch run endpoint calls the existing upload/segment/boundaries logic internally (function calls, not HTTP round-trips) to avoid network overhead and keep error handling centralised.

---

## Components and Interfaces

### Backend: New Endpoints

#### `POST /api/batch/upload-zip`
- Accepts `multipart/form-data` with a single `file` field (`.zip`).
- Validates: extension is `.zip`, size ≤ 500 MB, contains at least one supported image, contains ≤ 50 images.
- Extracts images to `backend/uploads/batch/{batch_id}/images/`.
- Creates a `BatchJob` record in the in-memory state dict.
- Returns `BatchUploadResponse`.

#### `POST /api/batch/{batch_id}/run`
- Accepts `BatchRunRequest` (`model` name).
- Validates `batch_id` exists and job is in `uploaded` state.
- Starts sequential processing loop (async, `asyncio` task) — for each item: upload image → segment → detect boundaries → store result.
- Returns `{ "status": "started" }` immediately; progress is polled separately.

#### `GET /api/batch/{batch_id}/status`
- Returns `BatchStatusResponse` with overall job state and per-item states.

#### `GET /api/batch/{batch_id}/download`
- Query param: `format` — one of `json`, `png`, `jpeg` (default `json`).
- Packages results into a ZIP and streams it as `application/zip`.
- For `json`: one `{original_filename}_result.json` per item.
- For `png`/`jpeg`: one rendered image per item with polygons drawn on the original.

#### `POST /api/batch/{batch_id}/items/{item_id}/retry`
- Re-runs segment + boundary detection for a single failed item.
- Returns updated `BatchItem` state.

### Frontend: `batchProcessor.js`

New ES module class `BatchProcessor` wired into `index.js`.

Key methods:
- `init()` — renders the batch section HTML, attaches event listeners.
- `_uploadZip(file)` — POSTs to `/api/batch/upload-zip`, stores `batch_id`.
- `_runBatch()` — POSTs to `/api/batch/{batch_id}/run`, starts polling.
- `_pollStatus()` — `setInterval` every 2 s calling `GET /api/batch/{batch_id}/status`; stops when job is `complete` or `failed`.
- `_renderThumbnailGrid(items)` — renders thumbnail cards with status badges.
- `_openEditor(item)` — instantiates a `BatchPolygonEditor` (thin wrapper around the existing SVG editor logic) for the selected item.
- `_saveEdits(itemId, polygons)` — stores updated polygons in local state.
- `_downloadAll(format)` — triggers `GET /api/batch/{batch_id}/download?format={format}`.

### Frontend: `batchPolygonEditor.js`

Thin wrapper that reuses the SVG polygon editing logic extracted from `GPTBoundaryDetector`. Accepts `{ imageUrl, polygons }`, renders the editor in a modal overlay, and calls a `onSave(polygons)` callback on save.

---

## Data Models

### Backend (Python / Pydantic)

```python
from enum import Enum
from pydantic import BaseModel
from typing import Optional

class ItemStatus(str, Enum):
    pending    = "pending"
    processing = "processing"
    done       = "done"
    failed     = "failed"

class JobStatus(str, Enum):
    uploaded   = "uploaded"
    running    = "running"
    complete   = "complete"
    failed     = "failed"

class Polygon(BaseModel):
    id: int
    coordinates: list[list[float]]  # [[x1,y1],[x2,y2],...]

class BatchItem(BaseModel):
    item_id: str
    original_filename: str
    image_id: Optional[str] = None          # assigned after /upload
    status: ItemStatus = ItemStatus.pending
    error: Optional[str] = None
    building_count: int = 0
    polygons: list[Polygon] = []
    edited: bool = False                    # True if user saved edits

class BatchJob(BaseModel):
    batch_id: str
    status: JobStatus = JobStatus.uploaded
    model: Optional[str] = None
    items: list[BatchItem] = []
    created_at: str

# --- Request / Response models ---

class BatchUploadResponse(BaseModel):
    batch_id: str
    filenames: list[str]
    total_images: int

class BatchRunRequest(BaseModel):
    model: str

class BatchStatusResponse(BaseModel):
    batch_id: str
    status: JobStatus
    model: Optional[str]
    items: list[BatchItem]
    total: int
    done: int
    failed: int

class BatchItemUpdateRequest(BaseModel):
    polygons: list[Polygon]
```

### JSON Output Schema (per image)

```json
{
  "filename": "image1.png",
  "building_count": 3,
  "polygons": [
    { "id": 1, "coordinates": [[x1,y1],[x2,y2],...] }
  ]
}
```

### Frontend State (in `batchProcessor.js`)

```js
// Held in this._state
{
  batchId: "uuid",
  status: "running" | "complete" | "failed" | null,
  model: "sam2",
  items: [
    {
      item_id: "uuid",
      original_filename: "img.png",
      status: "pending" | "processing" | "done" | "failed",
      error: null,
      building_count: 0,
      polygons: [],   // [{ id, coordinates }]
      edited: false
    }
  ],
  outputFormat: "json"
}
```

---

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system — essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

