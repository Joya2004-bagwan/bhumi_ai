"""
Abstract base class for segmentation models.

This module defines the common interface that all segmentation models must implement.
The SegmentationModel class provides a template method pattern where the segment()
method orchestrates the complete segmentation pipeline by calling abstract methods
that subclasses must implement.
"""

from abc import ABC, abstractmethod
from typing import Any
import numpy as np


class SegmentationModel(ABC):
    """
    Abstract base class for all segmentation models.
    
    This class defines the interface that all segmentation models (YOLOv8, Mask R-CNN)
    must implement. It provides a common segment() method that orchestrates the
    segmentation pipeline by calling model-specific preprocessing, prediction,
    and postprocessing methods.
    
    Subclasses must implement:
    - load(): Initialize and load model weights
    - preprocess(): Apply model-specific preprocessing to input images
    - predict(): Run model inference on preprocessed input
    - postprocess(): Convert model output to binary mask format
    """
    
    @abstractmethod
    def load(self) -> None:
        """
        Load model weights and initialize the model.
        
        This method should handle all model initialization including:
        - Loading model weights from disk
        - Setting up the model architecture
        - Moving model to appropriate device (CPU/GPU)
        - Setting model to evaluation mode
        
        Raises:
            Exception: If model loading fails
        """
        pass
    
    @abstractmethod
    def preprocess(self, image: np.ndarray) -> Any:
        """
        Apply model-specific preprocessing to the input image.
        
        This method should handle all preprocessing steps required by the specific
        model, such as:
        - Color space conversion (RGB, BGR, etc.)
        - Normalization
        - Resizing
        - Tensor conversion
        
        Args:
            image: Input image as numpy array with shape (H, W, C) and dtype uint8
        
        Returns:
            Preprocessed input in the format expected by the model's predict() method.
            The return type is model-specific (e.g., numpy array, torch tensor, etc.)
        """
        pass
    
    @abstractmethod
    def predict(self, preprocessed_input: Any) -> Any:
        """
        Run model inference on preprocessed input.
        
        This method should:
        - Run the model's forward pass
        - Return raw model output without postprocessing
        
        Args:
            preprocessed_input: Preprocessed input from preprocess() method
        
        Returns:
            Raw model output in model-specific format (e.g., logits, masks, etc.)
        """
        pass
    
    @abstractmethod
    def postprocess(self, raw_output: Any) -> np.ndarray:
        """
        Convert raw model output to binary segmentation mask.
        
        This method should:
        - Apply thresholding or argmax operations
        - Convert to binary format (0 for background, 255 for building)
        - Resize to original image dimensions if needed
        - Return as uint8 numpy array
        
        Args:
            raw_output: Raw output from predict() method
        
        Returns:
            Binary segmentation mask as numpy array with shape (H, W),
            dtype uint8, and values in {0, 255}
        """
        pass
    
    def segment(self, image: np.ndarray) -> np.ndarray:
        """
        Complete segmentation pipeline.
        
        This method implements the template method pattern, orchestrating the
        complete segmentation workflow by calling the abstract methods in sequence:
        1. Preprocess the input image
        2. Run model prediction
        3. Postprocess the output to binary mask
        
        This method is implemented in the base class and should not be overridden
        by subclasses. Subclasses customize behavior by implementing the abstract
        methods.
        
        Args:
            image: Input image as numpy array with shape (H, W, C) and dtype uint8
        
        Returns:
            Binary segmentation mask as numpy array with shape (H, W),
            dtype uint8, and values in {0, 255}
        
        Raises:
            Exception: If any step in the pipeline fails
        """
        preprocessed = self.preprocess(image)
        raw_output = self.predict(preprocessed)
        mask = self.postprocess(raw_output)
        return mask
