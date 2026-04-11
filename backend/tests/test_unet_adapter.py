"""
Unit tests for UNetAdapter.

Tests verify that:
1. UNetAdapter correctly implements the SegmentationModel interface
2. Preprocessing resizes and normalizes images correctly
3. Postprocessing applies sigmoid, thresholds, and resizes back correctly
4. Error handling works correctly for edge cases
"""

import pytest
import numpy as np
import sys
from unittest.mock import Mock, patch, MagicMock

# Mock torch and PIL modules before importing UNetAdapter
mock_torch = Mock()
mock_nn = Mock()
mock_torch.nn = mock_nn
mock_torch.cuda.is_available.return_value = False
sys.modules['torch'] = mock_torch
sys.modules['torch.nn'] = mock_nn

from backend.models.unet_adapter import UNetAdapter


class TestUNetAdapterInitialization:
    """Test UNetAdapter initialization and loading."""
    
    def test_initialization_pytorch(self):
        """UNetAdapter should initialize with model path and framework."""
        adapter = UNetAdapter(
            model_path="/path/to/unet.pth",
            framework="pytorch"
        )
        
        assert adapter.model_path == "/path/to/unet.pth"
        assert adapter.framework == "pytorch"
        assert adapter.model is None  # Not loaded yet
        assert adapter.input_size == (256, 256)
        assert adapter.device in ['cuda', 'cpu']
    
    def test_initialization_default_framework(self):
        """UNetAdapter should default to pytorch framework."""
        adapter = UNetAdapter(model_path="/path/to/unet.pth")
        
        assert adapter.framework == "pytorch"
    
    @patch('backend.models.unet_adapter.torch')
    def test_load_success(self, mock_torch_module):
        """load() should successfully load PyTorch U-Net model."""
        # Setup mock
        mock_model = Mock()
        mock_model.eval.return_value = mock_model
        mock_model.to.return_value = mock_model
        mock_torch_module.load.return_value = mock_model
        mock_torch_module.cuda.is_available.return_value = False
        
        adapter = UNetAdapter(model_path="/path/to/unet.pth")
        adapter.load()
        
        # Verify torch.load was called
        mock_torch_module.load.assert_called_once()
        
        # Verify model is in eval mode and on correct device
        mock_model.eval.assert_called_once()
        mock_model.to.assert_called_once()
        
        # Verify model is set
        assert adapter.model == mock_model
    
    @patch('backend.models.unet_adapter.torch')
    def test_load_state_dict_error(self, mock_torch_module):
        """load() should raise error if state dict is loaded instead of model."""
        # Setup mock to return a dict (state dict)
        mock_torch_module.load.return_value = {'layer1.weight': Mock()}
        mock_torch_module.cuda.is_available.return_value = False
        
        adapter = UNetAdapter(model_path="/path/to/state_dict.pth")
        
        with pytest.raises(Exception, match="Failed to load U-Net model"):
            adapter.load()
    
    def test_load_unsupported_framework(self):
        """load() should raise error for unsupported frameworks."""
        adapter = UNetAdapter(
            model_path="/path/to/unet.h5",
            framework="tensorflow"
        )
        
        with pytest.raises(NotImplementedError, match="Framework 'tensorflow' not yet supported"):
            adapter.load()
    
    @patch('backend.models.unet_adapter.torch')
    def test_load_failure(self, mock_torch_module):
        """load() should raise exception if model loading fails."""
        mock_torch_module.load.side_effect = FileNotFoundError("Model file not found")
        mock_torch_module.cuda.is_available.return_value = False
        
        adapter = UNetAdapter(model_path="/invalid/path.pth")
        
        with pytest.raises(Exception, match="Failed to load U-Net model"):
            adapter.load()


class TestUNetAdapterPreprocessing:
    """Test UNetAdapter preprocessing."""
    
    @patch('PIL.Image.fromarray')
    def test_preprocess_valid_rgb_image(self, mock_fromarray):
        """preprocess() should resize, normalize, and convert to tensor."""
        adapter = UNetAdapter(model_path="/path/to/unet.pth")
        
        # Create test image
        image = np.random.randint(0, 256, (512, 512, 3), dtype=np.uint8)
        
        # Mock PIL operations
        mock_pil_image = Mock()
        mock_resized = Mock()
        resized_array = np.random.randint(0, 256, (256, 256, 3), dtype=np.uint8)
        
        mock_fromarray.return_value = mock_pil_image
        mock_pil_image.resize.return_value = mock_resized
        
        with patch('numpy.array', return_value=resized_array):
            with patch('backend.models.unet_adapter.torch') as mock_torch:
                # Setup torch mocks
                mock_tensor = Mock()
                mock_tensor.permute.return_value = mock_tensor
                mock_tensor.unsqueeze.return_value = mock_tensor
                mock_tensor.to.return_value = mock_tensor
                mock_torch.from_numpy.return_value = mock_tensor
                
                preprocessed = adapter.preprocess(image)
                
                # Verify PIL resize was called with correct dimensions
                # Note: Second argument is PIL.Image.BILINEAR constant
                assert mock_pil_image.resize.call_count == 1
                call_args = mock_pil_image.resize.call_args[0]
                assert call_args[0] == (256, 256)
                
                # Verify tensor operations
                mock_torch.from_numpy.assert_called_once()
                mock_tensor.permute.assert_called_once_with(2, 0, 1)
                mock_tensor.unsqueeze.assert_called_once_with(0)
                
                # Verify original size was stored
                assert adapter.original_size == (512, 512)
    
    def test_preprocess_rejects_wrong_channels(self):
        """preprocess() should reject images without 3 channels."""
        adapter = UNetAdapter(model_path="/path/to/unet.pth")
        
        # Test with 4 channels (RGBA)
        image_rgba = np.random.randint(0, 256, (100, 100, 4), dtype=np.uint8)
        with pytest.raises(ValueError, match="Expected 3-channel RGB image"):
            adapter.preprocess(image_rgba)
        
        # Test with 1 channel (grayscale)
        image_gray = np.random.randint(0, 256, (100, 100, 1), dtype=np.uint8)
        with pytest.raises(ValueError, match="Expected 3-channel RGB image"):
            adapter.preprocess(image_gray)
    
    @patch('PIL.Image.fromarray')
    def test_preprocess_normalization(self, mock_fromarray):
        """preprocess() should normalize pixel values to [0, 1]."""
        adapter = UNetAdapter(model_path="/path/to/unet.pth")
        
        # Create test image with known values
        image = np.array([[[0, 127, 255]]], dtype=np.uint8)  # 1x1x3 image
        
        # Mock PIL operations
        mock_pil_image = Mock()
        mock_resized = Mock()
        resized_array = np.array([[[0, 127, 255]]], dtype=np.uint8)
        
        mock_fromarray.return_value = mock_pil_image
        mock_pil_image.resize.return_value = mock_resized
        
        with patch('numpy.array', return_value=resized_array):
            with patch('backend.models.unet_adapter.torch') as mock_torch:
                # Capture the normalized array passed to from_numpy
                captured_array = None
                
                def capture_from_numpy(arr):
                    nonlocal captured_array
                    captured_array = arr
                    mock_tensor = Mock()
                    mock_tensor.permute.return_value = mock_tensor
                    mock_tensor.unsqueeze.return_value = mock_tensor
                    mock_tensor.to.return_value = mock_tensor
                    return mock_tensor
                
                mock_torch.from_numpy.side_effect = capture_from_numpy
                
                adapter.preprocess(image)
                
                # Verify normalization
                assert captured_array is not None
                assert captured_array.dtype == np.float32
                # Check that values are normalized (0 -> 0.0, 255 -> 1.0)
                assert np.allclose(captured_array[0, 0, 0], 0.0)
                assert np.allclose(captured_array[0, 0, 2], 1.0)
    
    @patch('PIL.Image.fromarray')
    def test_preprocess_various_sizes(self, mock_fromarray):
        """preprocess() should handle various input image sizes."""
        adapter = UNetAdapter(model_path="/path/to/unet.pth")
        
        test_sizes = [(64, 64, 3), (128, 256, 3), (512, 512, 3), (1024, 768, 3)]
        
        for size in test_sizes:
            image = np.random.randint(0, 256, size, dtype=np.uint8)
            
            # Mock PIL operations
            mock_pil_image = Mock()
            mock_resized = Mock()
            resized_array = np.random.randint(0, 256, (256, 256, 3), dtype=np.uint8)
            
            mock_fromarray.return_value = mock_pil_image
            mock_pil_image.resize.return_value = mock_resized
            
            with patch('numpy.array', return_value=resized_array):
                with patch('backend.models.unet_adapter.torch') as mock_torch:
                    mock_tensor = Mock()
                    mock_tensor.permute.return_value = mock_tensor
                    mock_tensor.unsqueeze.return_value = mock_tensor
                    mock_tensor.to.return_value = mock_tensor
                    mock_torch.from_numpy.return_value = mock_tensor
                    
                    adapter.preprocess(image)
                    
                    # Verify original size was stored correctly
                    assert adapter.original_size == (size[0], size[1])


class TestUNetAdapterPrediction:
    """Test UNetAdapter prediction."""
    
    @patch('backend.models.unet_adapter.torch')
    def test_predict_success(self, mock_torch_module):
        """predict() should run forward pass and return output."""
        # Setup mocks
        mock_model = Mock()
        mock_output = Mock()
        mock_model.return_value = mock_output
        mock_model.eval.return_value = mock_model
        mock_model.to.return_value = mock_model
        
        mock_torch_module.load.return_value = mock_model
        mock_torch_module.cuda.is_available.return_value = False
        mock_torch_module.no_grad.return_value.__enter__ = Mock()
        mock_torch_module.no_grad.return_value.__exit__ = Mock()
        
        adapter = UNetAdapter(model_path="/path/to/unet.pth")
        adapter.load()
        
        # Create mock input tensor
        mock_input = Mock()
        
        output = adapter.predict(mock_input)
        
        # Verify model was called
        mock_model.assert_called_with(mock_input)
        
        # Verify output is returned
        assert output == mock_output
    
    def test_predict_without_loading(self):
        """predict() should raise exception if model not loaded."""
        adapter = UNetAdapter(model_path="/path/to/unet.pth")
        
        mock_input = Mock()
        
        with pytest.raises(Exception, match="Model not loaded"):
            adapter.predict(mock_input)
    
    @patch('backend.models.unet_adapter.torch')
    def test_predict_failure(self, mock_torch_module):
        """predict() should raise exception if prediction fails."""
        # Setup mocks
        mock_model = Mock()
        mock_model.side_effect = RuntimeError("CUDA out of memory")
        mock_model.eval.return_value = mock_model
        mock_model.to.return_value = mock_model
        
        mock_torch_module.load.return_value = mock_model
        mock_torch_module.cuda.is_available.return_value = False
        
        adapter = UNetAdapter(model_path="/path/to/unet.pth")
        adapter.load()
        
        mock_input = Mock()
        
        with pytest.raises(Exception, match="U-Net prediction failed"):
            adapter.predict(mock_input)


class TestUNetAdapterPostprocessing:
    """Test UNetAdapter postprocessing."""
    
    @patch('PIL.Image.fromarray')
    @patch('backend.models.unet_adapter.torch')
    def test_postprocess_applies_sigmoid_and_threshold(self, mock_torch_module, mock_fromarray):
        """postprocess() should apply sigmoid and threshold at 0.5."""
        adapter = UNetAdapter(model_path="/path/to/unet.pth")
        adapter.original_size = (100, 100)
        
        # Create mock output tensor with logits
        mock_output = Mock()
        mock_probabilities = Mock()
        mock_binary = Mock()
        mock_squeezed = Mock()
        
        # Setup sigmoid chain
        mock_torch_module.sigmoid.return_value = mock_probabilities
        
        # Setup threshold chain
        mock_probabilities.__gt__ = Mock(return_value=mock_binary)
        mock_binary.float.return_value = mock_binary
        
        # Setup squeeze chain
        mock_binary.squeeze.return_value = mock_squeezed
        mock_squeezed.squeeze.return_value = mock_squeezed
        
        # Setup cpu/numpy chain
        mock_cpu = Mock()
        mock_squeezed.cpu.return_value = mock_cpu
        mask_array = np.ones((256, 256), dtype=np.float32)
        mock_cpu.numpy.return_value = mask_array
        
        # Mock PIL resize
        mock_pil = Mock()
        mock_resized = Mock()
        final_array = np.ones((100, 100), dtype=np.uint8) * 255
        
        mock_fromarray.return_value = mock_pil
        mock_pil.resize.return_value = mock_resized
        
        with patch('numpy.array', return_value=final_array):
            result = adapter.postprocess(mock_output)
        
        # Verify sigmoid was applied
        mock_torch_module.sigmoid.assert_called_once_with(mock_output)
        
        # Verify threshold was applied
        mock_probabilities.__gt__.assert_called_once_with(0.5)
        
        # Verify result
        assert result.shape == (100, 100)
        assert result.dtype == np.uint8
    
    @patch('PIL.Image.fromarray')
    @patch('backend.models.unet_adapter.torch')
    def test_postprocess_resizes_to_original(self, mock_torch_module, mock_fromarray):
        """postprocess() should resize mask back to original dimensions."""
        adapter = UNetAdapter(model_path="/path/to/unet.pth")
        adapter.original_size = (512, 768)  # Different from input_size
        
        # Create mock output
        mock_output = Mock()
        mock_probabilities = Mock()
        mock_binary = Mock()
        mock_squeezed = Mock()
        
        mock_torch_module.sigmoid.return_value = mock_probabilities
        mock_probabilities.__gt__ = Mock(return_value=mock_binary)
        mock_binary.float.return_value = mock_binary
        mock_binary.squeeze.return_value = mock_squeezed
        mock_squeezed.squeeze.return_value = mock_squeezed
        
        mock_cpu = Mock()
        mock_squeezed.cpu.return_value = mock_cpu
        mask_array = np.ones((256, 256), dtype=np.float32)
        mock_cpu.numpy.return_value = mask_array
        
        # Mock PIL resize
        mock_pil = Mock()
        mock_resized = Mock()
        final_array = np.ones((512, 768), dtype=np.uint8) * 255
        
        mock_fromarray.return_value = mock_pil
        mock_pil.resize.return_value = mock_resized
        
        with patch('numpy.array', return_value=final_array):
            result = adapter.postprocess(mock_output)
        
        # Verify resize was called with correct dimensions (width, height)
        # Note: Second argument is PIL.Image.NEAREST constant
        assert mock_pil.resize.call_count == 1
        call_args = mock_pil.resize.call_args[0]
        assert call_args[0] == (768, 512)
        
        # Verify result has original dimensions
        assert result.shape == (512, 768)
    
    @patch('PIL.Image.fromarray')
    @patch('backend.models.unet_adapter.torch')
    def test_postprocess_binary_output(self, mock_torch_module, mock_fromarray):
        """postprocess() should produce binary mask with values {0, 255}."""
        adapter = UNetAdapter(model_path="/path/to/unet.pth")
        adapter.original_size = (100, 100)
        
        # Create mock output
        mock_output = Mock()
        mock_probabilities = Mock()
        mock_binary = Mock()
        mock_squeezed = Mock()
        
        mock_torch_module.sigmoid.return_value = mock_probabilities
        mock_probabilities.__gt__ = Mock(return_value=mock_binary)
        mock_binary.float.return_value = mock_binary
        mock_binary.squeeze.return_value = mock_squeezed
        mock_squeezed.squeeze.return_value = mock_squeezed
        
        mock_cpu = Mock()
        mock_squeezed.cpu.return_value = mock_cpu
        
        # Create binary mask (0 and 1)
        mask_array = np.zeros((256, 256), dtype=np.float32)
        mask_array[50:150, 50:150] = 1.0
        mock_cpu.numpy.return_value = mask_array
        
        # Mock PIL resize
        mock_pil = Mock()
        mock_resized = Mock()
        
        # Create final binary array (0 and 255)
        final_array = np.zeros((100, 100), dtype=np.uint8)
        final_array[20:80, 20:80] = 255
        
        mock_fromarray.return_value = mock_pil
        mock_pil.resize.return_value = mock_resized
        
        with patch('numpy.array', return_value=final_array):
            result = adapter.postprocess(mock_output)
        
        # Verify binary output
        assert result.dtype == np.uint8
        assert set(np.unique(result)).issubset({0, 255})


class TestUNetAdapterIntegration:
    """Test complete UNetAdapter pipeline."""
    
    @patch('backend.models.unet_adapter.torch')
    @patch('PIL.Image.fromarray')
    def test_complete_segment_pipeline(self, mock_fromarray, mock_torch_module):
        """Test complete segment() pipeline from image to binary mask."""
        # Setup model mock
        mock_model = Mock()
        mock_model.eval.return_value = mock_model
        mock_model.to.return_value = mock_model
        
        # Setup model output
        mock_output = Mock()
        mock_model.return_value = mock_output
        
        mock_torch_module.load.return_value = mock_model
        mock_torch_module.cuda.is_available.return_value = False
        mock_torch_module.no_grad.return_value.__enter__ = Mock()
        mock_torch_module.no_grad.return_value.__exit__ = Mock()
        
        # Setup preprocessing mocks
        mock_pil_image = Mock()
        mock_resized_input = Mock()
        resized_input_array = np.random.randint(0, 256, (256, 256, 3), dtype=np.uint8)
        
        # Setup preprocessing tensor
        mock_input_tensor = Mock()
        mock_input_tensor.permute.return_value = mock_input_tensor
        mock_input_tensor.unsqueeze.return_value = mock_input_tensor
        mock_input_tensor.to.return_value = mock_input_tensor
        mock_torch_module.from_numpy.return_value = mock_input_tensor
        
        # Setup postprocessing mocks
        mock_probabilities = Mock()
        mock_binary = Mock()
        mock_squeezed = Mock()
        
        mock_torch_module.sigmoid.return_value = mock_probabilities
        mock_probabilities.__gt__ = Mock(return_value=mock_binary)
        mock_binary.float.return_value = mock_binary
        mock_binary.squeeze.return_value = mock_squeezed
        mock_squeezed.squeeze.return_value = mock_squeezed
        
        mock_cpu = Mock()
        mock_squeezed.cpu.return_value = mock_cpu
        mask_array = np.ones((256, 256), dtype=np.float32)
        mock_cpu.numpy.return_value = mask_array
        
        # Setup PIL for both preprocessing and postprocessing
        def fromarray_side_effect(arr):
            if arr.dtype == np.uint8 and len(arr.shape) == 3:
                # Preprocessing
                mock_pil_image.resize.return_value = mock_resized_input
                return mock_pil_image
            else:
                # Postprocessing
                mock_pil_output = Mock()
                mock_resized_output = Mock()
                mock_pil_output.resize.return_value = mock_resized_output
                return mock_pil_output
        
        mock_fromarray.side_effect = fromarray_side_effect
        
        # Setup numpy.array for both preprocessing and postprocessing
        call_count = [0]
        def array_side_effect(obj, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                # Preprocessing
                return resized_input_array
            else:
                # Postprocessing
                final_array = np.ones((256, 256), dtype=np.uint8) * 255
                return final_array
        
        # Create adapter and load
        adapter = UNetAdapter(model_path="/path/to/unet.pth")
        adapter.load()
        
        # Create test image
        image = np.random.randint(0, 256, (256, 256, 3), dtype=np.uint8)
        
        # Run complete pipeline
        with patch('numpy.array', side_effect=array_side_effect):
            result = adapter.segment(image)
        
        # Verify output
        assert result.shape == (256, 256)
        assert result.dtype == np.uint8
        assert set(np.unique(result)).issubset({0, 255})
