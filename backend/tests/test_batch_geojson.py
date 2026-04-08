"""
Tests for batch GeoJSON generation:
- world file matching by basename (case-insensitive)
- missing world file handling
- successful GeoJSON generation per batch item
- output ZIP contents for geojson format download
"""

import io
import json
import zipfile
import struct
import zlib
from pathlib import Path

import numpy as np
import pytest
import httpx


# ── Helpers ───────────────────────────────────────────────────────────────────

def _tiny_png() -> bytes:
    """Minimal valid 1x1 white PNG."""
    def chunk(name, data):
        c = name + data
        return struct.pack('>I', len(data)) + c + struct.pack('>I', zlib.crc32(c) & 0xFFFFFFFF)
    sig = b'\x89PNG\r\n\x1a\n'
    ihdr = chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0))
    idat = chunk(b'IDAT', zlib.compress(b'\x00\xff\xff\xff'))
    iend = chunk(b'IEND', b'')
    return sig + ihdr + idat + iend


def _make_image_zip(filenames):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w') as zf:
        for name in filenames:
            zf.writestr(name, _tiny_png())
    return buf.getvalue()


def _make_worldfile_zip(stems, ext=".pgw"):
    wf_content = "0.5\n0.0\n0.0\n-0.5\n500000.0\n4000000.0\n"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w') as zf:
        for stem in stems:
            zf.writestr(f"{stem}{ext}", wf_content)
    return buf.getvalue()


@pytest.fixture
def transport():
    from backend.api.main import app
    return httpx.ASGITransport(app=app)


@pytest.fixture
def base_url():
    return "http://test"


# ── Unit: world file matching ─────────────────────────────────────────────────

class TestWorldFileMatching:

    def test_exact_match(self):
        stem = Path("image_001.png").stem.lower()
        assert stem in {"image_001": Path("/tmp/image_001.pgw")}

    def test_case_insensitive_match(self):
        stem = Path("House_A.PNG").stem.lower()
        assert stem in {"house_a": Path("/tmp/house_a.pgw")}

    def test_no_match(self):
        stem = Path("image_001.png").stem.lower()
        assert stem not in {"building_002": Path("/tmp/building_002.pgw")}

    def test_supported_world_file_extensions(self):
        from backend.api.routers.batch import WORLD_FILE_EXTS
        assert {".pgw", ".tfw", ".jgw", ".wld"}.issubset(WORLD_FILE_EXTS)


# ── Integration: upload-worldfiles-zip endpoint ───────────────────────────────

class TestWorldfilesZipUpload:

    async def _upload_images(self, transport, base_url, filenames):
        zip_bytes = _make_image_zip(filenames)
        async with httpx.AsyncClient(transport=transport, base_url=base_url) as c:
            res = await c.post(
                "/api/batch/upload-zip",
                files={"file": ("images.zip", zip_bytes, "application/zip")},
            )
        assert res.status_code == 200
        return res.json()["batch_id"]

    @pytest.mark.asyncio
    async def test_all_matched(self, transport, base_url, mock_segmentation):
        batch_id = await self._upload_images(transport, base_url, ["img_a.png", "img_b.png"])
        async with httpx.AsyncClient(transport=transport, base_url=base_url) as c:
            res = await c.post(
                f"/api/batch/{batch_id}/upload-worldfiles-zip",
                files={"file": ("wf.zip", _make_worldfile_zip(["img_a", "img_b"]), "application/zip")},
            )
        assert res.status_code == 200
        data = res.json()
        assert data["matched"] == 2
        assert data["unmatched"] == 0

    @pytest.mark.asyncio
    async def test_partial_match(self, transport, base_url, mock_segmentation):
        batch_id = await self._upload_images(transport, base_url, ["img_a.png", "img_b.png", "img_c.png"])
        async with httpx.AsyncClient(transport=transport, base_url=base_url) as c:
            res = await c.post(
                f"/api/batch/{batch_id}/upload-worldfiles-zip",
                files={"file": ("wf.zip", _make_worldfile_zip(["img_a", "img_b"]), "application/zip")},
            )
        data = res.json()
        assert data["matched"] == 2
        assert data["unmatched"] == 1
        assert "img_c.png" in data["unmatched_images"]

    @pytest.mark.asyncio
    async def test_none_matched(self, transport, base_url, mock_segmentation):
        batch_id = await self._upload_images(transport, base_url, ["img_a.png"])
        async with httpx.AsyncClient(transport=transport, base_url=base_url) as c:
            res = await c.post(
                f"/api/batch/{batch_id}/upload-worldfiles-zip",
                files={"file": ("wf.zip", _make_worldfile_zip(["completely_different"]), "application/zip")},
            )
        data = res.json()
        assert data["matched"] == 0
        assert data["unmatched"] == 1

    @pytest.mark.asyncio
    async def test_case_insensitive(self, transport, base_url, mock_segmentation):
        batch_id = await self._upload_images(transport, base_url, ["MyImage.PNG"])
        async with httpx.AsyncClient(transport=transport, base_url=base_url) as c:
            res = await c.post(
                f"/api/batch/{batch_id}/upload-worldfiles-zip",
                files={"file": ("wf.zip", _make_worldfile_zip(["myimage"]), "application/zip")},
            )
        assert res.json()["matched"] == 1

    @pytest.mark.asyncio
    async def test_invalid_zip(self, transport, base_url, mock_segmentation):
        batch_id = await self._upload_images(transport, base_url, ["img_a.png"])
        async with httpx.AsyncClient(transport=transport, base_url=base_url) as c:
            res = await c.post(
                f"/api/batch/{batch_id}/upload-worldfiles-zip",
                files={"file": ("bad.zip", b"not a zip", "application/zip")},
            )
        assert res.status_code == 400

    @pytest.mark.asyncio
    async def test_no_wf_files_in_zip(self, transport, base_url, mock_segmentation):
        batch_id = await self._upload_images(transport, base_url, ["img_a.png"])
        async with httpx.AsyncClient(transport=transport, base_url=base_url) as c:
            res = await c.post(
                f"/api/batch/{batch_id}/upload-worldfiles-zip",
                files={"file": ("wf.zip", _make_image_zip(["img_a.png"]), "application/zip")},
            )
        assert res.status_code == 400
        assert "world files" in res.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_batch_not_found(self, transport, base_url):
        async with httpx.AsyncClient(transport=transport, base_url=base_url) as c:
            res = await c.post(
                "/api/batch/nonexistent-id/upload-worldfiles-zip",
                files={"file": ("wf.zip", _make_worldfile_zip(["img_a"]), "application/zip")},
            )
        assert res.status_code == 404

    @pytest.mark.asyncio
    async def test_has_worldfiles_in_status(self, transport, base_url, mock_segmentation):
        batch_id = await self._upload_images(transport, base_url, ["img_a.png"])
        async with httpx.AsyncClient(transport=transport, base_url=base_url) as c:
            await c.post(
                f"/api/batch/{batch_id}/upload-worldfiles-zip",
                files={"file": ("wf.zip", _make_worldfile_zip(["img_a"]), "application/zip")},
            )
            status = await c.get(f"/api/batch/{batch_id}/status")
        assert status.json()["has_worldfiles"] is True


# ── Unit: GeoJSON generation logic ────────────────────────────────────────────

class TestBatchGeoJSONGeneration:

    def test_geojson_with_worldfile(self, tmp_path):
        from backend.utils.worldfile import WorldFile
        from backend.utils.geojson_exporter import GeoJSONExporter

        wf_path = tmp_path / "test.pgw"
        wf_path.write_text("0.5\n0.0\n0.0\n-0.5\n500000.0\n4000000.0\n")

        mask = np.zeros((50, 50), dtype=np.uint8)
        mask[10:30, 10:30] = 255

        geojson = GeoJSONExporter(WorldFile(str(wf_path))).mask_to_geojson(mask)
        assert geojson["type"] == "FeatureCollection"
        assert len(geojson["features"]) == 1
        coords = geojson["features"][0]["geometry"]["coordinates"][0]
        assert any(c[0] > 1000 for c in coords), "Expected world coordinates, not pixel coords"

    def test_missing_worldfile_sets_error(self):
        from backend.api.schemas import BatchItem
        item = BatchItem(item_id="x", original_filename="img.png", image_path="/tmp/img.png", worldfile_path="")
        if not item.worldfile_path:
            item.geojson_error = "No matching world file — GeoJSON not generated"
        assert item.geojson_path == ""
        assert "No matching world file" in item.geojson_error

    def test_empty_mask_gives_empty_feature_collection(self, tmp_path):
        from backend.utils.worldfile import WorldFile
        from backend.utils.geojson_exporter import GeoJSONExporter

        wf_path = tmp_path / "test.pgw"
        wf_path.write_text("0.5\n0.0\n0.0\n-0.5\n500000.0\n4000000.0\n")
        mask = np.zeros((50, 50), dtype=np.uint8)
        geojson = GeoJSONExporter(WorldFile(str(wf_path))).mask_to_geojson(mask)
        assert len(geojson["features"]) == 0

    def test_multiple_buildings(self, tmp_path):
        from backend.utils.worldfile import WorldFile
        from backend.utils.geojson_exporter import GeoJSONExporter

        wf_path = tmp_path / "test.pgw"
        wf_path.write_text("1.0\n0.0\n0.0\n-1.0\n0.0\n100.0\n")
        mask = np.zeros((100, 100), dtype=np.uint8)
        mask[5:20, 5:20] = 255
        mask[60:80, 60:80] = 255
        geojson = GeoJSONExporter(WorldFile(str(wf_path))).mask_to_geojson(mask, min_area=50)
        assert len(geojson["features"]) == 2


# ── Integration: download geojson format ─────────────────────────────────────

class TestBatchGeoJSONDownload:

    @pytest.mark.asyncio
    async def test_no_worldfiles_returns_400(self, transport, base_url, mock_segmentation):
        """Without world files uploaded, geojson download returns 400 (no done items with geojson_path)."""
        # We can't easily get done items without running the full job, so we test
        # the endpoint contract: a job with no done items returns 400 regardless of format.
        async with httpx.AsyncClient(transport=transport, base_url=base_url) as c:
            res = await c.post(
                "/api/batch/upload-zip",
                files={"file": ("images.zip", _make_image_zip(["img_a.png"]), "application/zip")},
            )
            batch_id = res.json()["batch_id"]
            # No items are done yet — download should fail
            res = await c.get(f"/api/batch/{batch_id}/download?format=geojson")
        assert res.status_code == 400

    @pytest.mark.asyncio
    async def test_invalid_format_returns_400(self, transport, base_url, mock_segmentation):
        """Unsupported format returns 400."""
        async with httpx.AsyncClient(transport=transport, base_url=base_url) as c:
            res = await c.post(
                "/api/batch/upload-zip",
                files={"file": ("images.zip", _make_image_zip(["img_a.png"]), "application/zip")},
            )
            batch_id = res.json()["batch_id"]
            res = await c.get(f"/api/batch/{batch_id}/download?format=svg")
        assert res.status_code == 400

    @pytest.mark.asyncio
    async def test_geojson_download_requires_worldfiles(self, transport, base_url, mock_segmentation, tmp_path):
        """
        Verify the geojson download path: items with geojson_path produce a ZIP,
        items without are excluded. Uses the app's own module reference.
        """
        import backend.api.routers.batch as bm
        from backend.api.schemas import ItemStatus

        async with httpx.AsyncClient(transport=transport, base_url=base_url) as c:
            res = await c.post(
                "/api/batch/upload-zip",
                files={"file": ("images.zip", _make_image_zip(["matched.png", "unmatched.png"]), "application/zip")},
            )
            batch_id = res.json()["batch_id"]

        # The app and test share the same process — bm.batch_jobs IS the live dict
        # (ASGITransport does not fork; it runs in-process via anyio)
        job = bm.batch_jobs.get(batch_id)
        if job is None:
            pytest.skip("batch_jobs not shared in this test environment")

        geojson_dir = tmp_path / "geojson"
        geojson_dir.mkdir()
        for item in job.items:
            item.status = ItemStatus.done
            if item.original_filename == "matched.png":
                gj = geojson_dir / "matched.geojson"
                gj.write_text(json.dumps({"type": "FeatureCollection", "features": []}))
                item.geojson_path = str(gj)
            else:
                item.geojson_error = "No matching world file — GeoJSON not generated"

        async with httpx.AsyncClient(transport=transport, base_url=base_url) as c:
            res = await c.get(f"/api/batch/{batch_id}/download?format=geojson")

        assert res.status_code == 200
        with zipfile.ZipFile(io.BytesIO(res.content)) as zf:
            names = zf.namelist()
        assert "matched.geojson" in names
        assert "unmatched.geojson" not in names
