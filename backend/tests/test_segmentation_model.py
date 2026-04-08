"""
Unit tests for SegmentationModel abstract base class.

Tests verify that:
1. SegmentationModel cannot be instantiated directly (abstract class)
2. Subclasses must implement all abstract methods
3. The segment() pipeline correctly orchestrates preprocessing, prediction, and postprocessing
4. The segment() method is implemented in the base class and works correctly
"""

import pytest
import numpy as np
from backend.models.segmentation_model import SegmentationModel


class TestSegmentationModelAbstract:
    """Test that SegmentationModel is properly abstract."""
    
    def test_cannot_instantiate_abstract_class(self):
        """SegmentationModel cannot be instantiated directly."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            SegmentationModel()
    
    def test_missing_load_method(self):
        """Subclass without load() method cannot be instantiated."""
        class IncompleteModel(SegmentationModel):
            def preprocess(self, image):
                return image
            def predict(self, preprocessed_input):
                return preprocessed_input
            def postprocess(self, raw_output):
                return raw_output
        
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            IncompleteModel()
    
    def test_missing_preprocess_method(self):
        """Subclass without preprocess() method cannot be instantiated."""
        class IncompleteModel(SegmentationModel):
            def load(self):
                pass
            def predict(self, preprocessed_input):
                return preprocessed_input
            def postprocess(self, raw_output):
                return raw_output
        
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            IncompleteModel()
    
    def test_missing_predict_method(self):
        """Subclass without predict() method cannot be instantiated."""
        class IncompleteModel(SegmentationModel):
            def load(self):
                pass
            def preprocess(self, image):
                return image
            def postprocess(self, raw_output):
                return raw_output
        
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            IncompleteModel()
    
    def test_missing_postprocess_method(self):
        """Subclass without postprocess() method cannot be instantiated."""
        class IncompleteModel(SegmentationModel):
            def load(self):
                pass
            def preprocess(self, image):
                return image
            def predict(self, preprocessed_input):
                return preprocessed_input
        
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            IncompleteModel()


class TestSegmentationModelPipeline:
    """Test the segment() pipeline orchestration."""
    
    @pytest.fixture
    def mock_model(self):
        """Create a concrete implementation of SegmentationModel for testing."""
        class MockSegmentationModel(SegmentationModel):
            def __init__(self):
                self.load_called = False
                self.preprocess_called = False
                self.predict_called = False
                self.postprocess_called = False
            
            def load(self):
                self.load_called = True
            
            def preprocess(self, image):
                self.preprocess_called = True
                # Simulate preprocessing: normalize to [0, 1]
                return image.astype(np.float32) / 255.0
            
            def predict(self, preprocessed_input):
                self.predict_called = True
                # Simulate prediction: threshold at 0.5
                return (preprocessed_input.mean(axis=2) > 0.5).astype(np.float32)
            
            def postprocess(self, raw_output):
                self.postprocess_called = True
                # Convert to binary mask (0 or 255)
                return (raw_output * 255).astype(np.uint8)
        
        return MockSegmentationModel()
    
    def test_segment_calls_all_methods_in_order(self, mock_model):
        """segment() should call preprocess, predict, and postprocess in order."""
        # Create a simple test image
        image = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
        
        # Run segmentation
        mask = mock_model.segment(image)
        
        # Verify all methods were called
        assert mock_model.preprocess_called, "preprocess() was not called"
        assert mock_model.predict_called, "predict() was not called"
        assert mock_model.postprocess_called, "postprocess() was not called"
        
        # Verify output is correct shape and type
        assert mask.shape == (100, 100), f"Expected shape (100, 100), got {mask.shape}"
        assert mask.dtype == np.uint8, f"Expected dtype uint8, got {mask.dtype}"
        assert set(np.unique(mask)).issubset({0, 255}), "Mask should only contain 0 or 255"
    
    def test_segment_returns_binary_mask(self, mock_model):
        """segment() should return a binary mask with values 0 or 255."""
        image = np.random.randint(0, 256, (50, 50, 3), dtype=np.uint8)
        mask = mock_model.segment(image)
        
        # Check that mask is binary
        unique_values = np.unique(mask)
        assert len(unique_values) <= 2, f"Expected at most 2 unique values, got {len(unique_values)}"
        assert all(v in [0, 255] for v in unique_values), f"Expected only 0 or 255, got {unique_values}"
    
    def test_segment_with_different_image_sizes(self, mock_model):
        """segment() should work with various image dimensions."""
        test_sizes = [(64, 64, 3), (128, 256, 3), (512, 512, 3), (100, 200, 3)]
        
        for size in test_sizes:
            image = np.random.randint(0, 256, size, dtype=np.uint8)
            mask = mock_model.segment(image)
            
            # Verify output shape matches input height and width
            assert mask.shape == (size[0], size[1]), \
                f"For input {size}, expected mask shape {(size[0], size[1])}, got {mask.shape}"
            assert mask.dtype == np.uint8
    
    def test_segment_pipeline_data_flow(self):
        """Test that data flows correctly through the pipeline."""
        class TrackingModel(SegmentationModel):
            def __init__(self):
                self.pipeline_data = []
            
            def load(self):
                pass
            
            def preprocess(self, image):
                self.pipeline_data.append(('preprocess', image.shape, image.dtype))
                return image.astype(np.float32)
            
            def predict(self, preprocessed_input):
                self.pipeline_data.append(('predict', preprocessed_input.shape, preprocessed_input.dtype))
                return preprocessed_input[:, :, 0]  # Take first channel
            
            def postprocess(self, raw_output):
                self.pipeline_data.append(('postprocess', raw_output.shape, raw_output.dtype))
                return (raw_output > 128).astype(np.uint8) * 255
        
        model = TrackingModel()
        image = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
        mask = model.segment(image)
        
        # Verify pipeline execution order
        assert len(model.pipeline_data) == 3
        assert model.pipeline_data[0][0] == 'preprocess'
        assert model.pipeline_data[1][0] == 'predict'
        assert model.pipeline_data[2][0] == 'postprocess'
        
        # Verify data types flow correctly
        assert model.pipeline_data[0][2] == np.uint8  # Input is uint8
        assert model.pipeline_data[1][2] == np.float32  # After preprocess is float32
        assert model.pipeline_data[2][2] == np.float32  # Predict output is float32


class TestSegmentationModelEdgeCases:
    """Test edge cases and error conditions."""
    
    @pytest.fixture
    def simple_model(self):
        """Create a simple concrete model for edge case testing."""
        class SimpleModel(SegmentationModel):
            def load(self):
                pass
            
            def preprocess(self, image):
                return image
            
            def predict(self, preprocessed_input):
                # Simple threshold: bright pixels become building
                return preprocessed_input.mean(axis=2)
            
            def postprocess(self, raw_output):
                return ((raw_output > 128) * 255).astype(np.uint8)
        
        return SimpleModel()
    
    def test_segment_with_small_image(self, simple_model):
        """segment() should handle very small images (1x1 pixel)."""
        image = np.array([[[100, 150, 200]]], dtype=np.uint8)
        mask = simple_model.segment(image)
        
        assert mask.shape == (1, 1)
        assert mask.dtype == np.uint8
        assert mask[0, 0] in [0, 255]
    
    def test_segment_with_all_black_image(self, simple_model):
        """segment() should handle all-black images."""
        image = np.zeros((100, 100, 3), dtype=np.uint8)
        mask = simple_model.segment(image)
        
        assert mask.shape == (100, 100)
        assert mask.dtype == np.uint8
        # All black should result in all background (0)
        assert np.all(mask == 0)
    
    def test_segment_with_all_white_image(self, simple_model):
        """segment() should handle all-white images."""
        image = np.full((100, 100, 3), 255, dtype=np.uint8)
        mask = simple_model.segment(image)
        
        assert mask.shape == (100, 100)
        assert mask.dtype == np.uint8
        # All white should result in all building (255)
        assert np.all(mask == 255)
