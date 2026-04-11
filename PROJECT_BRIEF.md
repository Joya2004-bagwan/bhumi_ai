# BHUMI AI — Project Brief

## Table of Contents

1. [Overview](#overview)
2. [What the Tool Does](#what-the-tool-does)
3. [Tech Stack](#tech-stack)
4. [System Architecture](#system-architecture)
5. [Frontend Implementation](#frontend-implementation)
6. [Backend Implementation](#backend-implementation)
7. [Machine Learning Models](#machine-learning-models)
8. [API Reference](#api-reference)
9. [Data Flow & Workflows](#data-flow--workflows)
10. [GeoJSON & Georeferencing](#geojson--georeferencing)
11. [Batch Processing](#batch-processing)
12. [Configuration & Environment](#configuration--environment)
13. [Project Structure](#project-structure)
14. [Running the Application](#running-the-application)

---

## Overview

BHUMI AI is a full-stack web application for automated building detection and boundary extraction from aerial, drone, and satellite imagery. It combines deep learning segmentation models with an interactive browser-based interface, allowing users to upload imagery, run AI inference, review and edit detected building polygons, and export results in multiple formats including GeoJSON with real-world coordinates.

The name "BHUMI" reflects the application's domain — earth observation and land-use analysis through aerial imagery.

---

## What the Tool Does

At its core, BHUMI AI solves a specific problem in geospatial analysis: identifying building footprints from overhead imagery without manual digitization. The tool automates what would otherwise be a time-consuming manual process of tracing building outlines on maps.

### Primary Capabilities

**Single Image Segmentation**
Upload a single aerial or satellite image (JPEG, PNG, TIFF up to 50MB). Select a model, run segmentation, and get back a binary mask highlighting all detected buildings. The mask is overlaid on the original image for visual review.

**Boundary Detection**
After segmentation, two boundary extraction methods are available:
- OpenCV contour-based detection with Douglas-Peucker polygon simplification
- Per-instance minAreaRect detection that fits tight rotated rectangles around each building

**Interactive Polygon Editing**
Detected building polygons are rendered as an SVG overlay. Users can drag vertices, delete polygons, or draw new ones before exporting.

**Batch Processing**
Upload a ZIP archive containing up to 50 images (500MB limit). The backend processes each image sequentially, tracking per-image status. Users can monitor progress, retry failed items, edit polygons per image, and download all results as a ZIP.

**GeoJSON Export with Georeferencing**
Upload a world file (.pgw, .tfw, .jgw, .wld) alongside an image to enable coordinate transformation. The exported GeoJSON contains real-world geographic coordinates instead of pixel coordinates, making results directly usable in GIS tools like QGIS or ArcGIS.

**Export Formats**
- JSON (polygon coordinates + building count)
- PNG / JPEG (original image with polygon overlays rendered)
- GeoJSON (georeferenced building footprints as a FeatureCollection)

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Vanilla ES6+ JavaScript, Vite 5, CSS3 |
| Backend | Python 3.9+, FastAPI, Uvicorn |
| ML — Detection | Ultralytics YOLOv8m-seg |
| ML — Segmentation | torchvision Mask R-CNN ResNet50-FPN |
| Image Processing | OpenCV, Pillow, NumPy, scikit-image |
| Geometry | Shapely (optional, for polygon validation) |
| Dev Tooling | Vite proxy, python-dotenv, pytest |

No frontend framework (React, Vue, etc.) is used. The UI is built entirely with vanilla JavaScript modules, which keeps the bundle small and avoids framework overhead for what is essentially a single-page tool.

---

## System Architecture

```
Browser (port 4000)
      │
      │  HTTP requests to /api/*, /upload, /segment, etc.
      ▼
Vite Dev Server (proxy)
      │
      │  Forwards API calls to localhost:8000
      ▼
FastAPI Backend (port 8000)
      │
      ├── /upload          → ImageProcessor → saves to uploads/images/
      ├── /segment         → ModelManager → YOLOv8 or MaskRCNN → saves mask
      ├── /boundaries      → BoundaryDetector → OpenCV contours
      ├── /api/gpt-boundaries → minAreaRect per instance
      ├── /api/batch/*     → BatchProcessor → sequential job runner
      └── /segment/geojson → GeoJSONExporter + WorldFile transform
```

The Vite dev server proxies all requests matching `/upload`, `/segment`, `/models`, `/boundaries`, `/api`, `/images`, `/masks`, and `/health` to the FastAPI backend. This means the frontend makes requests to its own origin and never deals with CORS in development.

Static files (uploaded images and generated masks) are served directly by FastAPI via `StaticFiles` mounts at `/images` and `/masks`.

---

## Frontend Implementation

The frontend is a single-page application (SPA) with client-side routing. There is no build-time framework — each feature is a self-contained ES6 module.

### Entry Point — `index.js`

The main controller initializes all components and handles page navigation. It reads the current page from a `data-page` attribute on the body or from URL hash routing, then mounts the appropriate components. On load it fetches available models from `/models` and populates the model selector.

### State Management — `appState.js`

A centralized state object holds:
- `currentImageId` — UUID of the uploaded image
- `currentModel` — selected model name
- `segmentationResult` — mask URL, base64 data, dimensions
- `detectedPolygons` — array of polygon coordinate arrays
- `processingLog` — timestamped list of operations for the dashboard

State is plain JavaScript (no reactive framework). Components read from and write to this object directly, with lightweight event emission for cross-component updates.

### Image Upload — `imageUploader.js`

Handles file selection via drag-and-drop or file input. Validates file type (JPEG, PNG, TIFF) and size client-side before sending a `multipart/form-data` POST to `/upload`. On success, stores the returned `image_id` in app state and triggers the model selector to appear.

### Model Selection — `modelSelector.js`

Fetches the model list from `GET /models` and renders a card-based UI. Each card shows the model name, architecture description, and a "best for" tag. Selecting a model stores the choice in app state and enables the segment button.

### Segmentation Runner — `segmentationRunner.js`

Posts `{image_id, model}` to `/segment`. While waiting, shows a spinner with elapsed time. On success, passes the mask URL and base64 data to the visualization panel and enables the boundary detection controls.

### Visualization Panel — `visualizationPanel.js`

Renders three side-by-side canvases:
- Original image
- Segmentation mask (white buildings on black background)
- Overlay (original image with semi-transparent mask blended on top)

Uses the Canvas 2D API to draw images from URLs or base64 data. Handles aspect ratio preservation and responsive resizing.

### Boundary Detection — `boundaryDetector.js`

Posts `{image_id}` to `/boundaries`. Receives a list of polygon coordinate arrays and renders them as SVG `<polygon>` elements overlaid on the visualization panel. Each polygon is clickable for selection.

### Enhanced Boundary Detection — `gptBoundaryDetector.js`

Posts to `/api/gpt-boundaries` which runs per-instance minAreaRect detection. Returns both polygon data and a pre-rendered overlay image. Provides an edit mode where users can:
- Drag individual polygon vertices
- Delete selected polygons
- Draw new polygons by clicking to place vertices

The editor uses SVG for polygon rendering with pointer event handlers for interaction.

### Batch Processor — `batchProcessor.js`

Manages the full batch workflow:
1. ZIP file upload to `/api/batch/upload-zip`
2. Starts the job via `/api/batch/{id}/run`
3. Polls `/api/batch/{id}/status` every 2 seconds
4. Renders a grid of image thumbnails with per-item status badges (pending / processing / done / failed)
5. Opens the polygon editor for individual items on click
6. Triggers download from `/api/batch/{id}/download`

### Batch Polygon Editor — `batchPolygonEditor.js`

A modal SVG editor for a single batch item. Loads the item's image and detected polygons, allows vertex-level editing, and saves changes back to `/api/batch/{id}/items/{item_id}/polygons`.

### Dashboard — `dashboard.js`

Displays session statistics: total images processed, total buildings detected, average processing time, and a scrollable log of recent operations. The log is populated from `appState.processingLog` and persists for the duration of the browser session.

### GeoJSON Exporter — `geojsonExporter.js`

Provides a world file upload input. When a world file is present, the segment button routes to `/segment/geojson` instead of `/segment`. The returned GeoJSON is offered as a file download.

### Styling

Two CSS files handle all styling:
- `theme.css` — CSS custom properties (design tokens) for colors, spacing, typography, and dark/light theme switching
- `app.css` — Layout, component styles, batch editor styles, responsive breakpoints

Theme switching is done by toggling a `data-theme="dark"` attribute on the root element, which swaps the CSS variable values.

---

## Backend Implementation

### Entry Point — `api/main.py`

Creates the FastAPI application instance, configures CORS middleware, mounts static file directories, registers exception handlers for 400/404/413/500 responses, and includes all routers. The `.env` file is loaded here via `python-dotenv` before any other imports resolve.

### Configuration — `api/config.py`

Loads environment variables (with its own `load_dotenv` call as a safety net for import order issues), resolves all directory paths relative to the `backend/` directory, creates upload directories if they don't exist, and instantiates the three shared service singletons:
- `image_processor` — `ImageProcessor` instance
- `model_manager` — `SegmentationModelManager` instance
- `boundary_detector` — `BoundaryDetector` instance

These singletons are imported by all routers, ensuring a single model manager instance across the application.

### Schemas — `api/schemas.py`

All Pydantic v2 request and response models live here. Key schemas include:
- `UploadResponse` — image_id, filename, dimensions
- `SegmentRequest` / `SegmentResponse` — model selection, mask URL, base64 mask, building count
- `BoundaryRequest` / `BoundaryResponse` — polygon lists
- `BatchUploadResponse` / `BatchStatusResponse` — batch job state
- `GeoJSONRequest` / `GeoJSONResponse` — georeferenced export

### Routers

**`routers/segmentation.py`**
- `GET /models` — returns the list of available model names and metadata
- `POST /upload` — validates file type and size, saves to `uploads/images/` with a UUID filename, returns image metadata
- `POST /segment` — loads the image, runs the selected model via `model_manager.segment()`, saves the mask, returns mask URL and base64-encoded mask

**`routers/boundaries.py`**
- `POST /boundaries` — loads the saved mask, runs `boundary_detector.detect()` which applies morphological operations and extracts contours, returns simplified polygon coordinates
- `POST /api/gpt-boundaries` — runs per-instance segmentation via `model.instance_segment()`, fits a `minAreaRect` to each instance, renders an overlay image, returns polygons and overlay

**`routers/batch.py`**
- `POST /api/batch/upload-zip` — validates ZIP, extracts images to `uploads/batch/{batch_id}/images/`, creates in-memory `BatchJob` object
- `POST /api/batch/{id}/run` — launches `_run_batch_job()` as a background task via FastAPI's `BackgroundTasks`
- `GET /api/batch/{id}/status` — returns current job and per-item status
- `POST /api/batch/{id}/items/{item_id}/polygons` — saves edited polygon data to the in-memory item
- `POST /api/batch/{id}/items/{item_id}/retry` — re-runs segmentation for a failed item
- `GET /api/batch/{id}/download` — renders all results into a ZIP and streams it back

**`routers/geojson.py`**
- `POST /upload/worldfile` — parses the world file and stores georeferencing parameters in a session dict keyed by a `worldfile_id`
- `POST /segment/geojson` — runs segmentation, passes the mask and optional world file to `GeoJSONExporter`, returns a GeoJSON FeatureCollection

### Utilities

**`utils/image_processor.py`**
Handles all image I/O: validating file extensions and sizes, loading images with Pillow, converting between numpy arrays and PIL Images, saving masks, and base64-encoding images for API responses.

**`utils/boundary_detector.py`**
Implements the OpenCV-based boundary extraction pipeline:
1. Apply morphological closing to fill small gaps in the mask
2. Find external contours with `cv2.findContours`
3. Simplify each contour with Douglas-Peucker (`cv2.approxPolyDP`)
4. Filter by minimum area
5. Optionally smooth with Shapely if available

Configurable parameters: `min_area`, `epsilon_factor`, `morph_kernel_size`, `morph_iterations`, `shapely_tolerance`.

**`utils/geojson_exporter.py`**
Converts a binary segmentation mask to a GeoJSON FeatureCollection:
1. Label connected components with `cv2.connectedComponents`
2. For each component above `min_area`, fit a `minAreaRect`
3. Transform pixel coordinates to world coordinates via `WorldFile` if provided
4. Optionally validate/repair polygons with Shapely
5. Return a standard GeoJSON structure

**`utils/worldfile.py`**
Parses world files (`.pgw`, `.tfw`, etc.) which contain six parameters defining an affine transformation from pixel space to geographic coordinates:
- Pixel width (x scale)
- Rotation terms (usually 0)
- Pixel height (y scale, usually negative)
- X coordinate of upper-left pixel center
- Y coordinate of upper-left pixel center

Exposes a `pixel_to_world(x, y)` method used by the GeoJSON exporter.

---

## Machine Learning Models

### Abstract Base Class — `segmentation_model.py`

All model adapters implement a common interface defined as a Python ABC:

```python
class SegmentationModel(ABC):
    def load(self) -> None: ...
    def preprocess(self, image: np.ndarray) -> Any: ...
    def predict(self, preprocessed_input: Any) -> Any: ...
    def postprocess(self, raw_output: Any) -> np.ndarray: ...
    def segment(self, image: np.ndarray) -> np.ndarray: ...
    def instance_segment(self, image: np.ndarray) -> list: ...
```

The `segment()` method is the standard pipeline: preprocess → predict → postprocess, returning a binary mask. `instance_segment()` returns a list of per-building masks, used by the enhanced boundary detection.

### Model Manager — `segmentation_model_manager.py`

A registry that maps model names to adapter classes and weight paths. Models are lazy-loaded — the adapter class is not even imported until the model is first requested. This keeps startup time fast and avoids loading PyTorch until needed.

The manager reads weight paths from environment variables (`YOLOV8_MODEL_PATH`, `MASKRCNN_MODEL_PATH`) with fallback to the `models/weights/` directory. Once loaded, models stay in memory for the lifetime of the server process.

### YOLOv8 Adapter — `yolov8_adapter.py`

Wraps the Ultralytics YOLOv8m-seg model. The adapter:
- Loads the `.pt` weights file via `ultralytics.YOLO`
- Runs inference with `model.predict()` returning instance masks and confidence scores
- Combines all instance masks above a confidence threshold into a single binary mask for `segment()`
- Returns individual instance masks for `instance_segment()`

Weight file: `best_fixed.pt` (~109MB), a YOLOv8m-seg model fine-tuned on a building dataset.

### Mask R-CNN Adapter — `maskrcnn_adapter.py`

Wraps torchvision's `maskrcnn_resnet50_fpn`. The adapter:
- Builds the model architecture (ResNet50-FPN backbone + custom box/mask predictors for 2 classes)
- Loads the `.pth` checkpoint, handling multiple checkpoint formats (`model_state_dict`, `state_dict`, or raw)
- Runs inference on CPU or CUDA depending on availability
- Filters detections by confidence threshold (default 0.5) and class label (building = 1)
- Combines instance masks with `np.maximum` for `segment()`
- Returns individual instance masks for `instance_segment()`

Weight file: `maskrcnn_building_best.pth` (~176MB), a Mask R-CNN model trained on building footprint data.

**Note on backbone weights:** torchvision's `maskrcnn_resnet50_fpn` with `pretrained=False` still attempts to download ImageNet-pretrained ResNet50 backbone weights from PyTorch Hub on first load. The `TORCH_HOME` environment variable controls where these are cached. If `XDG_CACHE_HOME` points to an inaccessible path (e.g., an unmounted external drive), this will fail with a permission error. Setting `TORCH_HOME` in `.env` to a local writable path resolves this.

---

## API Reference

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Health check, returns `{"status": "healthy"}` |
| GET | `/models` | List available models with metadata |
| POST | `/upload` | Upload single image, returns `image_id` |
| POST | `/segment` | Run segmentation on uploaded image |
| POST | `/boundaries` | OpenCV contour boundary detection |
| POST | `/api/gpt-boundaries` | Per-instance minAreaRect boundary detection |
| POST | `/upload/worldfile` | Upload georeferencing world file |
| POST | `/segment/geojson` | Segment and export as GeoJSON |
| POST | `/api/batch/upload-zip` | Upload ZIP for batch processing |
| POST | `/api/batch/{id}/run` | Start batch segmentation job |
| GET | `/api/batch/{id}/status` | Poll batch job progress |
| POST | `/api/batch/{id}/items/{item_id}/polygons` | Save edited polygons for batch item |
| POST | `/api/batch/{id}/items/{item_id}/retry` | Retry failed batch item |
| GET | `/api/batch/{id}/download` | Download batch results as ZIP |

---

## Data Flow & Workflows

### Single Image Workflow

```
1. User selects image file
   └─ Client validates type/size
   └─ POST /upload → {image_id, width, height}

2. User selects model
   └─ GET /models → model list rendered as cards

3. User clicks Segment
   └─ POST /segment {image_id, model}
   └─ Backend: load image → model.segment() → save mask
   └─ Response: {mask_url, mask_base64, building_count}
   └─ Frontend: render original / mask / overlay canvases

4. User clicks Detect Boundaries
   └─ POST /boundaries {image_id}  (or /api/gpt-boundaries)
   └─ Backend: load mask → extract contours → simplify polygons
   └─ Response: {polygons: [[x,y], ...]}
   └─ Frontend: render SVG polygon overlay

5. User edits polygons (optional)
   └─ Drag vertices, delete, draw new polygons in SVG editor

6. User exports
   └─ JSON: polygon data downloaded directly from state
   └─ PNG/JPEG: canvas rendered to blob and downloaded
   └─ GeoJSON: POST /segment/geojson with optional worldfile_id
```

### Batch Workflow

```
1. User uploads ZIP
   └─ POST /api/batch/upload-zip
   └─ Backend: extract images, create BatchJob, return batch_id

2. User selects model and starts job
   └─ POST /api/batch/{id}/run {model}
   └─ Backend: BackgroundTask runs _run_batch_job()
      └─ For each image: segment → detect boundaries → store polygons

3. Frontend polls status
   └─ GET /api/batch/{id}/status every 2s
   └─ Updates thumbnail grid with per-item status badges

4. User reviews and edits
   └─ Click thumbnail → open batchPolygonEditor modal
   └─ POST /api/batch/{id}/items/{item_id}/polygons to save

5. User downloads results
   └─ GET /api/batch/{id}/download?format=json|png|jpeg
   └─ Backend: render all items into ZIP, stream response
```

---

## GeoJSON & Georeferencing

World files are plain text files with six lines, each a single number:

```
0.5        ← pixel width in map units (x scale)
0.0        ← rotation about y axis (usually 0)
0.0        ← rotation about x axis (usually 0)
-0.5       ← pixel height in map units (y scale, negative = north-up)
500000.0   ← x coordinate of upper-left pixel center (easting)
4000000.0  ← y coordinate of upper-left pixel center (northing)
```

The `WorldFile` class applies this affine transform to convert pixel (col, row) to world (x, y):

```
x_world = x_scale * col + x_origin
y_world = y_scale * row + y_origin
```

The GeoJSON exporter uses `cv2.connectedComponents` to isolate individual buildings, fits a `cv2.minAreaRect` to each, and transforms the four corner points through the world file transform. The result is a standard GeoJSON FeatureCollection where each Feature is a building polygon with `area_pixels` as a property.

---

## Batch Processing

Batch jobs are stored entirely in memory as a Python dict (`batch_jobs: dict[str, BatchJob]`). There is no database or file-based persistence — if the server restarts, all batch state is lost.

Each `BatchJob` contains:
- `batch_id` — UUID string
- `status` — `uploaded | running | complete | failed`
- `model` — model name used for this batch
- `items` — list of `BatchItem` objects

Each `BatchItem` contains:
- `item_id` — UUID string
- `original_filename` — original name from the ZIP
- `image_path` — absolute path to saved image
- `mask_path` — absolute path to saved mask (set after processing)
- `status` — `pending | processing | done | failed`
- `polygons` — list of polygon coordinate arrays (set after boundary detection)
- `building_count` — integer count of detected buildings
- `error` — error message string if status is `failed`

Background processing runs sequentially (one image at a time) using FastAPI's `BackgroundTasks`. This avoids memory pressure from parallel model inference but means large batches take proportionally longer.

---

## Configuration & Environment

All configuration is in `backend/.env`. The file is loaded by both `api/main.py` and `api/config.py` (with `override=True`) to handle import order edge cases.

```env
HOST=0.0.0.0
PORT=8000

MAX_UPLOAD_SIZE_MB=50
MAX_BATCH_SIZE_MB=500
MAX_BATCH_IMAGES=50

YOLOV8_MODEL_PATH=/absolute/path/to/best_fixed.pt
MASKRCNN_MODEL_PATH=/absolute/path/to/maskrcnn_building_best.pth

TORCH_HOME=/home/user/.cache/torch

OPENAI_API_KEY=

CORS_ORIGINS=http://localhost:4000,http://127.0.0.1:4000
```

`TORCH_HOME` is important on systems where `XDG_CACHE_HOME` is set to an external or network drive. PyTorch's hub uses `TORCH_HOME` (falling back to `XDG_CACHE_HOME`) to cache downloaded backbone weights. Setting it explicitly to a local path prevents permission errors on first model load.

---

## Project Structure

```
.
├── Makefile                          # install / dev / stop targets
├── README.md
├── PROJECT_BRIEF.md
├── backend/
│   ├── .env                          # environment variables (not committed)
│   ├── .env.example                  # template
│   ├── requirements.txt
│   ├── run_server.py                 # alternative entry point
│   ├── pytest.ini
│   ├── api/
│   │   ├── main.py                   # FastAPI app, CORS, static mounts, routers
│   │   ├── config.py                 # paths, shared service singletons
│   │   ├── schemas.py                # all Pydantic request/response models
│   │   └── routers/
│   │       ├── segmentation.py       # /upload, /segment, /models
│   │       ├── boundaries.py         # /boundaries, /api/gpt-boundaries
│   │       ├── batch.py              # /api/batch/*
│   │       └── geojson.py            # /upload/worldfile, /segment/geojson
│   ├── models/
│   │   ├── segmentation_model.py     # abstract base class
│   │   ├── segmentation_model_manager.py
│   │   ├── yolov8_adapter.py
│   │   ├── maskrcnn_adapter.py
│   │   ├── unet_adapter.py           # stub, no weights
│   │   └── weights/
│   │       ├── best_fixed.pt         # YOLOv8m-seg weights (~109MB)
│   │       └── maskrcnn_building_best.pth  # Mask R-CNN weights (~176MB)
│   ├── utils/
│   │   ├── image_processor.py
│   │   ├── boundary_detector.py
│   │   ├── geojson_exporter.py
│   │   └── worldfile.py
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── test_api_setup.py
│   │   ├── test_segment_endpoint.py
│   │   ├── test_upload_endpoint.py
│   │   ├── test_models_endpoint.py
│   │   ├── test_segmentation_model.py
│   │   ├── test_segmentation_model_manager.py
│   │   ├── test_unet_adapter.py
│   │   ├── test_yolov8_adapter.py
│   │   ├── test_image_processor.py
│   │   ├── test_error_handling.py
│   │   └── test_segment_endpoint.py
│   └── uploads/
│       ├── images/                   # uploaded single images
│       ├── masks/                    # generated segmentation masks
│       └── batch/                    # batch job directories
└── frontend/
    ├── index.html                    # SPA shell
    ├── vite.config.js                # dev server port 4000, API proxy rules
    ├── package.json
    └── src/
        ├── index.js                  # app controller, page routing
        ├── appState.js               # centralized state
        ├── imageUploader.js
        ├── modelSelector.js
        ├── segmentationRunner.js
        ├── visualizationPanel.js
        ├── boundaryDetector.js
        ├── gptBoundaryDetector.js
        ├── batchProcessor.js
        ├── batchPolygonEditor.js
        ├── dashboard.js
        ├── geojsonExporter.js
        ├── theme.css                 # design tokens, dark/light themes
        └── app.css                   # layout and component styles
```

---

## Running the Application

**Prerequisites:** Python 3.9+, Node.js 18+, npm

```bash
# 1. Clone and set up environment
cp backend/.env.example backend/.env
# Edit backend/.env — set TORCH_HOME to a local writable path

# 2. Install dependencies
make install
# This creates backend/venv, installs Python packages, and runs npm install

# 3. Place model weights
# backend/models/weights/best_fixed.pt         (~109MB)
# backend/models/weights/maskrcnn_building_best.pth  (~176MB)

# 4. Start both servers
make dev
# Backend: http://localhost:8000
# Frontend: http://localhost:4000

# 5. Stop servers
make stop
```

Open **http://localhost:4000** in your browser.

To run backend tests:

```bash
cd backend
source venv/bin/activate
pytest
```
