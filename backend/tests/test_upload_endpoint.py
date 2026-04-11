"""
Unit tests for POST /upload endpoint.

Tests verify that the upload endpoint correctly handles file uploads,
validates file formats, generates unique IDs, and returns proper metadata.
"""

import pytest
import io
from pathlib import Path
from fastapi.testclient import TestClient
from PIL import Image
import numpy as np
from backend.api.main import app, UPLOAD_DIR


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def valid_jpg_file():
    """Create a valid JPG image file in memory."""
    # Create a simple RGB image
    img = Image.new('RGB', (100, 100), color='red')
    buffer = io.BytesIO()
    img.save(buffer, format='JPEG')
    buffer.seek(0)
    return buffer


@pytest.fixture
def valid_png_file():
    """Create a valid PNG image file in memory."""
    img = Image.new('RGB', (200, 150), color='blue')
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return buffer


@pytest.fixture
def valid_tiff_file():
    """Create a valid TIFF image file in memory."""
    img = Image.new('RGB', (300, 200), color='green')
    buffer = io.BytesIO()
    img.save(buffer, format='TIFF')
    buffer.seek(0)
    return buffer


@pytest.fixture
def corrupted_file():
    """Create a corrupted file that claims to be an image."""
    buffer = io.BytesIO(b"This is not a valid image file")
    return buffer


@pytest.fixture(autouse=True)
def cleanup_uploads():
    """Clean up uploaded files after each test."""
    yield
    # Remove all test files from upload directory
    for file in UPLOAD_DIR.glob("*"):
        if file.is_file():
            file.unlink()


def test_upload_valid_jpg(client, valid_jpg_file):
    """Test uploading a valid JPG image."""
    response = client.post(
        "/upload",
        files={"file": ("test_image.jpg", valid_jpg_file, "image/jpeg")}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Check response structure
    assert "image_id" in data
    assert "image_url" in data
    assert "width" in data
    assert "height" in data
    
    # Check values
    assert len(data["image_id"]) == 36  # UUID format
    assert data["image_url"].startswith("/images/")
    assert data["image_url"].endswith(".jpg")
    assert data["width"] == 100
    assert data["height"] == 100
    
    # Verify file was saved
    image_id = data["image_id"]
    saved_file = UPLOAD_DIR / f"{image_id}.jpg"
    assert saved_file.exists()


def test_upload_valid_png(client, valid_png_file):
    """Test uploading a valid PNG image."""
    response = client.post(
        "/upload",
        files={"file": ("test_image.png", valid_png_file, "image/png")}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["width"] == 200
    assert data["height"] == 150
    assert data["image_url"].endswith(".png")


def test_upload_valid_tiff(client, valid_tiff_file):
    """Test uploading a valid TIFF image."""
    response = client.post(
        "/upload",
        files={"file": ("test_image.tiff", valid_tiff_file, "image/tiff")}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["width"] == 300
    assert data["height"] == 200
    assert data["image_url"].endswith(".tiff")


def test_upload_invalid_extension(client):
    """Test uploading a file with unsupported extension."""
    buffer = io.BytesIO(b"fake content")
    
    response = client.post(
        "/upload",
        files={"file": ("test_file.txt", buffer, "text/plain")}
    )
    
    assert response.status_code == 400
    data = response.json()
    assert "Unsupported file format" in data["detail"]


def test_upload_corrupted_file(client, corrupted_file):
    """Test uploading a corrupted file that claims to be an image."""
    response = client.post(
        "/upload",
        files={"file": ("corrupted.jpg", corrupted_file, "image/jpeg")}
    )
    
    assert response.status_code == 400
    data = response.json()
    assert "corrupted" in data["detail"].lower() or "unable to read" in data["detail"].lower()


def test_upload_file_too_large(client):
    """Test uploading a file that exceeds size limit."""
    # Create a large file (> 50MB)
    large_data = b"x" * (51 * 1024 * 1024)  # 51 MB
    buffer = io.BytesIO(large_data)
    
    response = client.post(
        "/upload",
        files={"file": ("large_image.jpg", buffer, "image/jpeg")}
    )
    
    assert response.status_code == 413
    data = response.json()
    assert "too large" in data["detail"].lower()


def test_upload_generates_unique_ids(client, valid_jpg_file):
    """Test that multiple uploads generate unique image IDs."""
    # Upload first image
    response1 = client.post(
        "/upload",
        files={"file": ("test1.jpg", valid_jpg_file, "image/jpeg")}
    )
    assert response1.status_code == 200
    image_id_1 = response1.json()["image_id"]
    
    # Reset buffer and upload second image
    valid_jpg_file.seek(0)
    response2 = client.post(
        "/upload",
        files={"file": ("test2.jpg", valid_jpg_file, "image/jpeg")}
    )
    assert response2.status_code == 200
    image_id_2 = response2.json()["image_id"]
    
    # IDs should be different
    assert image_id_1 != image_id_2


def test_upload_no_file_provided(client):
    """Test upload endpoint when no file is provided."""
    response = client.post("/upload")
    
    # Should return 422 (Unprocessable Entity) for missing required field
    assert response.status_code == 422


def test_upload_preserves_image_quality(client, valid_png_file):
    """Test that uploaded image maintains its quality and dimensions."""
    response = client.post(
        "/upload",
        files={"file": ("test.png", valid_png_file, "image/png")}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Load the saved image and verify dimensions
    image_id = data["image_id"]
    saved_file = UPLOAD_DIR / f"{image_id}.png"
    
    with Image.open(saved_file) as img:
        assert img.size == (200, 150)
        assert img.mode == 'RGB'


def test_upload_handles_rgba_images(client):
    """Test uploading an image with alpha channel (RGBA)."""
    # Create RGBA image
    img = Image.new('RGBA', (100, 100), color=(255, 0, 0, 128))
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    
    response = client.post(
        "/upload",
        files={"file": ("rgba_image.png", buffer, "image/png")}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["width"] == 100
    assert data["height"] == 100


def test_upload_handles_grayscale_images(client):
    """Test uploading a grayscale image."""
    # Create grayscale image
    img = Image.new('L', (150, 150), color=128)
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    
    response = client.post(
        "/upload",
        files={"file": ("gray_image.png", buffer, "image/png")}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["width"] == 150
    assert data["height"] == 150


def test_upload_cleans_up_on_validation_failure(client, corrupted_file):
    """Test that invalid files are cleaned up and not left in storage."""
    response = client.post(
        "/upload",
        files={"file": ("corrupted.jpg", corrupted_file, "image/jpeg")}
    )
    
    assert response.status_code == 400
    
    # Verify no files were left in upload directory
    uploaded_files = list(UPLOAD_DIR.glob("*.jpg"))
    assert len(uploaded_files) == 0
