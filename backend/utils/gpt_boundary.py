"""
Building boundary detection using minAreaRect (rotated rectangle per instance mask).
"""

import logging
import time
from typing import List, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)

GPT_BOUNDARY_MAX_BUILDINGS = 50


# ---------------------------------------------------------------------------
# Core: fit a rotated rectangle to each building mask
# ---------------------------------------------------------------------------

def process_all_buildings_rect(
    masks: List[np.ndarray],
) -> List[Tuple[int, List, str]]:
    """
    Compute minAreaRect for every building mask.
    Returns list of (idx, polygon_coords, "rect").
    """
    results = []
    for idx, mask in enumerate(masks):
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            results.append((idx, [], "rect"))
            continue
        largest = max(contours, key=cv2.contourArea)
        rect = cv2.minAreaRect(largest)
        box = cv2.boxPoints(rect)
        box = np.intp(box)
        h, w = mask.shape[:2]
        poly = [
            [max(0, min(w - 1, int(p[0]))), max(0, min(h - 1, int(p[1])))]
            for p in box
        ]
        results.append((idx, poly, "rect"))
    return results


# ---------------------------------------------------------------------------
# Overlay rendering
# ---------------------------------------------------------------------------

def render_overlay(
    original_bgr: np.ndarray,
    results: List[Tuple[int, List, str]],
) -> np.ndarray:
    """Draw 1px red rotated rectangles on the original image."""
    out = original_bgr.copy()
    for idx, polygon, source in results:
        if len(polygon) < 3:
            continue
        pts = np.array(polygon, dtype=np.int32).reshape(-1, 1, 2)
        cv2.polylines(out, [pts], True, (0, 0, 255), 1, cv2.LINE_AA)
    return out


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

class GPTBoundaryExtractor:
    """Building boundary extraction using minAreaRect per instance mask."""

    def __init__(self, api_key: str = ""):
        pass  # api_key kept for interface compatibility, not used

    async def process_async(
        self,
        original_bgr: np.ndarray,
        instance_masks: List[np.ndarray],
    ) -> dict:
        # Sort by area descending, cap at max
        areas = [np.sum(m > 0) for m in instance_masks]
        order = sorted(range(len(instance_masks)), key=lambda i: areas[i], reverse=True)
        order = order[:GPT_BOUNDARY_MAX_BUILDINGS]
        capped_masks = [instance_masks[i] for i in order]

        logger.info(f"Processing {len(capped_masks)} buildings with minAreaRect...")
        start = time.time()

        results = process_all_buildings_rect(capped_masks)

        elapsed = time.time() - start
        logger.info(f"minAreaRect done in {elapsed:.3f}s")

        polygons = [r[1] for r in results if r[1]]
        overlay = render_overlay(original_bgr, results)

        return {
            "polygons": polygons,
            "fallback_count": 0,
            "gpt_count": len(polygons),
            "fallback_reasons": {},
            "gpt_overlay_bgr": overlay,
        }
