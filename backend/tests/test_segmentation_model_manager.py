"""
Unit tests for SegmentationModelManager.

This module tests the model manager's ability to load, manage, and route
segmentation requests to different models with lazy loading support.
"""

import pytest
import numpy as np
import sys
from unittest.mock import Mock, patch, MagicMock

# Mock torch and model-specific modules before importing
mock_torch = MagicMock()
mock_torch.nn = MagicMock()
mock_torch.cuda = MagicMock()
mock_torch.cuda.is_available = MagicMock(return_value=False)
sys.modules['torch'] = mock_torch
sys.modules['torch.nn'] = mock_torch.nn
sys.modules['ultralytics'] = Mock()
sys.modules['torchvision'] = MagicMock()
sys.modules['torchvision.models'] = MagicMock()
sys.modules['torchvision.models.detection'] = MagicMock()
sys.modules['torchvision.models.detection.faster_rcnn'] = MagicMock()
sys.modules['torchvision.models.detection.mask_rcnn'] = MagicMock()

from backend.models.segmentation_model_manager import SegmentationModelManager
from backend.models.segmentation_model import SegmentationModel

# Patch targets — adapters are lazily imported inside load_model()
YOLO_PATCH = 'backend.models.yolov8_adapter.YOLOv8Adapter'
MASKRCNN_PATCH = 'backend.models.maskrcnn_adapter.MaskRCNNAdapter'


class TestSegmentationModelManager:
    """Test suite for SegmentationModelManager."""

    def test_initialization(self):
        """Test that manager initializes with empty model registry."""
        manager = SegmentationModelManager()

        assert isinstance(manager.models, dict)
        assert len(manager.models) == 0
        assert 'yolov8m-custom' in manager.model_configs
        assert 'maskrcnn-custom' in manager.model_configs

    def test_get_available_models(self):
        """Test getting list of available models."""
        manager = SegmentationModelManager()
        available = manager.get_available_models()

        assert isinstance(available, list)
        assert 'yolov8m-custom' in available
        assert 'maskrcnn-custom' in available
        assert len(available) == 2

    def test_is_model_loaded_false(self):
        """Test checking if model is loaded when it's not."""
        manager = SegmentationModelManager()

        assert manager.is_model_loaded('yolov8m-custom') is False
        assert manager.is_model_loaded('maskrcnn-custom') is False

    def test_load_model_invalid_name(self):
        """Test loading model with invalid name raises ValueError."""
        manager = SegmentationModelManager()

        with pytest.raises(ValueError) as exc_info:
            manager.load_model('invalid_model')

        assert 'Unsupported model' in str(exc_info.value)
        assert 'invalid_model' in str(exc_info.value)

    @patch(YOLO_PATCH)
    def test_load_model_yolov8(self, mock_yolo_class):
        """Test loading YOLOv8 model."""
        mock_model = Mock(spec=SegmentationModel)
        mock_yolo_class.return_value = mock_model

        manager = SegmentationModelManager()
        manager.load_model('yolov8m-custom')

        mock_yolo_class.assert_called_once()
        mock_model.load.assert_called_once()
        assert 'yolov8m-custom' in manager.models
        assert manager.is_model_loaded('yolov8m-custom') is True

    @patch(MASKRCNN_PATCH)
    def test_load_model_maskrcnn(self, mock_maskrcnn_class):
        """Test loading Mask R-CNN model."""
        mock_model = Mock(spec=SegmentationModel)
        mock_maskrcnn_class.return_value = mock_model

        manager = SegmentationModelManager()
        manager.load_model('maskrcnn-custom')

        mock_maskrcnn_class.assert_called_once()
        mock_model.load.assert_called_once()
        assert 'maskrcnn-custom' in manager.models
        assert manager.is_model_loaded('maskrcnn-custom') is True

    @patch(YOLO_PATCH)
    def test_load_model_idempotent(self, mock_yolo_class):
        """Test that loading same model twice doesn't reload it."""
        mock_model = Mock(spec=SegmentationModel)
        mock_yolo_class.return_value = mock_model

        manager = SegmentationModelManager()
        manager.load_model('yolov8m-custom')
        manager.load_model('yolov8m-custom')

        mock_yolo_class.assert_called_once()
        mock_model.load.assert_called_once()

    @patch(YOLO_PATCH)
    def test_get_model_already_loaded(self, mock_yolo_class):
        """Test getting model that's already loaded."""
        mock_model = Mock(spec=SegmentationModel)
        mock_yolo_class.return_value = mock_model

        manager = SegmentationModelManager()
        manager.load_model('yolov8m-custom')
        retrieved_model = manager.get_model('yolov8m-custom')

        assert retrieved_model == mock_model
        mock_model.load.assert_called_once()

    @patch(MASKRCNN_PATCH)
    def test_get_model_lazy_loading(self, mock_maskrcnn_class):
        """Test that get_model loads model if not already loaded (lazy loading)."""
        mock_model = Mock(spec=SegmentationModel)
        mock_maskrcnn_class.return_value = mock_model

        manager = SegmentationModelManager()
        retrieved_model = manager.get_model('maskrcnn-custom')

        mock_maskrcnn_class.assert_called_once()
        mock_model.load.assert_called_once()
        assert retrieved_model == mock_model
        assert manager.is_model_loaded('maskrcnn-custom') is True

    def test_get_model_invalid_name(self):
        """Test getting model with invalid name raises ValueError."""
        manager = SegmentationModelManager()

        with pytest.raises(ValueError) as exc_info:
            manager.get_model('nonexistent')

        assert 'Unsupported model' in str(exc_info.value)

    @patch(YOLO_PATCH)
    def test_segment(self, mock_yolo_class):
        """Test segmentation routing to correct model."""
        mock_model = Mock(spec=SegmentationModel)
        expected_mask = np.zeros((100, 100), dtype=np.uint8)
        mock_model.segment.return_value = expected_mask
        mock_model.load.return_value = None
        mock_yolo_class.return_value = mock_model

        manager = SegmentationModelManager()
        test_image = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
        result_mask = manager.segment(test_image, 'yolov8m-custom')

        mock_yolo_class.assert_called_once()
        mock_model.load.assert_called_once()
        mock_model.segment.assert_called_once()
        np.testing.assert_array_equal(result_mask, expected_mask)

    @patch(MASKRCNN_PATCH)
    @patch(YOLO_PATCH)
    def test_segment_multiple_models(self, mock_yolo_class, mock_maskrcnn_class):
        """Test segmentation with different models maintains independence."""
        mock_yolo = Mock(spec=SegmentationModel)
        mock_maskrcnn = Mock(spec=SegmentationModel)

        yolo_mask = np.ones((50, 50), dtype=np.uint8) * 255
        maskrcnn_mask = np.zeros((50, 50), dtype=np.uint8)

        mock_yolo.segment.return_value = yolo_mask
        mock_maskrcnn.segment.return_value = maskrcnn_mask
        mock_yolo.load.return_value = None
        mock_maskrcnn.load.return_value = None

        mock_yolo_class.return_value = mock_yolo
        mock_maskrcnn_class.return_value = mock_maskrcnn

        manager = SegmentationModelManager()
        test_image = np.random.randint(0, 256, (50, 50, 3), dtype=np.uint8)

        result1 = manager.segment(test_image, 'yolov8m-custom')
        result2 = manager.segment(test_image, 'maskrcnn-custom')

        assert manager.is_model_loaded('yolov8m-custom')
        assert manager.is_model_loaded('maskrcnn-custom')
        np.testing.assert_array_equal(result1, yolo_mask)
        np.testing.assert_array_equal(result2, maskrcnn_mask)

    @patch(YOLO_PATCH)
    def test_unload_model(self, mock_yolo_class):
        """Test unloading a model from memory."""
        mock_model = Mock(spec=SegmentationModel)
        mock_yolo_class.return_value = mock_model

        manager = SegmentationModelManager()
        manager.load_model('yolov8m-custom')
        assert manager.is_model_loaded('yolov8m-custom')

        manager.unload_model('yolov8m-custom')
        assert manager.is_model_loaded('yolov8m-custom') is False

    def test_unload_model_not_loaded(self):
        """Test unloading model that's not loaded doesn't raise error."""
        manager = SegmentationModelManager()
        manager.unload_model('yolov8m-custom')
        assert manager.is_model_loaded('yolov8m-custom') is False

    @patch(YOLO_PATCH)
    def test_model_loading_failure(self, mock_yolo_class):
        """Test that model loading failures are propagated."""
        mock_model = Mock(spec=SegmentationModel)
        mock_model.load.side_effect = Exception("Model file not found")
        mock_yolo_class.return_value = mock_model

        manager = SegmentationModelManager()

        with pytest.raises(Exception) as exc_info:
            manager.load_model('yolov8m-custom')

        assert "Model file not found" in str(exc_info.value)
        assert manager.is_model_loaded('yolov8m-custom') is False

    @patch(YOLO_PATCH)
    def test_segment_with_model_error(self, mock_yolo_class):
        """Test that segmentation errors are propagated."""
        mock_model = Mock(spec=SegmentationModel)
        mock_model.load.return_value = None
        mock_model.segment.side_effect = Exception("Segmentation failed")
        mock_yolo_class.return_value = mock_model

        manager = SegmentationModelManager()
        test_image = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)

        with pytest.raises(Exception) as exc_info:
            manager.segment(test_image, 'yolov8m-custom')

        assert "Segmentation failed" in str(exc_info.value)
