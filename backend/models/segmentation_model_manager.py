"""
Segmentation Model Manager for managing and routing segmentation requests.

This module provides a centralized manager for loading and executing different
segmentation models (YOLOv8, Mask R-CNN). It implements lazy loading to only
initialize models when first requested, improving startup time and memory usage.
"""

from typing import Dict, Optional
from pathlib import Path
import os
import numpy as np

from .segmentation_model import SegmentationModel


class SegmentationModelManager:
    """
    Manager for segmentation models with lazy loading support.
    
    This class manages multiple segmentation model instances and provides
    a unified interface for loading and executing segmentation. Models are
    loaded lazily - they are only initialized when first requested, which
    improves startup time and reduces memory usage.
    
    Attributes:
        models: Dictionary mapping model names to loaded model instances
        model_configs: Dictionary mapping model names to their configuration
    """
    
    def __init__(self):
        """Initialize the model manager with empty model registry."""
        self.models: Dict[str, SegmentationModel] = {}
        self.model_configs: Dict[str, dict] = {}
        
        # Resolve weights directory relative to this file
        _weights_dir = Path(__file__).parent / 'weights'

        yolov8_path = os.getenv("YOLOV8_MODEL_PATH") or str(_weights_dir / 'best_fixed.pt')
        maskrcnn_path = os.getenv("MASKRCNN_MODEL_PATH") or str(_weights_dir / 'maskrcnn_building_best.pth')

        # Add custom YOLOv8m segmentation model trained on building dataset
        self.model_configs['yolov8m-custom'] = {
            'class': None,
            'model_path': yolov8_path,
        }
        
        # Add custom Mask R-CNN segmentation model trained on building dataset
        self.model_configs['maskrcnn-custom'] = {
            'class': None,
            'model_path': maskrcnn_path,
            'num_classes': 2,
        }
    
    def load_model(self, model_name: str) -> None:
        """
        Load specified model into memory.
        
        This method initializes the specified model and loads its weights.
        If the model is already loaded, this method does nothing (idempotent).
        
        Args:
            model_name: Name of the model to load
        
        Raises:
            ValueError: If model_name is not supported
            Exception: If model loading fails
        """
        # Check if model is already loaded
        if model_name in self.models:
            return
        
        # Validate model name
        if model_name not in self.model_configs:
            supported = ', '.join(self.model_configs.keys())
            raise ValueError(
                f"Unsupported model: '{model_name}'. "
                f"Supported models: {supported}"
            )
        
        # Get model configuration
        config = self.model_configs[model_name]
        model_class = config['class']
        
        # Lazy import the adapter class now (deferred from module load)
        if model_class is None:
            if model_name == 'yolov8m-custom':
                from .yolov8_adapter import YOLOv8Adapter
                model_class = YOLOv8Adapter
            elif model_name == 'maskrcnn-custom':
                from .maskrcnn_adapter import MaskRCNNAdapter
                model_class = MaskRCNNAdapter
        
        # Create model instance based on type
        if model_name == 'yolov8m-custom':
            model = model_class(
                model_path=config['model_path']
            )
        elif model_name == 'maskrcnn-custom':
            model = model_class(
                model_path=config['model_path'],
                num_classes=config.get('num_classes', 2)
            )
        else:
            # Generic fallback for new models
            model = model_class(**{k: v for k, v in config.items() if k != 'class'})
        
        # Load model weights
        model.load()
        
        # Store loaded model
        self.models[model_name] = model
    
    def get_model(self, model_name: str) -> SegmentationModel:
        """
        Get loaded model instance.
        
        This method returns the specified model instance. If the model is not
        yet loaded, it will be loaded automatically (lazy loading).
        
        Args:
            model_name: Name of the model to retrieve
        
        Returns:
            Loaded model instance implementing SegmentationModel interface
        
        Raises:
            ValueError: If model_name is not supported
            Exception: If model loading fails
        """
        # Load model if not already loaded (lazy loading)
        if model_name not in self.models:
            self.load_model(model_name)
        
        return self.models[model_name]
    
    def segment(self, image: np.ndarray, model_name: str) -> np.ndarray:
        """
        Run segmentation using specified model.
        
        This method routes the segmentation request to the appropriate model.
        The model is loaded automatically if not already in memory (lazy loading).
        
        Args:
            image: Input image as numpy array with shape (H, W, C) and dtype uint8
            model_name: Name of the model to use
        
        Returns:
            Binary segmentation mask as numpy array with shape (H, W),
            dtype uint8, and values in {0, 255}
        
        Raises:
            ValueError: If model_name is not supported
            Exception: If segmentation fails
        """
        # Get model (loads if necessary)
        model = self.get_model(model_name)
        
        # Run segmentation
        mask = model.segment(image)
        
        return mask
    
    def is_model_loaded(self, model_name: str) -> bool:
        """
        Check if a model is currently loaded in memory.
        
        Args:
            model_name: Name of the model to check
        
        Returns:
            True if model is loaded, False otherwise
        """
        return model_name in self.models
    
    def unload_model(self, model_name: str) -> None:
        """
        Unload a model from memory.
        
        This method removes the model from the registry, allowing it to be
        garbage collected. Useful for freeing memory when a model is no longer needed.
        
        Args:
            model_name: Name of the model to unload
        """
        if model_name in self.models:
            del self.models[model_name]
    
    def get_available_models(self) -> list:
        """
        Get list of available model names.
        
        Returns:
            List of supported model names
        """
        return list(self.model_configs.keys())
