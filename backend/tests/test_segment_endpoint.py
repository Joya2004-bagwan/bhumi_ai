"""
Unit tests for POST /segment endpoint.

Tests verify that the segment endpoint correctly validates inputs,
runs segmentation, saves masks, and returns proper responses.
"""

import pytest
import io
from pathlib import Path
from fastapi.testclient import TestClient
from PIL import Image
import numpy as np
from backend.api.main import app, UPLOAD_DIR, MASK_DIR


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def valid_test_image():
    """Create a valid test image file in memory."""
    img = Image.new('RGB', (100, 100), color='red')
    buffer = io.BytesIO()
    img.save(buffer, format='JPEG')
    buffer.seek(0)
    return buffer


@pytest.fixture
def uploaded_image_id(client, valid_test_image):
    """Upload an image and return its ID."""
    response = client.post(
        "/upload",
        files={"file": ("test_image.jpg", valid_test_image, "image/jpeg")}
    )
    assert response.status_code == 200
    return response.json()["image_id"]


@pytest.fixture(autouse=True)
def cleanup_files():
    """Clean up uploaded files and masks after each test."""
    yield
    for file in UPLOAD_DIR.glob("*"):
        if file.is_file():
            file.unlink()
    for file in MASK_DIR.glob("*"):
        if file.is_file():
            file.unlink()


def test_segment_with_valid_inputs(client, uploaded_image_id, mock_segmentation):
    """Test segmentation with valid image_id and model."""
    response = client.post(
        "/segment",
        json={
            "image_id": uploaded_image_id,
            "model": "yolov8m-custom"
        }
    )

    assert response.status_code == 200
    data = response.json()

    assert "mask_url" in data
    assert "mask_base64" in data
    assert "processing_time" in data
    assert "model_used" in data

    assert data["mask_url"].startswith("/masks/")
    assert data["mask_url"].endswith("-mask.png")
    assert uploaded_image_id in data["mask_url"]
    assert "yolov8m-custom" in data["mask_url"]
    assert len(data["mask_base64"]) > 0
    assert data["processing_time"] > 0
    assert data["model_used"] == "yolov8m-custom"

    mask_filename = data["mask_url"].split("/")[-1]
    mask_file = MASK_DIR / mask_filename
    assert mask_file.exists()


def test_segment_with_maskrcnn_model(client, uploaded_image_id, mock_segmentation):
    """Test segmentation with Mask R-CNN model."""
    response = client.post(
        "/segment",
        json={
            "image_id": uploaded_image_id,
            "model": "maskrcnn-custom"
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["model_used"] == "maskrcnn-custom"
    assert "maskrcnn-custom" in data["mask_url"]


def test_segment_with_invalid_model(client, uploaded_image_id):
    """Test segmentation with unsupported model name."""
    response = client.post(
        "/segment",
        json={
            "image_id": uploaded_image_id,
            "model": "invalid_model"
        }
    )

    assert response.status_code == 400
    data = response.json()
    assert "Invalid model name" in data["detail"]
    assert "yolov8m-custom" in data["detail"]
    assert "maskrcnn-custom" in data["detail"]


def test_segment_with_missing_image(client):
    """Test segmentation with non-existent image_id."""
    response = client.post(
        "/segment",
        json={
            "image_id": "non-existent-uuid",
            "model": "yolov8m-custom"
        }
    )

    assert response.status_code == 404
    data = response.json()
    assert "Image not found" in data["detail"]


def test_segment_without_image_id(client):
    """Test segmentation without providing image_id."""
    response = client.post(
        "/segment",
        json={
            "model": "yolov8m-custom"
        }
    )
    assert response.status_code == 422


def test_segment_without_model(client, uploaded_image_id):
    """Test segmentation without providing model name."""
    response = client.post(
        "/segment",
        json={
            "image_id": uploaded_image_id
        }
    )
    assert response.status_code == 422


def test_segment_multiple_times_same_image(client, uploaded_image_id, mock_segmentation):
    """Test running segmentation multiple times on the same image."""
    response1 = client.post(
        "/segment",
        json={"image_id": uploaded_image_id, "model": "yolov8m-custom"}
    )
    assert response1.status_code == 200

    response2 = client.post(
        "/segment",
        json={"image_id": uploaded_image_id, "model": "maskrcnn-custom"}
    )
    assert response2.status_code == 200

    assert response1.json()["mask_url"] != response2.json()["mask_url"]


def test_segment_returns_base64_encoded_mask(client, uploaded_image_id, mock_segmentation):
    """Test that the returned base64 mask can be decoded."""
    import base64

    response = client.post(
        "/segment",
        json={"image_id": uploaded_image_id, "model": "yolov8m-custom"}
    )

    assert response.status_code == 200
    data = response.json()

    try:
        decoded = base64.b64decode(data["mask_base64"])
        mask_image = Image.open(io.BytesIO(decoded))
        assert mask_image.mode == 'L'
    except Exception as e:
        pytest.fail(f"Failed to decode base64 mask: {e}")


def test_segment_processing_time_is_reasonable(client, uploaded_image_id, mock_segmentation):
    """Test that processing time is recorded and reasonable."""
    response = client.post(
        "/segment",
        json={"image_id": uploaded_image_id, "model": "yolov8m-custom"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["processing_time"] > 0
    assert data["processing_time"] < 300


def test_segment_with_different_image_formats(client, mock_segmentation):
    """Test segmentation works with different image formats (JPG, PNG, TIFF)."""
    formats = [
        ("test.jpg", "JPEG", "image/jpeg"),
        ("test.png", "PNG", "image/png"),
        ("test.tiff", "TIFF", "image/tiff")
    ]

    for filename, format_name, mime_type in formats:
        img = Image.new('RGB', (100, 100), color='blue')
        buffer = io.BytesIO()
        img.save(buffer, format=format_name)
        buffer.seek(0)

        upload_response = client.post(
            "/upload",
            files={"file": (filename, buffer, mime_type)}
        )
        assert upload_response.status_code == 200
        image_id = upload_response.json()["image_id"]

        segment_response = client.post(
            "/segment",
            json={"image_id": image_id, "model": "yolov8m-custom"}
        )
        assert segment_response.status_code == 200
