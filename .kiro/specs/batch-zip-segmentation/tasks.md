# Implementation Plan: Batch ZIP Segmentation

## Overview

Extend the existing FastAPI + Vite vanilla JS app with a batch processing workflow: ZIP upload → model selection → sequential segmentation + boundary detection → per-image polygon editing → bulk ZIP download.

## Tasks

- [x] 1. Add backend data models and in-memory batch state
  - [x] 1.1 Define Pydantic models in `backend/api/main.py`: `ItemStatus`, `JobStatus`, `Polygon`, `BatchItem`, `BatchJob`, `BatchUploadResponse`, `BatchRunRequest`, `BatchStatusResponse`, `BatchItemUpdateRequest`
    - Add a module-level `batch_jobs: dict[str, BatchJob] = {}` store
    - _Requirements: 3.2, 3.3_
  - [ ]* 1.2 Write unit tests for Pydantic model validation
    - Test default field values, enum transitions, and optional fields
    - _Requirements: 3.2_

- [x] 2. Implement `POST /api/batch/upload-zip` endpoint
  - [x] 2.1 Add the endpoint to `backend/api/main.py`
    - Validate `.zip` extension and size ≤ 500 MB; raise HTTP 400/413 on failure
    - Extract images with supported extensions into `backend/uploads/batch/{batch_id}/images/`
    - Enforce max 50 images; reject with HTTP 400 if exceeded
    - Create a `BatchJob` entry in `batch_jobs` with `status=uploaded`
    - Return `BatchUploadResponse`
    - _Requirements: 1.2, 1.3, 1.6, 1.7, 1.8, 1.9_
  - [ ]* 2.2 Write property test for ZIP upload validation
    - **Property: Any ZIP with 0 supported images always returns HTTP 400**
    - **Validates: Requirements 1.7**
  - [ ]* 2.3 Write unit tests for upload endpoint
    - Test valid ZIP, oversized ZIP, non-ZIP file, empty ZIP, ZIP with >50 images
    - _Requirements: 1.2, 1.3, 1.7, 1.8_

- [x] 3. Implement `POST /api/batch/{batch_id}/run` endpoint
  - [x] 3.1 Add the endpoint to `backend/api/main.py`
    - Validate `batch_id` exists and job is in `uploaded` state
    - Store `model` on the `BatchJob`; set status to `running`
    - Launch an `asyncio` background task that iterates items sequentially:
      - For each item: call existing `upload_image` logic → `segment_image` logic → `detect_boundaries` logic (function calls, not HTTP)
      - Update `item.status` to `processing` before each item, then `done` or `failed`
    - Set job status to `complete` when all items finish (or `failed` if all fail)
    - Return `{"status": "started"}` immediately
    - _Requirements: 3.1, 3.2, 3.3, 3.5, 3.6_
  - [ ]* 3.2 Write unit tests for run endpoint
    - Test invalid `batch_id`, wrong job state, model validation
    - _Requirements: 3.1_

- [x] 4. Implement `GET /api/batch/{batch_id}/status` endpoint
  - [x] 4.1 Add the endpoint to `backend/api/main.py`
    - Return `BatchStatusResponse` with per-item states and aggregate counts (`total`, `done`, `failed`)
    - Raise HTTP 404 if `batch_id` not found
    - _Requirements: 3.3, 3.4_
  - [ ]* 4.2 Write property test for status consistency
    - **Property: `done + failed + pending + processing == total` always holds**
    - **Validates: Requirements 3.3**

- [x] 5. Implement `GET /api/batch/{batch_id}/download` endpoint
  - [x] 5.1 Add the endpoint to `backend/api/main.py`
    - Accept `format` query param (`json` | `png` | `jpeg`), default `json`
    - For `json`: build one `{original_filename}_output.json` per done item using the agreed schema (`filename`, `building_count`, `polygons`)
    - For `png`/`jpeg`: render polygons onto the original image using OpenCV and encode; output file named `{original_filename}_output.png` or `{original_filename}_output.jpg`
    - Package all files into an in-memory ZIP using `io.BytesIO` + `zipfile`
    - Stream response with `StreamingResponse` and `Content-Disposition: attachment`
    - Raise HTTP 404 if `batch_id` not found; HTTP 400 if no done items
    - _Requirements: 5.3, 5.4, 5.5, 5.6_
  - [ ]* 5.2 Write unit tests for download endpoint
    - Test JSON format output schema, PNG rendering, empty batch rejection
    - _Requirements: 5.4, 5.5_

- [x] 6. Implement `POST /api/batch/{batch_id}/items/{item_id}/retry` endpoint
  - [x] 6.1 Add the endpoint to `backend/api/main.py`
    - Validate `batch_id` and `item_id` exist; item must be in `failed` state
    - Re-run segment + boundary detection for that item only
    - Update item status and return updated `BatchItem`
    - _Requirements: 6.4_
  - [ ]* 6.2 Write unit tests for retry endpoint
    - Test retry of failed item, retry of non-failed item (should 400), unknown ids
    - _Requirements: 6.4_

- [ ] 7. Checkpoint — backend complete
  - Ensure all backend tests pass. Ask the user if questions arise.

- [x] 8. Create `frontend/src/batchProcessor.js`
  - [x] 8.1 Scaffold the `BatchProcessor` ES module class with `init()` method
    - Render the batch section HTML into `index.html` (ZIP upload input, upload button, model dropdown, run button, status area, thumbnail grid, format selector, download button)
    - The batch section must be visually separate from the existing single-image section
    - Wire all DOM event listeners inside `init()`
    - _Requirements: 1.1, 2.1, 5.1_
  - [x] 8.2 Implement `_uploadZip(file)` — client-side validation + POST to `/api/batch/upload-zip`
    - Validate `.zip` extension before sending; show error and reject on failure
    - Display filename, file size, and upload progress indicator during upload
    - On success: store `batch_id`, display extracted filenames list
    - On error: display descriptive message and allow retry
    - _Requirements: 1.2, 1.3, 1.4, 1.5, 1.10, 6.1_
  - [x] 8.3 Implement `_runBatch()` — POST to `/api/batch/{batch_id}/run` + start polling
    - Disable "Run Batch" button until ZIP uploaded and model selected
    - On click: POST run request, then call `_startPolling()`
    - _Requirements: 2.3, 3.1_
  - [x] 8.4 Implement `_startPolling()` / `_pollStatus()` — `setInterval` every 2 s on `GET /api/batch/{batch_id}/status`
    - Update per-image status badges (pending / processing / done / failed) in the thumbnail grid
    - Stop polling when job is `complete` or `failed`
    - On job complete: call `_renderThumbnailGrid(items)`
    - _Requirements: 3.4, 3.7_
  - [x] 8.5 Implement `_renderThumbnailGrid(items)` — render thumbnail cards
    - Each card shows: image thumbnail (served from `/images/`), status badge, edited indicator, retry button (if failed)
    - Clicking a done card opens the polygon editor
    - _Requirements: 4.1, 4.6, 6.2_
  - [x] 8.6 Implement `_saveEdits(itemId, polygons)` and discard-on-close logic
    - On save: update local state polygons for item, mark `edited: true`, refresh thumbnail card
    - On close without save: discard changes, retain previous polygons
    - _Requirements: 4.4, 4.5_
  - [x] 8.7 Implement `_downloadAll(format)` — GET `/api/batch/{batch_id}/download?format={format}`
    - Disable "Download All" if no done items
    - Trigger browser file download on response
    - On error: display message and allow retry
    - _Requirements: 5.2, 5.3, 5.7, 5.8, 6.5_

- [x] 9. Create `frontend/src/batchPolygonEditor.js`
  - [x] 9.1 Implement `BatchPolygonEditor` class
    - Accept `{ imageUrl, polygons, onSave, onClose }` config
    - Render a modal overlay with the image and SVG polygon overlays
    - Reuse the drag/resize/add/delete polygon logic from `gptBoundaryDetector.js`
    - Call `onSave(polygons)` when user clicks Save; call `onClose()` on cancel/close
    - _Requirements: 4.2, 4.3_

- [x] 10. Wire `BatchProcessor` into the app
  - [x] 10.1 Import and instantiate `BatchProcessor` in `frontend/src/index.js`
    - Add `<section id="batch-section">` placeholder to `frontend/index.html`
    - Call `batchProcessor.init()` in `AerialSegmentationApp` constructor
    - _Requirements: 1.1_

- [ ] 11. Final checkpoint — Ensure all tests pass
  - Ensure all backend tests pass and the batch UI renders correctly end-to-end. Ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for a faster MVP
- Sequential processing (one image at a time) is intentional to avoid GPU memory contention
- Max 50 images per ZIP is enforced on both backend (HTTP 400) and communicated in the UI
- Batch state is in-memory only — restarting the server clears all batch jobs
- The polygon editor reuses existing SVG editing logic from `gptBoundaryDetector.js`
