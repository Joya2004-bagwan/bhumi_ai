"""Boundary detection router: OpenCV contours and per-instance minAreaRect."""

import os
import logging
import time
import base64

import cv2
import numpy as np
from fastapi import APIRouter, HTTPException

try:
    from api.config import (
        UPLOAD_DIR, MASK_DIR,
        image_processor, model_manager, boundary_detector,
    )
    from api.schemas import (
        BoundaryRequest, BoundaryResponse,
        GPTBoundaryRequest, GPTBoundaryResponse,
    )
    from utils.image_processor import ImageProcessor
    from utils.gpt_boundary import GPTBoundaryExtractor
except ImportError:
    from backend.api.config import (
        UPLOAD_DIR, MASK_DIR,
        image_processor, model_manager, boundary_detector,
    )
    from backend.api.schemas import (
        BoundaryRequest, BoundaryResponse,
        GPTBoundaryRequest, GPTBoundaryResponse,
    )
    from backend.utils.image_processor import ImageProcessor
    from backend.utils.gpt_boundary import GPTBoundaryExtractor

logger = logging.getLogger(__name__)
router = APIRouter()


def _opencv_overlay(original_bgr: np.ndarray, mask_gray: np.ndarray) -> np.ndarray:
    """Draw OpenCV contours on original image (green, 2px)."""
    result = original_bgr.copy()
    contours, _ = cv2.findContours(mask_gray, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(result, contours, -1, (0, 255, 0), 2)
    return result


@router.post("/boundaries", response_model=BoundaryResponse)
async def detect_boundaries(request: BoundaryRequest):
    """Detect building boundaries from segmentation mask."""
    logger.info(f"Boundary detection request: image_id={request.image_id}, model={request.model}")

    mask_filename = f"{request.image_id}-{request.model}-mask.png"
    mask_path = MASK_DIR / mask_filename

    if not mask_path.exists():
        logger.warning(f"Mask not found: {mask_path}")
        raise HTTPException(status_code=404, detail="Mask not found. Please run segmentation first.")

    try:
        logger.info(f"Loading mask: {mask_path}")
        mask = image_processor.load_image(str(mask_path))
        if len(mask.shape) == 3:
            mask = cv2.cvtColor(mask, cv2.COLOR_RGB2GRAY)

        logger.info("Detecting building boundaries...")
        start_time = time.time()
        buildings = boundary_detector.detect_boundaries(mask)
        processing_time = time.time() - start_time
        logger.info(f"Boundary detection completed: {len(buildings)} buildings found, time={processing_time:.2f}s")

        return BoundaryResponse(buildings=buildings, total_buildings=len(buildings), processing_time=processing_time)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Boundary detection failed: image_id={request.image_id}, model={request.model}, error={str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Boundary detection failed: {str(e)}")


@router.post("/api/gpt-boundaries", response_model=GPTBoundaryResponse)
async def gpt_boundaries(request: GPTBoundaryRequest):
    """Detect building boundaries using per-instance minAreaRect."""
    api_key = os.getenv("OPENAI_API_KEY", "")

    original_path = None
    for ext in ImageProcessor.SUPPORTED_FORMATS:
        p = UPLOAD_DIR / f"{request.image_id}{ext}"
        if p.exists():
            original_path = p
            break
    if original_path is None:
        raise HTTPException(status_code=404, detail="Original image not found.")

    mask_filename = f"{request.image_id}-{request.model}-mask.png"
    mask_path = MASK_DIR / mask_filename
    if not mask_path.exists():
        raise HTTPException(status_code=404, detail="Mask not found. Please run segmentation first.")

    try:
        start_time = time.time()

        original_rgb = image_processor.load_image(str(original_path))
        original_bgr = cv2.cvtColor(original_rgb, cv2.COLOR_RGB2BGR)

        mask_rgb = image_processor.load_image(str(mask_path))
        mask_gray = cv2.cvtColor(mask_rgb, cv2.COLOR_RGB2GRAY) if len(mask_rgb.shape) == 3 else mask_rgb

        model_obj = model_manager.get_model(request.model)
        if hasattr(model_obj, 'instance_segment'):
            instance_masks = model_obj.instance_segment(original_rgb)
        else:
            instance_masks = [mask_gray]

        logger.info(f"GPT boundaries: {len(instance_masks)} instance masks for model={request.model}")

        extractor = GPTBoundaryExtractor(api_key=api_key)
        result = await extractor.process_async(original_bgr, instance_masks)

        opencv_img = _opencv_overlay(original_bgr, mask_gray)

        _, gpt_buf = cv2.imencode(".png", result["gpt_overlay_bgr"])
        gpt_b64 = base64.b64encode(gpt_buf.tobytes()).decode("utf-8")

        _, cv_buf = cv2.imencode(".png", opencv_img)
        cv_b64 = base64.b64encode(cv_buf.tobytes()).decode("utf-8")

        processing_time = time.time() - start_time
        logger.info(f"GPT boundaries done: {len(result['polygons'])} buildings, {result['fallback_count']} fallbacks, {processing_time:.1f}s")

        return GPTBoundaryResponse(
            gpt_overlay_b64=gpt_b64,
            opencv_overlay_b64=cv_b64,
            building_count=len(result["polygons"]),
            polygons=result["polygons"],
            processing_time_s=round(processing_time, 2),
            fallback_count=result["fallback_count"],
            gpt_count=result.get("gpt_count", 0),
            fallback_reasons=result.get("fallback_reasons", {}),
            image_url=f"/images/{request.image_id}{original_path.suffix}",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"GPT boundary detection failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"GPT boundary detection failed: {str(e)}")
