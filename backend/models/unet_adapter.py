"""
U-Net adapter for aerial image segmentation.

This module implements the SegmentationModel interface for U-Net, providing
semantic segmentation for building detection in aerial images using the
classic encoder-decoder architecture.
"""

from typing import Any
import numpy as np
import torch
import torch.nn as nn
from PIL import Image

from .segmentation_model import SegmentationModel


class UNetAdapter(SegmentationModel):
    """
    Adapter for U-Net segmentation model.
    
    This adapter uses U-Net's encoder-decoder architecture for semantic
    segmentation of buildings in aerial images. U-Net is widely used for
    image segmentation tasks and provides good accuracy for building detection.
    
    Attributes:
        model_path: Path to U-Net model weights file
        framework: Framework used ('pytorch' or 'tensorflow')
        model: U-Net model instance
        input_size: Fixed input size for U-Net (height, width)
        device: Device to run model on ('cuda' or 'cpu')
    """
    
    def __init__(self, model_path: str, framework: str = "pytorch"):
        """
        Initialize UNetAdapter.
        
        Args:
            model_path: Path to U-Net weights file
            framework: Framework to use ('pytorch' or 'tensorflow')
        """
        self.model_path = model_path
        self.framework = framework
        self.model = None
        self.input_size = (256, 256)  # Standard U-Net input size
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
    
    def load(self) -> None:
        """
        Load U-Net model.
        
        Currently supports PyTorch models. The model should be a standard
        U-Net architecture with a single output channel for binary segmentation.
        
        Raises:
            Exception: If model loading fails
        """
        if self.framework != "pytorch":
            raise NotImplementedError(f"Framework '{self.framework}' not yet supported. Use 'pytorch'.")
        
        try:
            # Load PyTorch model
            self.model = torch.load(self.model_path, map_location=self.device)
            
            # If the loaded object is a state dict, we need a model architecture
            if isinstance(self.model, dict):
                # For now, we'll raise an error - user should provide full model
                raise ValueError(
                    "Loaded a state dict instead of a model. "
                    "Please save the full model using torch.save(model, path) "
                    "instead of torch.save(model.state_dict(), path)"
                )
            
            # Set model to evaluation mode
            self.model.eval()
            self.model.to(self.device)
            
        except Exception as e:
            raise Exception(f"Failed to load U-Net model: {str(e)}")
    
    def preprocess(self, image: np.ndarray) -> torch.Tensor:
        """
        Apply U-Net-specific preprocessing.
        
        U-Net requires:
        1. Resize to fixed input size (256x256)
        2. Normalize pixel values to [0, 1]
        3. Convert to tensor with shape (1, C, H, W)
        
        Args:
            image: Input image as numpy array with shape (H, W, C)
        
        Returns:
            Preprocessed image as PyTorch tensor with shape (1, 3, 256, 256)
        """
        # Store original dimensions for later resizing
        self.original_size = (image.shape[0], image.shape[1])  # (height, width)
        
        # Ensure image is RGB
        if image.shape[2] != 3:
            raise ValueError(f"Expected 3-channel RGB image, got {image.shape[2]} channels")
        
        # Resize to fixed input size using PIL
        image_pil = Image.fromarray(image)
        image_resized = image_pil.resize(
            (self.input_size[1], self.input_size[0]),  # PIL uses (width, height)
            Image.BILINEAR
        )
        
        # Convert back to numpy array
        image_np = np.array(image_resized)
        
        # Normalize to [0, 1]
        image_normalized = image_np.astype(np.float32) / 255.0
        
        # Convert to tensor: (H, W, C) -> (C, H, W)
        image_tensor = torch.from_numpy(image_normalized).permute(2, 0, 1)
        
        # Add batch dimension: (C, H, W) -> (1, C, H, W)
        image_tensor = image_tensor.unsqueeze(0)
        
        # Move to device
        image_tensor = image_tensor.to(self.device)
        
        return image_tensor
    
    def predict(self, preprocessed_input: torch.Tensor) -> torch.Tensor:
        """
        Run U-Net forward pass.
        
        Args:
            preprocessed_input: Preprocessed image tensor with shape (1, 3, H, W)
        
        Returns:
            Raw model output (logits) with shape (1, 1, H, W)
        
        Raises:
            Exception: If prediction fails
        """
        if self.model is None:
            raise Exception("Model not loaded. Call load() first.")
        
        try:
            # Run inference without gradient computation
            with torch.no_grad():
                output = self.model(preprocessed_input)
            
            return output
            
        except Exception as e:
            raise Exception(f"U-Net prediction failed: {str(e)}")
    
    def postprocess(self, raw_output: torch.Tensor) -> np.ndarray:
        """
        Convert U-Net output to binary segmentation mask.
        
        This method:
        1. Applies sigmoid activation to convert logits to probabilities
        2. Thresholds at 0.5 to create binary mask
        3. Resizes back to original image dimensions
        4. Converts to uint8 format with values {0, 255}
        
        Args:
            raw_output: Raw model output tensor with shape (1, 1, H, W)
        
        Returns:
            Binary segmentation mask with shape (orig_H, orig_W), dtype uint8,
            and values in {0, 255}
        """
        # Apply sigmoid to convert logits to probabilities
        probabilities = torch.sigmoid(raw_output)
        
        # Threshold at 0.5 to create binary mask
        binary_mask = (probabilities > 0.5).float()
        
        # Remove batch and channel dimensions: (1, 1, H, W) -> (H, W)
        binary_mask = binary_mask.squeeze(0).squeeze(0)
        
        # Convert to numpy array
        mask_np = binary_mask.cpu().numpy()
        
        # Resize back to original dimensions
        mask_pil = Image.fromarray((mask_np * 255).astype(np.uint8))
        mask_resized = mask_pil.resize(
            (self.original_size[1], self.original_size[0]),  # PIL uses (width, height)
            Image.NEAREST  # Use nearest neighbor to preserve binary values
        )
        
        # Convert to numpy array with uint8 dtype
        final_mask = np.array(mask_resized, dtype=np.uint8)
        
        return final_mask
