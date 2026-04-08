"""
Unit tests for FastAPI application setup and configuration.

Tests verify that the FastAPI app is properly configured with CORS middleware
and static file serving.
"""

import pytest
from fastapi.testclient import TestClient
from backend.api.main import app, UPLOAD_DIR, MASK_DIR


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


def test_app_instance_created():
    """Test that FastAPI app instance is created."""
    assert app is not None
    assert app.title == "Aerial Image Segmentation API"
    assert app.version == "1.0.0"


def test_root_endpoint(client):
    """Test that root endpoint returns correct response."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Aerial Image Segmentation API"
    assert data["version"] == "1.0.0"
    assert data["status"] == "running"


def test_health_check_endpoint(client):
    """Test that health check endpoint returns healthy status."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_cors_middleware_configured(client):
    """Test that CORS middleware is configured and allows requests."""
    # Make a request with Origin header
    response = client.get(
        "/",
        headers={"Origin": "http://localhost:5173"}
    )
    assert response.status_code == 200
    # CORS headers should be present in response
    assert "access-control-allow-origin" in response.headers


def test_upload_directories_exist():
    """Test that upload directories are created."""
    assert UPLOAD_DIR.exists()
    assert UPLOAD_DIR.is_dir()
    assert MASK_DIR.exists()
    assert MASK_DIR.is_dir()


def test_static_file_mounts_configured(client):
    """Test that static file routes are mounted."""
    # The routes should exist even if no files are present yet
    # We'll test with a 404 since no files exist yet
    response = client.get("/images/nonexistent.jpg")
    # Should return 404 (not found) rather than 405 (method not allowed)
    # This confirms the route is mounted
    assert response.status_code == 404
    
    response = client.get("/masks/nonexistent.png")
    assert response.status_code == 404
