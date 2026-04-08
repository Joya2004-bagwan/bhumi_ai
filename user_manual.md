# BHUMI AI — User Manual

## Table of Contents

1. [Getting Started](#1-getting-started)
2. [Interface Overview](#2-interface-overview)
3. [Single Image Processing](#3-single-image-processing)
4. [Batch Processing](#4-batch-processing)
5. [GeoJSON Export](#5-geojson-export)
6. [Dashboard & Export Log](#6-dashboard--export-log)
7. [Settings & Profile](#7-settings--profile)
8. [Supported File Formats](#8-supported-file-formats)
9. [Troubleshooting](#9-troubleshooting)

---

## 1. Getting Started

Open your browser and navigate to:

```
http://localhost:4000
```

The application loads directly into the **Single Processing** page. No login is required. The sidebar on the left gives access to all four sections of the tool.

---

## 2. Interface Overview

The interface is divided into two areas:

**Sidebar (left)**
- Navigation between pages: Single Processing, Batch Processing, Dashboard, Settings/Profile
- Your user identity is shown at the bottom of the sidebar

**Main content area (right)**
- Changes based on the active page
- A breadcrumb at the top shows your current location

**Pages:**

| Page | Purpose |
|---|---|
| Single Processing | Upload one image, run detection, edit polygons, export |
| Batch Processing | Upload a ZIP of images, process all at once, bulk download |
| Dashboard | Session export log — files downloaded and building counts |
| Settings/Profile | Theme, default model, personal info |

---

## 3. Single Image Processing

This is the main workflow for processing one aerial or satellite image at a time.

### Step 1 — Upload an Image

On the **Single Processing** page, the left panel shows the **Source Material** card.

- Click **Browse Files** to open a file picker, or drag and drop an image directly onto the upload zone.
- Supported formats: JPG, JPEG, PNG, TIFF, TIF
- Maximum file size: 50 MB

Once uploaded, the image appears in the main viewer on the right. The status line below the upload zone confirms the filename and dimensions, for example:

```
✓ Uploaded: tile_100.png (512x512)
```

### Step 2 — Select a Model

The **Intelligence Model** card below the upload zone shows two options:

**YOLOv8**
- Architecture: YOLOv8m-seg
- Best for: fast inference, dense urban areas with many buildings close together
- Speed: faster

**Mask R-CNN**
- Architecture: Mask R-CNN ResNet50-FPN
- Best for: complex or irregular building shapes, better boundary accuracy
- Speed: slower

Click a model card to select it. The selected card is highlighted.

> Both models are loaded on first use. The first request after startup will take longer while the model loads into memory. Subsequent requests are faster.

### Step 3 — Detect Buildings

Click the **Detect Buildings** button (enabled once both an image and a model are selected).

The button shows a loading state while the backend:
1. Runs segmentation to produce a binary mask
2. Fits a rotated rectangle (minAreaRect) to each detected building instance
3. Returns polygon coordinates for every building

When complete, the main viewer updates to show the original image with green polygon outlines drawn over each detected building. The **Detection Results** panel below shows:

- **Buildings Detected** — total count of polygons returned
- **Avg Confidence** — average model confidence score
- **Proc. Time** — total processing time in seconds

### Step 4 — Review Results

The viewer has two tabs:

- **Original** — the uploaded image with polygon overlays
- **GeoJSON Preview** — appears after GeoJSON is generated (see Section 5)

Click any polygon to inspect it. The overlay uses green outlines with a semi-transparent green fill.

### Step 5 — Edit Polygons (optional)

Click **Edit Polygons** to enter edit mode. In edit mode:

- **Drag a vertex** — click and drag any corner point of a polygon to reposition it
- **Delete a polygon** — select a polygon then click **Delete Polygon**
- **Draw a new polygon** — click **Draw Polygon**, then click on the image to place each vertex; click the first vertex again to close the shape
- **Finish editing** — click **Done Editing** to exit edit mode and save changes

### Step 6 — Export

After detection (and optional editing), three export options are available:

**Download as JSON**
Contains the polygon coordinates and building count for the image. Useful for further processing in other tools.

**Download as PNG / JPEG**
The original image rendered with green polygon overlays drawn on top. Good for reports and visual review.

**Download as GeoJSON**
Requires a world file — see [Section 5](#5-geojson-export) for the full GeoJSON workflow.

---

## 4. Batch Processing

Batch processing lets you run detection across many images at once by uploading a ZIP archive.

### Step 1 — Upload Images ZIP

Navigate to **Batch Processing** from the sidebar.

- Click **Choose File** next to **Images ZIP** and select your `.zip` file, or use the file picker.
- Click **Upload ZIP**.

Limits:
- Maximum 50 images per batch
- Maximum 500 MB ZIP size
- Supported image formats inside the ZIP: JPG, JPEG, PNG, TIFF, TIF

> TIFF images are automatically converted to PNG during upload so they display correctly in the browser.

After upload, a status line confirms how many images were found:

```
✓ Uploaded — 11 image(s) found
```

The filenames are listed as chips below the status line.

### Step 2 — Upload World Files ZIP (optional)

This step is only needed if you want GeoJSON output with real-world coordinates. If you only need JSON, PNG, or JPEG output, skip to Step 3.

After the images ZIP is uploaded, a second upload row appears: **World Files ZIP**.

- Prepare a ZIP containing one world file per image, with matching base names:
  - `tile_100.png` → `tile_100.pgw`
  - `tile_101.tif` → `tile_101.tfw`
- Supported world file extensions: `.pgw`, `.tfw`, `.jgw`, `.wld`
- Click **Choose File**, select your world files ZIP, then click **Upload World Files**.

The status line reports how many files matched:

```
✓ 9 matched · 2 unmatched (tile_104.png, tile_107.png)
```

Unmatched images will still be processed — they just won't have GeoJSON output. The batch never fails because of a missing world file.

### Step 3 — Select a Model

Use the **Select Model** dropdown to choose between:

- **YOLOv8 (Fast, Dense Urban)**
- **Mask R-CNN (Complex Boundaries)**

### Step 4 — Run Detection

Click **Detect Buildings**. The button is enabled only when both an images ZIP and a model are selected.

A progress indicator shows how many images have been processed:

```
Detecting buildings… 4/11 images
```

Each image card in the grid below updates in real time with a status badge:

| Badge | Meaning |
|---|---|
| pending | Waiting to be processed |
| processing | Currently running |
| done | Completed successfully |
| failed | An error occurred |

### Step 5 — Review Thumbnails

Once images finish processing, their cards show:
- A thumbnail of the image with green polygon overlays
- The number of buildings detected (e.g. `50 bldg`)
- An **Edit** button
- A click-to-expand preview (click the thumbnail to open a full-size modal)

**Full-size preview modal**
Click any thumbnail to open a full-size view of the image with all detected polygons drawn at full resolution. Press **Escape** or click outside the modal to close it.

### Step 6 — Edit Individual Images (optional)

Click **Edit** on any completed card to open the polygon editor for that image.

The editor opens full-screen over the grid. It works the same as the single-image editor:
- Drag vertices to adjust polygon shapes
- Delete unwanted polygons
- Draw new polygons

Click **Save** to save your changes and return to the grid. The card will show an **edited** badge. Click **Close** to discard changes.

### Step 7 — Retry Failed Items

If any image shows a **failed** badge, click **Retry** on that card. The item will re-run segmentation independently without restarting the whole batch.

### Step 8 — Download Results

When at least one image is done, the **Output Format** row appears at the bottom.

Select a format:

| Format | Contents |
|---|---|
| JSON | One `{stem}_output.json` per image with polygon coordinates and building count |
| PNG | One `{stem}_output.png` per image — original image with green polygon overlays |
| JPEG | Same as PNG but in JPEG format |
| GeoJSON | One `{stem}.geojson` per image that had a matching world file |

> The **GeoJSON** option is greyed out until a world files ZIP has been uploaded. It only includes images that had a matched world file.

Click **Download All**. A ZIP file is downloaded containing one output file per successfully processed image.

---

## 5. GeoJSON Export

GeoJSON export produces georeferenced building footprints — polygons with real-world geographic coordinates instead of pixel coordinates. This output can be loaded directly into GIS tools like QGIS or ArcGIS.

### What is a World File?

A world file is a plain text file with six lines that define how pixel coordinates map to geographic coordinates. It is typically produced by the same software that captured or processed the aerial image.

Common extensions and their associated image types:

| World File | Image Type |
|---|---|
| `.pgw` | PNG |
| `.tfw` | TIFF |
| `.jgw` | JPEG |
| `.wld` | Generic |

The base name must match the image exactly:
- `tile_100.png` → `tile_100.pgw`
- `survey_area.tif` → `survey_area.tfw`

### Single Image GeoJSON Workflow

1. Upload your image (Step 1–2 of Single Processing)
2. In the **GeoJSON Export** card on the left panel:
   - Click the world file input and select your `.pgw` / `.tfw` / `.jgw` / `.wld` file
   - The status shows `filename.pgw ✓ (ready)`
3. Optionally adjust:
   - **Min Area (px)** — buildings smaller than this pixel area are excluded (default: 100)
   - **Simplify Tolerance** — polygon simplification level (default: 1; higher = fewer vertices)
4. Click **Generate GeoJSON**
   - The world file is uploaded to the server
   - Segmentation runs on the image
   - Building polygons are transformed to world coordinates
5. The result shows `N features exported`
6. The viewer switches to the **GeoJSON Preview** tab, showing the image with polygon outlines
7. Click **Download GeoJSON** to save the `.geojson` file

The downloaded file is named after the original image:
```
tile_100.geojson
```

### Batch GeoJSON Workflow

Follow the full Batch Processing workflow (Section 4), including Step 2 (upload world files ZIP). After processing completes, select **GeoJSON** from the Output Format dropdown and click **Download All**.

The downloaded ZIP contains one `.geojson` file per image that had a matching world file:
```
tile_100.geojson
tile_101.geojson
tile_102.geojson
...
```

Images without a matching world file are excluded from the GeoJSON ZIP but are still available in JSON, PNG, or JPEG format.

---

## 6. Dashboard & Export Log

The **Dashboard** page tracks activity for the current browser session.

**Images Processed** — total count of images that have been through detection.

**Export Log table** — every time you download output (single or batch), a row is added:

| Column | Description |
|---|---|
| Output File | The filename that was downloaded |
| Buildings Detected | Number of building polygons in that file |
| Export Format | JSON, PNG, JPEG, or GeoJSON |

The log resets when you refresh the page or close the browser tab, as it is stored in memory for the session only.

---

## 7. Settings & Profile

Navigate to **Settings/Profile** from the sidebar.

### Personal Info tab

Update your display name and email address. These are cosmetic only and do not affect processing.

### Preferences tab

- **Default Intelligence Model** — sets which model card is pre-selected when you open Single Processing
- **Default Export Format** — sets the default format in the download dropdown
- **Hardware Acceleration** — toggle GPU rendering hints (informational; actual GPU use depends on server hardware)

Click **Save Preferences** to apply.

### Appearance tab

Switch between **Dark** and **Light** themes. Click **Apply Theme** to save the selection. The theme is applied immediately across the entire interface.

---

## 8. Supported File Formats

### Input Images

| Format | Extension | Notes |
|---|---|---|
| JPEG | `.jpg`, `.jpeg` | Standard compressed photo format |
| PNG | `.png` | Lossless, recommended for aerial tiles |
| TIFF | `.tif`, `.tiff` | Common GIS raster format; auto-converted to PNG on upload |

Maximum single image size: **50 MB**
Maximum batch ZIP size: **500 MB**
Maximum images per batch: **50**

### World Files

| Extension | Associated Image |
|---|---|
| `.pgw` | PNG |
| `.tfw` | TIFF |
| `.jgw` | JPEG |
| `.wld` | Any |

World file format — 6 lines, one value per line:
```
0.5        ← pixel width in map units
0.0        ← rotation (usually 0)
0.0        ← rotation (usually 0)
-0.5       ← pixel height in map units (negative = north-up)
500000.0   ← X coordinate of upper-left pixel center
4000000.0  ← Y coordinate of upper-left pixel center
```

### Output Formats

| Format | Extension | Description |
|---|---|---|
| JSON | `.json` | Polygon coordinates + building count |
| PNG | `.png` | Image with polygon overlays |
| JPEG | `.jpg` | Image with polygon overlays |
| GeoJSON | `.geojson` | Georeferenced building footprints (requires world file) |

---

## 9. Troubleshooting

**Image uploads but no thumbnail appears in batch grid**
The image may be a TIFF that failed to convert. Check that the file is a valid, uncorrupted TIFF. Re-upload the ZIP.

**"Detect Buildings" button stays disabled**
Both an image (or images ZIP) and a model must be selected before the button enables.

**GeoJSON option is greyed out in batch download**
A world files ZIP must be uploaded before running the batch. The option enables automatically after a successful world files upload.

**"No matching world file" shown for some batch items**
The world file base name must exactly match the image base name (case-insensitive). For example, `Tile_100.PNG` matches `tile_100.pgw`. Check for typos or extra characters in filenames.

**First detection request is slow**
Models are loaded into memory on first use. YOLOv8 typically takes 5–15 seconds to load; Mask R-CNN takes 20–40 seconds. Subsequent requests on the same model are much faster.

**"Failed to load Mask R-CNN model: Permission denied"**
The server's PyTorch cache directory is set to an inaccessible path. Set `TORCH_HOME` in `backend/.env` to a local writable directory, for example:
```
TORCH_HOME=/home/youruser/.cache/torch
```
Then restart the backend.

**Batch job shows all items as failed**
Check that the backend server is running at `http://localhost:8000`. Open the browser developer console (F12) for detailed error messages.

**Lost connection to server during batch**
If the browser shows "Lost connection to server", verify the backend process is still running. Restart it with `make dev` and refresh the page. Batch state is held in memory — a server restart clears all in-progress jobs.

**World file upload fails with "Invalid world file"**
Ensure the file has exactly 6 lines, each containing a single numeric value. Empty lines or extra whitespace at the end of the file can cause parse failures.
