"""
YOLOv8 segmentation adapter for aerial image segmentation.

This module implements the SegmentationModel interface for YOLOv8, providing
real-time instance segmentation for building detection in aerial images.
"""

from typing import Any
import numpy as np
import torch

# Monkey-patch torch.load to use weights_only=False for trusted model files
# This is necessary for PyTorch 2.6+ compatibility with YOLOv8 models
_original_torch_load = torch.load

def _patched_torch_load(*args, **kwargs):
    """Patched torch.load that sets weights_only=False for model loading."""
    if 'weights_only' not in kwargs:
        kwargs['weights_only'] = False
    return _original_torch_load(*args, **kwargs)

torch.load = _patched_torch_load

from ultralytics import YOLO

from .segmentation_model import SegmentationModel


class YOLOv8Adapter(SegmentationModel):
    """
    Adapter for YOLOv8 segmentation model.
    
    This adapter uses YOLOv8's instance segmentation capabilities to detect
    and segment buildings in aerial images. YOLOv8 is optimized for speed
    and accuracy in real-time applications.
    
    Attributes:
        model_path: Path to YOLOv8 model weights file
        model: YOLOv8 model instance
    """
    
    def __init__(self, model_path: str):
        """
        Initialize YOLOv8Adapter.
        
        Args:
            model_path: Path to YOLOv8 weights file (e.g., 'yolov8n-seg.pt')
        """
        self.model_path = model_path
        self.model = None
    
    def load(self) -> None:
        """
        Load YOLOv8 segmentation model.
        
        Loads model from local file. The module-level torch.load patch
        handles PyTorch 2.6+ compatibility.
        
        Raises:
            Exception: If model loading fails
        """
        try:
            # Local model file
            print(f"Loading YOLOv8 model from local file: {self.model_path}")
            self.model = YOLO(self.model_path)
            
        except Exception as e:
            raise Exception(f"Failed to load YOLOv8 model: {str(e)}")
    
    def preprocess(self, image: np.ndarray) -> np.ndarray:
        """
        Apply YOLOv8-specific preprocessing.
        
        YOLOv8 handles most preprocessing internally (resize, normalize),
        but we ensure the image is in RGB format with uint8 dtype.
        
        Args:
            image: Input image as numpy array with shape (H, W, C)
        
        Returns:
            Preprocessed image as numpy array in RGB format
        """
        # Ensure image is RGB
        if image.shape[2] != 3:
            raise ValueError(f"Expected 3-channel RGB image, got {image.shape[2]} channels")
        
        # Ensure uint8 dtype
        if image.dtype != np.uint8:
            image = image.astype(np.uint8)
        
        return image
    
    def predict(self, preprocessed_input: np.ndarray) -> Any:
        """
        Run YOLOv8 segmentation inference.
        
        Args:
            preprocessed_input: Preprocessed RGB image
        
        Returns:
            YOLOv8 Results object containing detection and segmentation data
        
        Raises:
            Exception: If prediction fails
        """
        if self.model is None:
            raise Exception("Model not loaded. Call load() first.")
        
        try:
            # Run inference
            # verbose=False to suppress output
            # Use task='segment' to ensure segmentation mode
            results = self.model.predict(
                preprocessed_input,
                verbose=False,
                task='segment'
            )
            return results
            
        except AttributeError as e:
            if "'Segment' object has no attribute 'detect'" in str(e):
                # Model architecture issue - try reloading with explicit task
                try:
                    print("Attempting to reload model with explicit segmentation task...")
                    self.model = YOLO(self.model_path, task='segment')
                    results = self.model.predict(
                        preprocessed_input,
                        verbose=False
                    )
                    return results
                except Exception as e2:
                    raise Exception(
                        f"YOLOv8 model architecture incompatibility. "
                        f"Your model may have been trained with a different ultralytics version. "
                        f"Error: {str(e2)}"
                    )
            else:
                raise Exception(f"YOLOv8 prediction failed: {str(e)}")
        except Exception as e:
            raise Exception(f"YOLOv8 prediction failed: {str(e)}")
    
    def postprocess(self, raw_output: Any) -> np.ndarray:
        """
        Convert YOLOv8 output to binary segmentation mask.
        
        This method extracts building class masks from YOLOv8 results and
        combines them into a single binary mask. For building detection,
        we typically look for the 'building' class in COCO dataset (class 0)
        or all detected objects if using a custom model.
        
        Args:
            raw_output: YOLOv8 Results object
        
        Returns:
            Binary segmentation mask with shape (H, W), dtype uint8,
            and values in {0, 255}
        """
        import logging
        logger = logging.getLogger(__name__)
        
        # Get the first result (single image inference)
        result = raw_output[0]
        
        # Get original image dimensions
        orig_shape = result.orig_shape  # (height, width)
        height, width = orig_shape
        
        # Initialize combined mask
        combined_mask = np.zeros((height, width), dtype=np.uint8)
        
        # Check if masks are available
        if result.masks is None:
            # No detections, return empty mask
            logger.warning("YOLOv8: No masks detected in image")
            logger.warning("YOLOv8: This may be because the pretrained model doesn't recognize buildings from aerial view")
            logger.warning("YOLOv8: Consider using a model trained on aerial imagery")
            return combined_mask
        
        # Log detection info
        num_detections = len(result.masks.data)
        logger.info(f"YOLOv8: Found {num_detections} detections")
        if hasattr(result, 'boxes') and result.boxes is not None:
            classes = result.boxes.cls.cpu().numpy()
            logger.info(f"YOLOv8: Detected classes: {classes}")
        
        # Extract masks
        # result.masks.data contains the segmentation masks
        # result.boxes.cls contains the class IDs
        masks = result.masks.data  # Shape: (N, H, W) where N is number of detections
        
        # For building segmentation, we can either:
        # 1. Use all detected objects (assuming model is trained on buildings)
        # 2. Filter by specific class ID if using COCO or custom classes
        # For now, we'll use all detected objects
        
        if len(masks) > 0:
            # Combine all masks using logical OR
            for mask in masks:
                # Resize mask to original image dimensions if needed
                if mask.shape != (height, width):
                    # Convert to numpy and resize
                    mask_np = mask.cpu().numpy()
                    from PIL import Image
                    mask_pil = Image.fromarray((mask_np * 255).astype(np.uint8))
                    mask_pil = mask_pil.resize((width, height), Image.NEAREST)
                    mask_resized = np.array(mask_pil) > 127
                else:
                    mask_resized = mask.cpu().numpy() > 0.5
                
                combined_mask = np.logical_or(combined_mask, mask_resized).astype(np.uint8)
        
        # Convert to binary format (0 or 255)
        combined_mask = combined_mask * 255
        
        return combined_mask

    def instance_segment(self, image: np.ndarray) -> list:
        """
        Return list of per-instance binary masks (one per detected building).

        Returns:
            List of np.ndarray (H, W) uint8 masks with values {0, 255}
        """
        if self.model is None:
            self.load()

        results = self.model.predict(image, verbose=False, task='segment')
        result = results[0]

        if result.masks is None:
            return []

        orig_h, orig_w = result.orig_shape
        instance_masks = []

        for mask_tensor in result.masks.data:
            mask_np = mask_tensor.cpu().numpy()
            if mask_np.shape != (orig_h, orig_w):
                from PIL import Image
                pil = Image.fromarray((mask_np * 255).astype(np.uint8))
                pil = pil.resize((orig_w, orig_h), Image.NEAREST)
                mask_np = np.array(pil)
            else:
                mask_np = (mask_np * 255).astype(np.uint8)

            binary = np.where(mask_np > 127, 255, 0).astype(np.uint8)
            instance_masks.append(binary)

        return instance_masks

    def segment(self, image: np.ndarray) -> np.ndarray:
        """Run full segmentation pipeline."""
        preprocessed = self.preprocess(image)
        raw = self.predict(preprocessed)
        return self.postprocess(raw)
