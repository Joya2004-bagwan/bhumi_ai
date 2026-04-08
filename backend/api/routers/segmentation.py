"""Segmentation router: upload, segment, list models."""

import logging
import time
import uuid
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException

try:
    from api.config import (
        UPLOAD_DIR, MASK_DIR, MAX_FILE_SIZE, SEGMENTATION_TIMEOUT,
        image_processor, model_manager,
    )
    from api.schemas import (
        UploadResponse, SegmentRequest, SegmentResponse,
        ModelInfo, ModelsResponse,
    )
    from utils.image_processor import ImageProcessor
except ImportError:
    from backend.api.config import (
        UPLOAD_DIR, MASK_DIR, MAX_FILE_SIZE, SEGMENTATION_TIMEOUT,
        image_processor, model_manager,
    )
    from backend.api.schemas import (
        UploadResponse, SegmentRequest, SegmentResponse,
        ModelInfo, ModelsResponse,
    )
    from backend.utils.image_processor import ImageProcessor

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/upload", response_model=UploadResponse)
async def upload_image(file: UploadFile = File(...)):
    """Upload an aerial image for segmentation."""
    logger.info(f"Upload request received: filename={file.filename}")

    contents = await file.read()
    file_size = len(contents)

    if file_size > MAX_FILE_SIZE:
        logger.warning(f"File too large: {file_size} bytes (max: {MAX_FILE_SIZE})")
        raise HTTPException(status_code=413, detail=f"Image file is too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB.")

    image_id = str(uuid.uuid4())
    original_filename = file.filename or "image.jpg"
    file_extension = Path(original_filename).suffix.lower()

    if file_extension not in ImageProcessor.SUPPORTED_FORMATS:
        logger.warning(f"Unsupported format: {file_extension}")
        raise HTTPException(status_code=400, detail="Unsupported file format. Please upload JPG, PNG, or TIFF images.")

    temp_file_path = UPLOAD_DIR / f"{image_id}{file_extension}"

    try:
        with open(temp_file_path, "wb") as f:
            f.write(contents)

        logger.info(f"File saved: image_id={image_id}, size={file_size} bytes")

        validation_result = image_processor.validate_image(str(temp_file_path))
        if not validation_result.valid:
            temp_file_path.unlink()
            logger.warning(f"Invalid image: image_id={image_id}, error={validation_result.error}")
            raise HTTPException(status_code=400, detail=validation_result.error)

        image_array = image_processor.load_image(str(temp_file_path))
        height, width = image_array.shape[:2]
        image_url = f"/images/{image_id}{file_extension}"

        logger.info(f"Upload successful: image_id={image_id}, dimensions={width}x{height}")
        return UploadResponse(image_id=image_id, image_url=image_url, width=width, height=height)

    except HTTPException:
        raise
    except Exception as e:
        if temp_file_path.exists():
            temp_file_path.unlink()
        logger.error(f"Upload failed: image_id={image_id}, error={str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to process uploaded image: {str(e)}")


@router.post("/segment", response_model=SegmentResponse)
async def segment_image(request: SegmentRequest):
    """Run segmentation on an uploaded image."""
    logger.info(f"Segmentation request: image_id={request.image_id}, model={request.model}")

    available_models = model_manager.get_available_models()
    if request.model not in available_models:
        logger.warning(f"Invalid model: {request.model}")
        raise HTTPException(status_code=400, detail=f"Invalid model name. Supported models: {', '.join(available_models)}")

    image_path = None
    for ext in ImageProcessor.SUPPORTED_FORMATS:
        potential_path = UPLOAD_DIR / f"{request.image_id}{ext}"
        if potential_path.exists():
            image_path = potential_path
            break

    if image_path is None:
        logger.warning(f"Image not found: image_id={request.image_id}")
        raise HTTPException(status_code=404, detail="Image not found. Please upload an image first.")

    try:
        logger.info(f"Loading image: {image_path}")
        image_array = image_processor.load_image(str(image_path))

        logger.info(f"Starting segmentation: model={request.model}, image_shape={image_array.shape}")
        start_time = time.time()
        mask = model_manager.segment(image_array, request.model)
        processing_time = time.time() - start_time
        logger.info(f"Segmentation completed: time={processing_time:.2f}s")

        if processing_time > SEGMENTATION_TIMEOUT:
            logger.warning(f"Segmentation exceeded timeout: time={processing_time:.2f}s, timeout={SEGMENTATION_TIMEOUT}s")

        mask_filename = f"{request.image_id}-{request.model}-mask.png"
        mask_path = MASK_DIR / mask_filename
        image_processor.save_mask(mask, str(mask_path))
        logger.info(f"Mask saved: {mask_path}")

        mask_base64 = image_processor.mask_to_base64(mask)
        mask_url = f"/masks/{mask_filename}"

        logger.info(f"Segmentation successful: image_id={request.image_id}, model={request.model}, time={processing_time:.2f}s")
        return SegmentResponse(mask_url=mask_url, mask_base64=mask_base64, processing_time=processing_time, model_used=request.model)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Segmentation failed: image_id={request.image_id}, model={request.model}, error={str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Segmentation failed. The image may be incompatible with this model: {str(e)}")


@router.get("/models", response_model=ModelsResponse)
async def get_models():
    """Get list of available segmentation models."""
    MODEL_DISPLAY = {
        "yolov8m-custom": ("YOLOv8m Custom (Your Dataset)", "YOLOv8m trained on your building dataset"),
        "maskrcnn-custom": ("Mask R-CNN Custom (Your Dataset)", "Mask R-CNN trained on your building dataset"),
    }
    models = []
    for name in model_manager.get_available_models():
        display_name, description = MODEL_DISPLAY.get(name, (name, ""))
        models.append(ModelInfo(name=name, display_name=display_name, description=description))
    return ModelsResponse(models=models)
