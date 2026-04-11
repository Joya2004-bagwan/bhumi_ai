"""Unit tests for ImageProcessor class."""

import pytest
import numpy as np
from pathlib import Path
import tempfile
import os
from PIL import Image
from utils.image_processor import ImageProcessor, ValidationResult


@pytest.fixture
def image_processor():
    """Create ImageProcessor instance for testing."""
    return ImageProcessor()


@pytest.fixture
def temp_dir():
    """Create temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def sample_image(temp_dir):
    """Create a sample valid image for testing."""
    img_path = os.path.join(temp_dir, "sample.jpg")
    img = Image.new('RGB', (100, 100), color='red')
    img.save(img_path)
    return img_path


@pytest.fixture
def sample_mask():
    """Create a sample binary mask."""
    mask = np.zeros((100, 100), dtype=np.uint8)
    mask[25:75, 25:75] = 255
    return mask


class TestValidateImage:
    """Tests for validate_image method."""
    
    def test_valid_jpg_image(self, image_processor, sample_image):
        """Test validation of valid JPG image."""
        result = image_processor.validate_image(sample_image)
        assert result.valid is True
        assert result.error is None
    
    def test_valid_png_image(self, image_processor, temp_dir):
        """Test validation of valid PNG image."""
        img_path = os.path.join(temp_dir, "sample.png")
        img = Image.new('RGB', (100, 100), color='blue')
        img.save(img_path)
        
        result = image_processor.validate_image(img_path)
        assert result.valid is True
        assert result.error is None
    
    def test_valid_tiff_image(self, image_processor, temp_dir):
        """Test validation of valid TIFF image."""
        img_path = os.path.join(temp_dir, "sample.tiff")
        img = Image.new('RGB', (100, 100), color='green')
        img.save(img_path)
        
        result = image_processor.validate_image(img_path)
        assert result.valid is True
        assert result.error is None
    
    def test_invalid_format(self, image_processor, temp_dir):
        """Test rejection of unsupported file format."""
        txt_path = os.path.join(temp_dir, "sample.txt")
        with open(txt_path, 'w') as f:
            f.write("Not an image")
        
        result = image_processor.validate_image(txt_path)
        assert result.valid is False
        assert "Unsupported file format" in result.error
    
    def test_nonexistent_file(self, image_processor):
        """Test validation of nonexistent file."""
        result = image_processor.validate_image("/nonexistent/file.jpg")
        assert result.valid is False
        assert "does not exist" in result.error
    
    def test_corrupted_image(self, image_processor, temp_dir):
        """Test detection of corrupted image file."""
        corrupted_path = os.path.join(temp_dir, "corrupted.jpg")
        with open(corrupted_path, 'wb') as f:
            f.write(b"This is not a valid JPEG file")
        
        result = image_processor.validate_image(corrupted_path)
        assert result.valid is False
        assert "corrupted" in result.error.lower()


class TestLoadImage:
    """Tests for load_image method."""
    
    def test_load_rgb_image(self, image_processor, sample_image):
        """Test loading RGB image."""
        img_array = image_processor.load_image(sample_image)
        
        assert isinstance(img_array, np.ndarray)
        assert img_array.shape == (100, 100, 3)
        assert img_array.dtype == np.uint8
    
    def test_load_rgba_image(self, image_processor, temp_dir):
        """Test loading RGBA image converts to RGB."""
        img_path = os.path.join(temp_dir, "rgba.png")
        img = Image.new('RGBA', (50, 50), color=(255, 0, 0, 128))
        img.save(img_path)
        
        img_array = image_processor.load_image(img_path)
        
        assert img_array.shape == (50, 50, 3)
        assert img_array.dtype == np.uint8
    
    def test_load_grayscale_image(self, image_processor, temp_dir):
        """Test loading grayscale image converts to RGB."""
        img_path = os.path.join(temp_dir, "gray.png")
        img = Image.new('L', (50, 50), color=128)
        img.save(img_path)
        
        img_array = image_processor.load_image(img_path)
        
        assert img_array.shape == (50, 50, 3)
        assert img_array.dtype == np.uint8
    
    def test_load_invalid_file(self, image_processor, temp_dir):
        """Test loading invalid file raises ValueError."""
        invalid_path = os.path.join(temp_dir, "invalid.jpg")
        with open(invalid_path, 'w') as f:
            f.write("Not an image")
        
        with pytest.raises(ValueError, match="Failed to load image"):
            image_processor.load_image(invalid_path)
    
    def test_load_various_sizes(self, image_processor, temp_dir):
        """Test loading images of various sizes."""
        sizes = [(1, 1), (10, 10), (100, 200), (500, 300)]
        
        for width, height in sizes:
            img_path = os.path.join(temp_dir, f"img_{width}x{height}.jpg")
            img = Image.new('RGB', (width, height), color='blue')
            img.save(img_path)
            
            img_array = image_processor.load_image(img_path)
            assert img_array.shape == (height, width, 3)


class TestSaveMask:
    """Tests for save_mask method."""
    
    def test_save_valid_mask(self, image_processor, sample_mask, temp_dir):
        """Test saving valid binary mask."""
        output_path = os.path.join(temp_dir, "mask.png")
        
        result_path = image_processor.save_mask(sample_mask, output_path)
        
        assert result_path == output_path
        assert os.path.exists(output_path)
        
        # Verify saved mask
        loaded_mask = np.array(Image.open(output_path))
        np.testing.assert_array_equal(loaded_mask, sample_mask)
    
    def test_save_mask_invalid_values(self, image_processor, temp_dir):
        """Test saving mask with non-binary values raises error."""
        invalid_mask = np.array([[0, 128, 255]], dtype=np.uint8)
        output_path = os.path.join(temp_dir, "mask.png")
        
        with pytest.raises(ValueError, match="Mask must be binary"):
            image_processor.save_mask(invalid_mask, output_path)
    
    def test_save_mask_wrong_dimensions(self, image_processor, temp_dir):
        """Test saving 3D mask raises error."""
        invalid_mask = np.zeros((10, 10, 3), dtype=np.uint8)
        output_path = os.path.join(temp_dir, "mask.png")
        
        with pytest.raises(ValueError, match="Mask must be 2D"):
            image_processor.save_mask(invalid_mask, output_path)


class TestMaskToBase64:
    """Tests for mask_to_base64 method."""
    
    def test_encode_valid_mask(self, image_processor, sample_mask):
        """Test encoding valid binary mask to base64."""
        base64_str = image_processor.mask_to_base64(sample_mask)
        
        assert isinstance(base64_str, str)
        assert len(base64_str) > 0
        
        # Verify it's valid base64
        import base64
        decoded = base64.b64decode(base64_str)
        assert len(decoded) > 0
    
    def test_encode_mask_invalid_values(self, image_processor):
        """Test encoding mask with non-binary values raises error."""
        invalid_mask = np.array([[0, 128, 255]], dtype=np.uint8)
        
        with pytest.raises(ValueError, match="Mask must be binary"):
            image_processor.mask_to_base64(invalid_mask)
    
    def test_encode_mask_wrong_dimensions(self, image_processor):
        """Test encoding 3D mask raises error."""
        invalid_mask = np.zeros((10, 10, 3), dtype=np.uint8)
        
        with pytest.raises(ValueError, match="Mask must be 2D"):
            image_processor.mask_to_base64(invalid_mask)
    
    def test_encode_decode_roundtrip(self, image_processor, sample_mask, temp_dir):
        """Test that encoding and decoding preserves mask data."""
        import base64
        from io import BytesIO
        
        # Encode to base64
        base64_str = image_processor.mask_to_base64(sample_mask)
        
        # Decode and load
        decoded_bytes = base64.b64decode(base64_str)
        decoded_mask = np.array(Image.open(BytesIO(decoded_bytes)))
        
        # Verify masks match
        np.testing.assert_array_equal(decoded_mask, sample_mask)


class TestEdgeCases:
    """Tests for edge cases and special scenarios."""
    
    def test_empty_file(self, image_processor, temp_dir):
        """Test validation of empty file."""
        empty_path = os.path.join(temp_dir, "empty.jpg")
        Path(empty_path).touch()
        
        result = image_processor.validate_image(empty_path)
        assert result.valid is False
    
    def test_tiny_image(self, image_processor, temp_dir):
        """Test loading 1x1 pixel image."""
        tiny_path = os.path.join(temp_dir, "tiny.png")
        img = Image.new('RGB', (1, 1), color='red')
        img.save(tiny_path)
        
        img_array = image_processor.load_image(tiny_path)
        assert img_array.shape == (1, 1, 3)
    
    def test_all_black_mask(self, image_processor):
        """Test encoding all-black mask."""
        black_mask = np.zeros((50, 50), dtype=np.uint8)
        base64_str = image_processor.mask_to_base64(black_mask)
        assert len(base64_str) > 0
    
    def test_all_white_mask(self, image_processor):
        """Test encoding all-white mask."""
        white_mask = np.full((50, 50), 255, dtype=np.uint8)
        base64_str = image_processor.mask_to_base64(white_mask)
        assert len(base64_str) > 0
