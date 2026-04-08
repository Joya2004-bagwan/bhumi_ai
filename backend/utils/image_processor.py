"""Image processing utilities for aerial image segmentation."""

import base64
import io
from pathlib import Path
from typing import Tuple, Optional
import numpy as np
from PIL import Image


class ValidationResult:
    """Result of image validation."""
    
    def __init__(self, valid: bool, error: Optional[str] = None):
        self.valid = valid
        self.error = error


class ImageProcessor:
    """Handles image validation, loading, and mask operations."""
    
    SUPPORTED_FORMATS = {'.jpg', '.jpeg', '.png', '.tiff', '.tif'}
    
    def validate_image(self, file_path: str) -> ValidationResult:
        """
        Validate image file format and integrity.
        
        Args:
            file_path: Path to the image file
            
        Returns:
            ValidationResult with valid flag and optional error message
        """
        path = Path(file_path)
        
        # Check if file exists
        if not path.exists():
            return ValidationResult(False, "File does not exist")
        
        # Check file extension
        if path.suffix.lower() not in self.SUPPORTED_FORMATS:
            return ValidationResult(
                False, 
                f"Unsupported file format. Please upload JPG, PNG, or TIFF images."
            )
        
        # Check file integrity by attempting to load
        try:
            with Image.open(file_path) as img:
                img.verify()  # Verify it's a valid image
            
            # Re-open after verify (verify closes the file)
            with Image.open(file_path) as img:
                img.load()  # Actually load the image data
                
            return ValidationResult(True)
            
        except Exception as e:
            return ValidationResult(
                False, 
                f"Unable to read image file. The file may be corrupted: {str(e)}"
            )
    
    def load_image(self, file_path: str) -> np.ndarray:
        """
        Load image as numpy array.
        
        Args:
            file_path: Path to the image file
            
        Returns:
            Image as numpy array in RGB format with shape (height, width, 3)
            
        Raises:
            ValueError: If image cannot be loaded
        """
        try:
            with Image.open(file_path) as img:
                # Convert to RGB (handles RGBA, grayscale, etc.)
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Convert to numpy array
                image_array = np.array(img)
                
                return image_array
                
        except Exception as e:
            raise ValueError(f"Failed to load image: {str(e)}")
    
    def save_mask(self, mask: np.ndarray, output_path: str) -> str:
        """
        Save binary mask as PNG.
        
        Args:
            mask: Binary mask array with values 0 or 255
            output_path: Path where mask should be saved
            
        Returns:
            Path to saved mask file
            
        Raises:
            ValueError: If mask format is invalid
        """
        # Validate mask is binary
        unique_values = np.unique(mask)
        if not np.all(np.isin(unique_values, [0, 255])):
            raise ValueError("Mask must be binary with values 0 or 255")
        
        # Ensure mask is 2D
        if mask.ndim != 2:
            raise ValueError("Mask must be 2D array")
        
        try:
            # Convert to PIL Image and save
            mask_image = Image.fromarray(mask.astype(np.uint8), mode='L')
            mask_image.save(output_path, format='PNG')
            
            return output_path
            
        except Exception as e:
            raise ValueError(f"Failed to save mask: {str(e)}")
    
    def mask_to_base64(self, mask: np.ndarray) -> str:
        """
        Convert mask to base64-encoded PNG.
        
        Args:
            mask: Binary mask array with values 0 or 255
            
        Returns:
            Base64-encoded PNG string
            
        Raises:
            ValueError: If mask format is invalid
        """
        # Validate mask is binary
        unique_values = np.unique(mask)
        if not np.all(np.isin(unique_values, [0, 255])):
            raise ValueError("Mask must be binary with values 0 or 255")
        
        # Ensure mask is 2D
        if mask.ndim != 2:
            raise ValueError("Mask must be 2D array")
        
        try:
            # Convert to PIL Image
            mask_image = Image.fromarray(mask.astype(np.uint8), mode='L')
            
            # Save to bytes buffer
            buffer = io.BytesIO()
            mask_image.save(buffer, format='PNG')
            buffer.seek(0)
            
            # Encode to base64
            base64_encoded = base64.b64encode(buffer.read()).decode('utf-8')
            
            return base64_encoded
            
        except Exception as e:
            raise ValueError(f"Failed to encode mask: {str(e)}")
