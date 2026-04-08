"""
Mask R-CNN segmentation adapter for aerial building segmentation.

This module implements the SegmentationModel interface for Mask R-CNN,
providing instance segmentation for building detection in aerial images.
"""

from typing import Any
import numpy as np
import os
import ssl
from pathlib import Path
import torch
import torchvision
from torchvision.models.detection import maskrcnn_resnet50_fpn
from torchvision.models.detection.faster_rcnn import FastRCNNPredictor
from torchvision.models.detection.mask_rcnn import MaskRCNNPredictor
import logging

# Bypass SSL verification for environments with missing/broken certificates
ssl._create_default_https_context = ssl._create_unverified_context

from .segmentation_model import SegmentationModel

logger = logging.getLogger(__name__)


class MaskRCNNAdapter(SegmentationModel):
    """
    Adapter for Mask R-CNN building segmentation model.
    
    This adapter uses a Mask R-CNN model trained specifically on building
    datasets for aerial/satellite imagery segmentation.
    
    Attributes:
        model_path: Path to Mask R-CNN model weights (.pth file)
        model: Loaded Mask R-CNN model
        device: Device for inference (cuda or cpu)
    """
    
    def __init__(self, model_path: str, num_classes: int = 2):
        """
        Initialize MaskRCNNAdapter.
        
        Args:
            model_path: Path to model weights (.pth file)
            num_classes: Number of classes (default: 2 for background + building)
        """
        self.model_path = model_path
        self.num_classes = num_classes
        self.model = None
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.confidence_threshold = 0.5  # Minimum confidence for detections
    
    def load(self) -> None:
        """
        Load Mask R-CNN model from checkpoint.
        
        Creates a Mask R-CNN model with ResNet50-FPN backbone and loads
        the trained weights.
        
        Raises:
            Exception: If model loading fails
        """
        try:
            logger.info(f"Loading Mask R-CNN model from: {self.model_path}")

            # Ensure torch hub cache is not on an inaccessible external drive
            import os as _os
            torch_home = _os.getenv("TORCH_HOME")
            if torch_home:
                _os.environ["TORCH_HOME"] = torch_home
            elif _os.getenv("XDG_CACHE_HOME"):
                # XDG_CACHE_HOME may point to an external drive; fall back to ~/.cache/torch
                _os.environ["TORCH_HOME"] = str(Path.home() / ".cache" / "torch")

            # Create Mask R-CNN model with ResNet50-FPN backbone
            self.model = maskrcnn_resnet50_fpn(pretrained=False)
            
            # Replace the box predictor
            in_features = self.model.roi_heads.box_predictor.cls_score.in_features
            self.model.roi_heads.box_predictor = FastRCNNPredictor(in_features, self.num_classes)
            
            # Replace the mask predictor
            in_features_mask = self.model.roi_heads.mask_predictor.conv5_mask.in_channels
            hidden_layer = 256
            self.model.roi_heads.mask_predictor = MaskRCNNPredictor(
                in_features_mask,
                hidden_layer,
                self.num_classes
            )
            
            # Load trained weights
            checkpoint = torch.load(self.model_path, map_location=self.device, weights_only=False)
            
            # Handle different checkpoint formats
            if isinstance(checkpoint, dict):
                if 'model_state_dict' in checkpoint:
                    state_dict = checkpoint['model_state_dict']
                elif 'state_dict' in checkpoint:
                    state_dict = checkpoint['state_dict']
                else:
                    state_dict = checkpoint
            else:
                state_dict = checkpoint
            
            self.model.load_state_dict(state_dict)
            self.model.to(self.device)
            self.model.eval()
            
            logger.info(f"Mask R-CNN model loaded successfully on {self.device}")
            
        except Exception as e:
            raise Exception(f"Failed to load Mask R-CNN model: {str(e)}")
    
    def preprocess(self, image: np.ndarray) -> torch.Tensor:
        """
        Preprocess image for Mask R-CNN.
        
        Converts numpy array to tensor and normalizes to [0, 1].
        Mask R-CNN handles its own normalization internally.
        
        Args:
            image: Input RGB image as numpy array (H, W, 3)
        
        Returns:
            Preprocessed tensor ready for model inference
        """
        # Convert to tensor and normalize to [0, 1]
        image_tensor = torch.from_numpy(image).float().permute(2, 0, 1) / 255.0
        
        # Move to device
        image_tensor = image_tensor.to(self.device)
        
        return image_tensor
    
    def predict(self, preprocessed_input: torch.Tensor) -> dict:
        """
        Run Mask R-CNN inference.
        
        Args:
            preprocessed_input: Preprocessed image tensor
        
        Returns:
            Dictionary containing boxes, labels, scores, and masks
        
        Raises:
            Exception: If prediction fails
        """
        if self.model is None:
            raise Exception("Model not loaded. Call load() first.")
        
        try:
            with torch.no_grad():
                # Add batch dimension
                image_batch = [preprocessed_input]
                
                # Run inference
                predictions = self.model(image_batch)
                
            return predictions[0]  # Return first (and only) prediction
            
        except Exception as e:
            raise Exception(f"Mask R-CNN prediction failed: {str(e)}")
    
    def postprocess(self, raw_output: dict) -> np.ndarray:
        """
        Convert Mask R-CNN output to binary building mask.
        
        Combines all detected building masks into a single binary mask,
        filtering by confidence threshold.
        
        Args:
            raw_output: Dictionary with 'boxes', 'labels', 'scores', 'masks'
        
        Returns:
            Binary building mask (H, W) with values {0, 255}
        """
        masks = raw_output['masks']
        scores = raw_output['scores']
        labels = raw_output['labels']
        
        # Get image dimensions from first mask
        if len(masks) == 0:
            logger.warning("Mask R-CNN: No detections found")
            # Return empty mask with default size
            return np.zeros((512, 512), dtype=np.uint8)
        
        height, width = masks[0].shape[1:]
        
        # Initialize combined mask
        combined_mask = np.zeros((height, width), dtype=np.float32)
        
        # Filter detections by confidence and combine masks
        num_detections = 0
        for mask, score, label in zip(masks, scores, labels):
            # Filter by confidence threshold and building class (label == 1)
            if score >= self.confidence_threshold and label == 1:
                # Extract mask and threshold
                mask_np = mask[0].cpu().numpy()
                binary_mask = (mask_np > 0.5).astype(np.float32)
                
                # Combine using max (to handle overlaps)
                combined_mask = np.maximum(combined_mask, binary_mask)
                num_detections += 1
        
        logger.info(f"Mask R-CNN: Combined {num_detections} building masks")
        
        # Convert to uint8 binary mask
        binary_mask = (combined_mask * 255).astype(np.uint8)
        
        return binary_mask

    def instance_segment(self, image: np.ndarray) -> list:
        """
        Return list of per-instance binary masks (one per detected building).

        Returns:
            List of np.ndarray (H, W) uint8 masks with values {0, 255}
        """
        if self.model is None:
            self.load()

        image_tensor = self.preprocess(image)
        with torch.no_grad():
            predictions = self.model([image_tensor])
        pred = predictions[0]

        masks = pred['masks']
        scores = pred['scores']
        labels = pred['labels']

        instance_masks = []
        for mask, score, label in zip(masks, scores, labels):
            if score >= self.confidence_threshold and label == 1:
                mask_np = mask[0].cpu().numpy()
                binary = np.where(mask_np > 0.5, 255, 0).astype(np.uint8)
                instance_masks.append(binary)

        logger.info(f"Mask R-CNN instance_segment: {len(instance_masks)} buildings")
        return instance_masks

    def segment(self, image: np.ndarray) -> np.ndarray:
        """Run full segmentation pipeline."""
        preprocessed = self.preprocess(image)
        raw = self.predict(preprocessed)
        return self.postprocess(raw)
