"""GeoJSON export utilities for segmentation results."""

import json
from typing import List, Dict, Any, Optional
import numpy as np
import cv2

try:
    from shapely.geometry import Polygon, mapping
    from shapely.validation import make_valid
    SHAPELY_AVAILABLE = True
except ImportError:
    SHAPELY_AVAILABLE = False

from .worldfile import WorldFile


class GeoJSONExporter:
    """Converts segmentation masks to GeoJSON with world coordinates."""

    def __init__(self, world_file: Optional[WorldFile] = None):
        self.world_file = world_file

    def _transform_coords(self, pixel_coords: List) -> List:
        """Transform pixel coords to world coords if world file is set."""
        if not self.world_file:
            return pixel_coords
        return [list(self.world_file.pixel_to_world(x, y)) for x, y in pixel_coords]

    def _make_feature(self, idx: int, coords: List, area: float) -> Dict:
        """Build a GeoJSON Feature from a list of coordinate pairs."""
        closed = coords + [coords[0]]  # close the ring

        feature = {
            "type": "Feature",
            "properties": {"id": idx + 1, "area_pixels": float(area)},
            "geometry": {"type": "Polygon", "coordinates": [closed]}
        }

        if SHAPELY_AVAILABLE:
            try:
                poly = Polygon(closed)
                if not poly.is_valid:
                    poly = make_valid(poly)
                if poly.is_valid and not poly.is_empty:
                    feature["geometry"] = mapping(poly)
            except Exception:
                pass

        return feature

    def mask_to_geojson(
        self,
        mask: np.ndarray,
        min_area: float = 100.0,
        simplify_tolerance: float = 1.0
    ) -> Dict[str, Any]:
        """
        Convert binary mask to GeoJSON using minAreaRect per building instance.
        Each connected component gets a tight rotated-rectangle polygon,
        matching the style used by the Detect Buildings view.
        """
        features = []

        # Label connected components (each = one building instance)
        num_labels, labels = cv2.connectedComponents(mask)

        for label_id in range(1, num_labels):  # skip background (0)
            instance_mask = np.uint8(labels == label_id) * 255
            area = float(np.sum(instance_mask > 0))

            if area < min_area:
                continue

            contours, _ = cv2.findContours(
                instance_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )
            if not contours:
                continue

            largest = max(contours, key=cv2.contourArea)

            # Fit rotated rectangle — same as Detect Buildings
            rect = cv2.minAreaRect(largest)
            box = cv2.boxPoints(rect)
            box = np.intp(box)
            h, w = mask.shape[:2]
            pixel_coords = [
                [max(0, min(w - 1, int(p[0]))), max(0, min(h - 1, int(p[1])))]
                for p in box
            ]

            world_coords = self._transform_coords(pixel_coords)
            features.append(self._make_feature(len(features), world_coords, area))

        return {"type": "FeatureCollection", "features": features}

    def to_string(self, geojson: Dict[str, Any], indent: int = 2) -> str:
        return json.dumps(geojson, indent=indent)
