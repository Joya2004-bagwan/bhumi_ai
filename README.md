# BHUMI AI — Aerial Image Segmentation

Detect buildings in aerial and satellite imagery using deep learning. Upload drone photos, run AI segmentation, review detected building polygons, and export results. Supports single-image and batch (ZIP) workflows.

## Prerequisites

- Python 3.9+
- Node.js 18+ / npm
- 8 GB RAM minimum (16 GB recommended for GPU inference)

## Setup

```bash
git clone <repo-url> && cd bhumi-ai
cp backend/.env.example backend/.env
make install
```

Place model weights in `backend/models/weights/`:

| Model | File | Size |
|-------|------|------|
| YOLOv8m | `best_fixed.pt` | ~109 MB |
| Mask R-CNN | `maskrcnn_building_best.pth` | ~176 MB |

## Running

```bash
make dev      # starts backend (port 8000) + frontend (port 4000)
make stop     # kills both servers
```

Open **http://localhost:4000** in your browser.

## Environment

Edit `backend/.env` — all values have sensible defaults except:

```
OPENAI_API_KEY=           # optional, for future GPT-based boundary detection
YOLOV8_MODEL_PATH=        # leave empty to use backend/models/weights/best_fixed.pt
MASKRCNN_MODEL_PATH=      # leave empty to use backend/models/weights/maskrcnn_building_best.pth
MAX_UPLOAD_SIZE_MB=50
MAX_BATCH_SIZE_MB=500
MAX_BATCH_IMAGES=50
```

## Models

| Name | Architecture | Best For |
|------|-------------|----------|
| `yolov8m-custom` | YOLOv8m-seg (Ultralytics) | Fast inference, dense urban areas |
| `maskrcnn-custom` | Mask R-CNN ResNet50-FPN | Complex irregular building shapes |

Both models are lazy-loaded on first request. No GPU required — CPU works, just slower.

## Project Structure

```
├── Makefile                        # install / dev / stop
├── backend/
│   ├── api/
│   │   ├── main.py                 # FastAPI app, CORS, static mounts, routers
│   │   ├── config.py               # BASE_DIR, paths, shared services, constants
│   │   ├── schemas.py              # All Pydantic request/response models
│   │   └── routers/
│   │       ├── segmentation.py     # POST /upload, /segment, GET /models
│   │       ├── boundaries.py       # POST /boundaries, /api/gpt-boundaries
│   │       └── batch.py            # POST /api/batch/*, GET /api/batch/*
│   ├── models/
│   │   ├── segmentation_model.py   # Abstract base class
│   │   ├── segmentation_model_manager.py
│   │   ├── yolov8_adapter.py       # YOLOv8 adapter
│   │   ├── maskrcnn_adapter.py     # Mask R-CNN adapter
│   │   └── weights/                # .gitignored model files
│   ├── utils/
│   │   ├── image_processor.py      # Validate, load, save images/masks
│   │   ├── boundary_detector.py    # OpenCV contour detection
│   │   └── gpt_boundary.py         # minAreaRect boundary extraction
│   ├── tests/                      # pytest suite
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── index.html                  # SPA shell
│   ├── vite.config.js              # Dev server (port 4000), API proxy
│   ├── src/
│   │   ├── index.js                # App controller, page routing
│   │   ├── imageUploader.js        # Upload component
│   │   ├── modelSelector.js        # Model selection
│   │   ├── segmentationRunner.js   # Segmentation execution
│   │   ├── visualizationPanel.js   # Original / mask / overlay display
│   │   ├── boundaryDetector.js     # OpenCV boundary UI
│   │   ├── gptBoundaryDetector.js  # Enhanced boundary UI
│   │   ├── batchProcessor.js       # Batch ZIP workflow
│   │   ├── batchPolygonEditor.js   # Per-image polygon editor
│   │   ├── dashboard.js            # Stats and export log
│   │   ├── theme.css               # Design tokens, dark/light themes
│   │   └── app.css                 # Layout, components, batch editor
│   └── package.json
└── README.md
```

## API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/health` | Health check |
| `GET` | `/models` | List available models |
| `POST` | `/upload` | Upload single image |
| `POST` | `/segment` | Run segmentation |
| `POST` | `/boundaries` | OpenCV boundary detection |
| `POST` | `/api/gpt-boundaries` | Per-instance minAreaRect boundaries |
| `POST` | `/api/batch/upload-zip` | Upload ZIP for batch processing |
| `POST` | `/api/batch/{id}/run` | Start batch job |
| `GET` | `/api/batch/{id}/status` | Poll batch progress |
| `GET` | `/api/batch/{id}/download` | Download results as ZIP |

## Testing

```bash
cd backend
source venv/bin/activate
pytest
```

## License

MIT
