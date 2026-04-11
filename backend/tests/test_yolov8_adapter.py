"""
Unit tests for YOLOv8Adapter.

Tests verify that:
1. YOLOv8Adapter correctly implements the SegmentationModel interface
2. Preprocessing converts images to the correct format for YOLOv8
3. Postprocessing extracts and combines masks correctly into binary output
4. Error handling works correctly for edge cases
"""

import pytest
import numpy as np
import sys
from unittest.mock import Mock, patch, MagicMock

# Mock ultralytics module before importing YOLOv8Adapter
sys.modules['ultralytics'] = Mock()

from backend.models.yolov8_adapter import YOLOv8Adapter


class TestYOLOv8AdapterInitialization:
    """Test YOLOv8Adapter initialization and loading."""
    
    def test_initialization(self):
        """YOLOv8Adapter should initialize with model path."""
        adapter = YOLOv8Adapter(model_path="yolov8n-seg.pt")
        
        assert adapter.model_path == "yolov8n-seg.pt"
        assert adapter.model is None  # Not loaded yet
    
    @patch('backend.models.yolov8_adapter.YOLO')
    def test_load_success(self, mock_yolo):
        """load() should successfully initialize YOLOv8 model."""
        # Setup mock
        mock_model = Mock()
        mock_yolo.return_value = mock_model
        
        adapter = YOLOv8Adapter(model_path="yolov8n-seg.pt")
        adapter.load()
        
        # Verify YOLO was called with correct path
        mock_yolo.assert_called_once_with("yolov8n-seg.pt")
        
        # Verify model is set
        assert adapter.model == mock_model
    
    @patch('backend.models.yolov8_adapter.YOLO')
    def test_load_failure(self, mock_yolo):
        """load() should raise exception if model loading fails."""
        mock_yolo.side_effect = Exception("Model file not found")
        
        adapter = YOLOv8Adapter(model_path="invalid.pt")
        
        with pytest.raises(Exception, match="Failed to load YOLOv8 model"):
            adapter.load()


class TestYOLOv8AdapterPreprocessing:
    """Test YOLOv8Adapter preprocessing."""
    
    def test_preprocess_valid_rgb_image(self):
        """preprocess() should accept valid RGB uint8 images."""
        adapter = YOLOv8Adapter(model_path="yolov8n-seg.pt")
        
        image = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
        preprocessed = adapter.preprocess(image)
        
        assert preprocessed.shape == (100, 100, 3)
        assert preprocessed.dtype == np.uint8
        assert np.array_equal(preprocessed, image)
    
    def test_preprocess_converts_dtype(self):
        """preprocess() should convert non-uint8 images to uint8."""
        adapter = YOLOv8Adapter(model_path="yolov8n-seg.pt")
        
        # Create float32 image
        image = np.random.rand(100, 100, 3).astype(np.float32) * 255
        preprocessed = adapter.preprocess(image)
        
        assert preprocessed.dtype == np.uint8
        assert preprocessed.shape == (100, 100, 3)
    
    def test_preprocess_rejects_wrong_channels(self):
        """preprocess() should reject images without 3 channels."""
        adapter = YOLOv8Adapter(model_path="yolov8n-seg.pt")
        
        # Test with 4 channels (RGBA)
        image_rgba = np.random.randint(0, 256, (100, 100, 4), dtype=np.uint8)
        with pytest.raises(ValueError, match="Expected 3-channel RGB image"):
            adapter.preprocess(image_rgba)
        
        # Test with 1 channel (grayscale)
        image_gray = np.random.randint(0, 256, (100, 100, 1), dtype=np.uint8)
        with pytest.raises(ValueError, match="Expected 3-channel RGB image"):
            adapter.preprocess(image_gray)
    
    def test_preprocess_various_sizes(self):
        """preprocess() should handle various image sizes."""
        adapter = YOLOv8Adapter(model_path="yolov8n-seg.pt")
        
        test_sizes = [(64, 64, 3), (128, 256, 3), (512, 512, 3), (1024, 768, 3)]
        
        for size in test_sizes:
            image = np.random.randint(0, 256, size, dtype=np.uint8)
            preprocessed = adapter.preprocess(image)
            
            assert preprocessed.shape == size
            assert preprocessed.dtype == np.uint8


class TestYOLOv8AdapterPrediction:
    """Test YOLOv8Adapter prediction."""
    
    @patch('backend.models.yolov8_adapter.YOLO')
    def test_predict_success(self, mock_yolo):
        """predict() should call YOLOv8 model and return results."""
        # Setup mocks
        mock_model = Mock()
        mock_results = [Mock()]
        mock_model.return_value = mock_results
        mock_yolo.return_value = mock_model
        
        adapter = YOLOv8Adapter(model_path="yolov8n-seg.pt")
        adapter.load()
        
        image = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
        results = adapter.predict(image)
        
        # Verify model was called with verbose=False
        mock_model.assert_called_once_with(image, verbose=False)
        
        # Verify results are returned
        assert results == mock_results
    
    def test_predict_without_loading(self):
        """predict() should raise exception if model not loaded."""
        adapter = YOLOv8Adapter(model_path="yolov8n-seg.pt")
        
        image = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
        
        with pytest.raises(Exception, match="Model not loaded"):
            adapter.predict(image)
    
    @patch('backend.models.yolov8_adapter.YOLO')
    def test_predict_failure(self, mock_yolo):
        """predict() should raise exception if YOLOv8 prediction fails."""
        # Setup mocks
        mock_model = Mock()
        mock_model.side_effect = RuntimeError("CUDA out of memory")
        mock_yolo.return_value = mock_model
        
        adapter = YOLOv8Adapter(model_path="yolov8n-seg.pt")
        adapter.load()
        
        image = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
        
        with pytest.raises(Exception, match="YOLOv8 prediction failed"):
            adapter.predict(image)


class TestYOLOv8AdapterPostprocessing:
    """Test YOLOv8Adapter postprocessing."""
    
    def test_postprocess_single_mask(self):
        """postprocess() should convert single mask to binary format."""
        adapter = YOLOv8Adapter(model_path="yolov8n-seg.pt")
        
        # Create mock YOLOv8 result with one mask
        mock_mask_data = Mock()
        mask_tensor = Mock()
        mask_array = np.zeros((100, 100), dtype=np.float32)
        mask_array[20:80, 30:70] = 1.0  # Building region
        mask_tensor.cpu.return_value.numpy.return_value = mask_array
        mock_mask_data.__len__ = Mock(return_value=1)
        mock_mask_data.__iter__ = Mock(return_value=iter([mask_tensor]))
        
        mock_masks = Mock()
        mock_masks.data = mock_mask_data
        
        mock_result = Mock()
        mock_result.orig_shape = (100, 100)
        mock_result.masks = mock_masks
        
        raw_output = [mock_result]
        
        result = adapter.postprocess(raw_output)
        
        assert result.shape == (100, 100)
        assert result.dtype == np.uint8
        assert set(np.unique(result)).issubset({0, 255})
        # Building region should be marked
        assert np.all(result[20:80, 30:70] == 255)
    
    def test_postprocess_multiple_masks(self):
        """postprocess() should combine multiple masks using logical OR."""
        adapter = YOLOv8Adapter(model_path="yolov8n-seg.pt")
        
        # Create two non-overlapping masks
        mask1_array = np.zeros((100, 100), dtype=np.float32)
        mask1_array[10:30, 10:30] = 1.0  # Top-left building
        
        mask2_array = np.zeros((100, 100), dtype=np.float32)
        mask2_array[70:90, 70:90] = 1.0  # Bottom-right building
        
        mask1_tensor = Mock()
        mask1_tensor.cpu.return_value.numpy.return_value = mask1_array
        mask1_tensor.shape = (100, 100)
        
        mask2_tensor = Mock()
        mask2_tensor.cpu.return_value.numpy.return_value = mask2_array
        mask2_tensor.shape = (100, 100)
        
        mock_mask_data = Mock()
        mock_mask_data.__len__ = Mock(return_value=2)
        mock_mask_data.__iter__ = Mock(return_value=iter([mask1_tensor, mask2_tensor]))
        
        mock_masks = Mock()
        mock_masks.data = mock_mask_data
        
        mock_result = Mock()
        mock_result.orig_shape = (100, 100)
        mock_result.masks = mock_masks
        
        raw_output = [mock_result]
        
        result = adapter.postprocess(raw_output)
        
        assert result.shape == (100, 100)
        assert result.dtype == np.uint8
        assert set(np.unique(result)).issubset({0, 255})
        # Both regions should be marked as building
        assert np.all(result[10:30, 10:30] == 255)
        assert np.all(result[70:90, 70:90] == 255)
        # Background should be 0
        assert result[0, 0] == 0
        assert result[50, 50] == 0
    
    def test_postprocess_no_detections(self):
        """postprocess() should return empty mask when no objects detected."""
        adapter = YOLOv8Adapter(model_path="yolov8n-seg.pt")
        
        # Create mock result with no masks
        mock_result = Mock()
        mock_result.orig_shape = (100, 100)
        mock_result.masks = None  # No detections
        
        raw_output = [mock_result]
        
        result = adapter.postprocess(raw_output)
        
        assert result.shape == (100, 100)
        assert result.dtype == np.uint8
        # All pixels should be background
        assert np.all(result == 0)
    
    def test_postprocess_empty_mask_list(self):
        """postprocess() should handle empty mask list."""
        adapter = YOLOv8Adapter(model_path="yolov8n-seg.pt")
        
        # Create mock result with empty mask list
        mock_mask_data = Mock()
        mock_mask_data.__len__ = Mock(return_value=0)
        mock_mask_data.__iter__ = Mock(return_value=iter([]))
        
        mock_masks = Mock()
        mock_masks.data = mock_mask_data
        
        mock_result = Mock()
        mock_result.orig_shape = (100, 100)
        mock_result.masks = mock_masks
        
        raw_output = [mock_result]
        
        result = adapter.postprocess(raw_output)
        
        assert result.shape == (100, 100)
        assert result.dtype == np.uint8
        # All pixels should be background
        assert np.all(result == 0)
    
    def test_postprocess_with_resize(self):
        """postprocess() should resize masks to original dimensions if needed."""
        adapter = YOLOv8Adapter(model_path="yolov8n-seg.pt")
        
        # Create mask with different size than original
        mask_array = np.ones((50, 50), dtype=np.float32)  # Smaller than original
        
        mask_tensor = Mock()
        mask_tensor.cpu.return_value.numpy.return_value = mask_array
        mask_tensor.shape = (50, 50)  # Different from orig_shape
        
        mock_mask_data = Mock()
        mock_mask_data.__len__ = Mock(return_value=1)
        mock_mask_data.__iter__ = Mock(return_value=iter([mask_tensor]))
        
        mock_masks = Mock()
        mock_masks.data = mock_mask_data
        
        mock_result = Mock()
        mock_result.orig_shape = (100, 100)  # Original size
        mock_result.masks = mock_masks
        
        # Mock PIL Image operations
        mock_pil = Mock()
        mock_resized = Mock()
        mock_resized_array = np.ones((100, 100), dtype=np.uint8) * 255
        mock_pil.resize.return_value = mock_resized
        
        # Patch PIL.Image inside the postprocess method
        with patch('PIL.Image.fromarray', return_value=mock_pil):
            with patch('numpy.array', return_value=mock_resized_array):
                raw_output = [mock_result]
                result = adapter.postprocess(raw_output)
        
        assert result.shape == (100, 100)
        assert result.dtype == np.uint8


class TestYOLOv8AdapterIntegration:
    """Test complete YOLOv8Adapter pipeline."""
    
    @patch('backend.models.yolov8_adapter.YOLO')
    def test_complete_segment_pipeline(self, mock_yolo):
        """Test complete segment() pipeline from image to binary mask."""
        # Setup mocks
        mock_model = Mock()
        
        # Create realistic mask output
        mask_array = np.zeros((256, 256), dtype=np.float32)
        mask_array[50:150, 50:150] = 1.0  # Building in center
        
        mask_tensor = Mock()
        mask_tensor.cpu.return_value.numpy.return_value = mask_array
        mask_tensor.shape = (256, 256)
        
        mock_mask_data = Mock()
        mock_mask_data.__len__ = Mock(return_value=1)
        mock_mask_data.__iter__ = Mock(return_value=iter([mask_tensor]))
        
        mock_masks = Mock()
        mock_masks.data = mock_mask_data
        
        mock_result = Mock()
        mock_result.orig_shape = (256, 256)
        mock_result.masks = mock_masks
        
        mock_model.return_value = [mock_result]
        mock_yolo.return_value = mock_model
        
        # Create adapter and load
        adapter = YOLOv8Adapter(model_path="yolov8n-seg.pt")
        adapter.load()
        
        # Create test image
        image = np.random.randint(0, 256, (256, 256, 3), dtype=np.uint8)
        
        # Run complete pipeline
        result = adapter.segment(image)
        
        # Verify output
        assert result.shape == (256, 256)
        assert result.dtype == np.uint8
        assert set(np.unique(result)).issubset({0, 255})
        assert np.all(result[50:150, 50:150] == 255)  # Building region
        assert result[0, 0] == 0  # Background
