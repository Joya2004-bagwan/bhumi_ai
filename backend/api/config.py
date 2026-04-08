"""
Shared configuration for the aerial image segmentation API.

Defines base directories, upload paths, and shared service instances.
"""

import logging
import os
from pathlib import Path

# Ensure .env is loaded before any model paths are resolved
try:
    from dotenv import load_dotenv as _load_dotenv
    _load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env", override=True)
except ImportError:
    pass

# Override TORCH_HOME so torch.hub doesn't use XDG_CACHE_HOME (may point to external drive)
import os as _os
_torch_home = _os.getenv("TORCH_HOME")
if _torch_home:
    _os.environ["TORCH_HOME"] = _torch_home

from ..utils.image_processor import ImageProcessor
from ..models.segmentation_model_manager import SegmentationModelManager
from ..utils.boundary_detector import BoundaryDetector

logger = logging.getLogger(__name__)

# Resolve base directory relative to this file (backend/)
BASE_DIR = Path(__file__).resolve().parent.parent

# Storage directories
UPLOAD_DIR = BASE_DIR / "uploads" / "images"
MASK_DIR = BASE_DIR / "uploads" / "masks"
BATCH_DIR = BASE_DIR / "uploads" / "batch"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
MASK_DIR.mkdir(parents=True, exist_ok=True)
BATCH_DIR.mkdir(parents=True, exist_ok=True)

logger.info(f"BASE_DIR: {BASE_DIR}")
logger.info(f"UPLOAD_DIR: {UPLOAD_DIR}")
logger.info(f"MASK_DIR: {MASK_DIR}")
logger.info(f"BATCH_DIR: {BATCH_DIR}")

# Shared service instances
image_processor = ImageProcessor()
model_manager = SegmentationModelManager()
boundary_detector = BoundaryDetector(
    min_area=50,
    epsilon_factor=0.01,
    morph_kernel_size=3,
    morph_iterations=2,
    shapely_tolerance=None,
)

# Constants (wired to .env with sensible defaults)
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "50"))
MAX_BATCH_MB = int(os.getenv("MAX_BATCH_SIZE_MB", "500"))
MAX_BATCH_IMAGES = int(os.getenv("MAX_BATCH_IMAGES", "50"))

MAX_FILE_SIZE = MAX_UPLOAD_MB * 1024 * 1024
MAX_BATCH_ZIP_SIZE = MAX_BATCH_MB * 1024 * 1024
SEGMENTATION_TIMEOUT = 300                 # seconds
SUPPORTED_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".tiff", ".tif"}
