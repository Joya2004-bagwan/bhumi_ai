"""GeoJSON export router: upload world files, export segmentation as GeoJSON."""

import logging
import time
import uuid
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException

from ..config import UPLOAD_DIR, model_manager, image_processor
from ..schemas import (
    GeoJSONSegmentRequest, GeoJSONSegmentResponse,
    WorldFileUploadResponse
)
from ...utils.worldfile import WorldFile
from ...utils.geojson_exporter import GeoJSONExporter
from ...utils.event_logger import log_event

logger = logging.getLogger(__name__)
router = APIRouter()

# Directory for world files
WORLD_FILE_DIR = UPLOAD_DIR / "worldfiles"
WORLD_FILE_DIR.mkdir(exist_ok=True)

# In-memory storage for world file metadata
world_files = {}


@router.post("/upload/worldfile", response_model=WorldFileUploadResponse)
async def upload_worldfile(
    image_id: str,
    file: UploadFile = File(...)
):
    """
    Upload a world file (.pgw, .tfw, .jgw) for georeferencing an image.
    
    Args:
        image_id: The ID of the associated image
        file: The world file
    """
    logger.info(f"World file upload: image_id={image_id}, filename={file.filename}")
    
    # Validate file extension
    filename = file.filename or "worldfile.pgw"
    ext = Path(filename).suffix.lower()
    if ext not in {'.pgw', '.tfw', '.jgw', '.wld'}:
        raise HTTPException(
            status_code=400,
            detail="Invalid world file format. Expected .pgw, .tfw, .jgw, or .wld"
        )
    
    # Check if image exists
    image_exists = False
    for img_ext in ['.png', '.jpg', '.jpeg', '.tiff', '.tif']:
        if (UPLOAD_DIR / f"{image_id}{img_ext}").exists():
            image_exists = True
            break
    
    if not image_exists:
        raise HTTPException(
            status_code=404,
            detail=f"No image found with ID: {image_id}"
        )
    
    # Save world file
    world_file_id = str(uuid.uuid4())
    world_file_path = WORLD_FILE_DIR / f"{world_file_id}{ext}"
    
    try:
        contents = await file.read()
        with open(world_file_path, "wb") as f:
            f.write(contents)
        
        # Parse and validate world file
        wf = WorldFile(str(world_file_path))
        world_files[world_file_id] = {
            "path": str(world_file_path),
            "image_id": image_id,
            "params": wf.to_dict()
        }
        
        logger.info(f"World file saved: world_file_id={world_file_id}")
        
        return WorldFileUploadResponse(
            image_id=image_id,
            world_file_id=world_file_id,
            message=f"World file uploaded successfully. CRS origin: ({wf.origin_x}, {wf.origin_y})"
        )
        
    except Exception as e:
        if world_file_path.exists():
            world_file_path.unlink()
        logger.error(f"Failed to process world file: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid world file: {str(e)}"
        )


@router.post("/segment/geojson", response_model=GeoJSONSegmentResponse)
async def segment_to_geojson(request: GeoJSONSegmentRequest):
    """
    Run segmentation and return results as GeoJSON with world coordinates.
    
    Requires a previously uploaded world file for coordinate transformation.
    """
    logger.info(f"GeoJSON segmentation: image_id={request.image_id}, model={request.model}")
    
    # Validate model
    available_models = model_manager.get_available_models()
    if request.model not in available_models:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid model. Available: {', '.join(available_models)}"
        )
    
    # Check world file
    if request.world_file_id not in world_files:
        raise HTTPException(
            status_code=404,
            detail="World file not found. Please upload a world file first."
        )
    
    # Find image
    image_path = None
    for ext in ['.png', '.jpg', '.jpeg', '.tiff', '.tif']:
        potential = UPLOAD_DIR / f"{request.image_id}{ext}"
        if potential.exists():
            image_path = potential
            break
    
    if image_path is None:
        raise HTTPException(
            status_code=404,
            detail="Image not found. Please upload an image first."
        )
    
    try:
        start_time = time.time()
        
        # Load image
        image_array = image_processor.load_image(str(image_path))
        
        # Run segmentation
        mask = model_manager.segment(image_array, request.model)
        
        # Load world file
        wf_info = world_files[request.world_file_id]
        world_file = WorldFile(wf_info["path"])
        
        # Export to GeoJSON
        exporter = GeoJSONExporter(world_file)
        geojson = exporter.mask_to_geojson(
            mask,
            min_area=request.min_area,
            simplify_tolerance=request.simplify_tolerance
        )
        
        processing_time = time.time() - start_time
        
        logger.info(f"GeoJSON export complete: {len(geojson['features'])} features in {processing_time:.2f}s")
        
        log_event("export", image_id=request.image_id, filename=str(image_path.name),
                  export_format="geojson", building_count=len(geojson["features"]),
                  model=request.model, source="single")
        
        return GeoJSONSegmentResponse(
            geojson=geojson,
            feature_count=len(geojson["features"]),
            processing_time=processing_time,
            model_used=request.model,
            crs_info=wf_info["params"]
        )
        
    except Exception as e:
        logger.error(f"GeoJSON segmentation failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Segmentation failed: {str(e)}"
        )