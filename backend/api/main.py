"""
FastAPI application for aerial image segmentation.

Slim entry point: app instance, CORS, static mounts, exception handlers,
and router registration. All endpoint logic lives in api/routers/.
"""

import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

# Load .env
try:
    from dotenv import load_dotenv
    _env_path = Path(__file__).resolve().parent.parent / ".env"
    load_dotenv(dotenv_path=_env_path, override=True)
except ImportError:
    pass

try:
    from api.config import UPLOAD_DIR, MASK_DIR
    from api.schemas import ErrorResponse
    from api.routers import segmentation, boundaries, batch, geojson, stats
except ImportError:
    from .config import UPLOAD_DIR, MASK_DIR
    from .schemas import ErrorResponse
    from .routers import segmentation, boundaries, batch, geojson, stats

# Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# App
app = FastAPI(
    title="Aerial Image Segmentation API",
    description="API for segmenting buildings in aerial/satellite imagery using YOLOv8 and Mask R-CNN models",
    version="1.0.0",
)

# CORS — allow all origins in development; traffic from the network goes
# through the Vite proxy which forwards to localhost:8000.
_cors_env = os.getenv("CORS_ORIGINS", "")
_cors_origins = [o.strip() for o in _cors_env.split(",") if o.strip()] if _cors_env else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static file mounts
app.mount("/images", StaticFiles(directory=str(UPLOAD_DIR)), name="images")
app.mount("/masks", StaticFiles(directory=str(MASK_DIR)), name="masks")

# ── Exception handlers ───────────────────────────────────────────────────────

@app.exception_handler(400)
async def bad_request_handler(request: Request, exc: HTTPException):
    logger.warning(f"Bad request: {exc.detail} - Path: {request.url.path}")
    return JSONResponse(status_code=400, content=ErrorResponse(detail=exc.detail, timestamp=datetime.now(timezone.utc).isoformat(), path=str(request.url.path)).model_dump())

@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    logger.warning(f"Resource not found: {exc.detail} - Path: {request.url.path}")
    return JSONResponse(status_code=404, content=ErrorResponse(detail=exc.detail, timestamp=datetime.now(timezone.utc).isoformat(), path=str(request.url.path)).model_dump())

@app.exception_handler(413)
async def payload_too_large_handler(request: Request, exc: HTTPException):
    logger.warning(f"Payload too large: {exc.detail} - Path: {request.url.path}")
    return JSONResponse(status_code=413, content=ErrorResponse(detail=exc.detail, timestamp=datetime.now(timezone.utc).isoformat(), path=str(request.url.path)).model_dump())

@app.exception_handler(500)
async def internal_server_error_handler(request: Request, exc: Exception):
    logger.error(f"Internal server error: {str(exc)} - Path: {request.url.path}", exc_info=True)
    return JSONResponse(status_code=500, content=ErrorResponse(detail="Internal server error. Please try again later.", timestamp=datetime.now(timezone.utc).isoformat(), path=str(request.url.path)).model_dump())


# ── Root endpoints ───────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {"message": "Aerial Image Segmentation API", "version": "1.0.0", "status": "running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}


# ── Routers ──────────────────────────────────────────────────────────────────

app.include_router(segmentation.router)
app.include_router(boundaries.router)
app.include_router(batch.router)
app.include_router(geojson.router)
app.include_router(stats.router)
