"""
Building boundary detection from segmentation masks with GIS-ready output.

This module extracts building boundaries from binary segmentation masks
and converts them to GIS-ready polygon coordinates using comprehensive
preprocessing, contour extraction, and polygon simplification.
"""

import numpy as np
import cv2
from typing import List, Dict, Tuple, Optional

try:
    from shapely.geometry import Polygon
    from shapely.validation import make_valid
    SHAPELY_AVAILABLE = True
except ImportError:
    SHAPELY_AVAILABLE = False
    print("Warning: shapely not installed. Install with: pip install shapely")


class BoundaryDetector:
    """
    Detects building boundaries from segmentation masks with GIS-ready output.
    
    This class implements a comprehensive pipeline:
    1. Mask preprocessing with morphological operations
    2. Contour extraction using RETR_EXTERNAL
    3. Douglas-Peucker polygon simplification
    4. Small object filtering
    5. Optional Shapely polygon conversion and validation
    """
    
    def __init__(
        self,
        min_area: int = 50,
        epsilon_factor: float = 0.01,
        morph_kernel_size: int = 3,
        morph_iterations: int = 2,
        shapely_tolerance: Optional[float] = None
    ):
        """
        Initialize BoundaryDetector with configurable parameters.
        
        Args:
            min_area: Minimum contour area in pixels to consider (filters noise)
            epsilon_factor: Douglas-Peucker approximation accuracy (0.01 = 1% of perimeter)
            morph_kernel_size: Kernel size for morphological operations
            morph_iterations: Number of iterations for morphological operations
            shapely_tolerance: Optional tolerance for Shapely simplification (None = disabled)
        """
        self.min_area = min_area
        self.epsilon_factor = epsilon_factor
        self.morph_kernel_size = morph_kernel_size
        self.morph_iterations = morph_iterations
        self.shapely_tolerance = shapely_tolerance
    
    def preprocess_mask(self, mask: np.ndarray) -> np.ndarray:
        """
        Preprocess binary mask with morphological operations.
        
        Applies closing (fill holes) followed by opening (remove noise).
        
        Args:
            mask: Binary segmentation mask (H, W) with values 0 or 255
        
        Returns:
            Preprocessed binary mask
        """
        # Ensure mask is binary uint8
        if mask.dtype != np.uint8:
            mask = mask.astype(np.uint8)
        
        # Convert to binary (0 and 255)
        binary_mask = np.where(mask > 127, 255, 0).astype(np.uint8)
        
        # Create morphological kernel
        kernel = np.ones(
            (self.morph_kernel_size, self.morph_kernel_size),
            np.uint8
        )
        
        # Morphological closing: fill small holes in buildings
        closed = cv2.morphologyEx(
            binary_mask,
            cv2.MORPH_CLOSE,
            kernel,
            iterations=self.morph_iterations
        )
        
        # Morphological opening: remove small noise
        opened = cv2.morphologyEx(
            closed,
            cv2.MORPH_OPEN,
            kernel,
            iterations=self.morph_iterations
        )
        
        return opened
    
    def extract_contours(self, mask: np.ndarray) -> List[np.ndarray]:
        """
        Extract external contours from binary mask.
        
        Uses RETR_EXTERNAL to get only outer boundaries.
        
        Args:
            mask: Preprocessed binary mask
        
        Returns:
            List of contours (each contour is an array of points)
        """
        contours, _ = cv2.findContours(
            mask,
            cv2.RETR_EXTERNAL,  # Only external contours
            cv2.CHAIN_APPROX_SIMPLE  # Compress horizontal/vertical segments
        )
        
        return contours
    
    def simplify_contour(self, contour: np.ndarray) -> np.ndarray:
        """
        Simplify contour using Douglas-Peucker algorithm.
        
        Args:
            contour: Input contour array
        
        Returns:
            Simplified contour array
        """
        perimeter = cv2.arcLength(contour, True)
        epsilon = self.epsilon_factor * perimeter
        
        # Apply Douglas-Peucker approximation
        approx = cv2.approxPolyDP(contour, epsilon, True)
        
        return approx
    
    def filter_small_objects(self, contours: List[np.ndarray]) -> List[np.ndarray]:
        """
        Filter out contours smaller than minimum area threshold.
        
        Args:
            contours: List of contours
        
        Returns:
            Filtered list of contours
        """
        filtered = []
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if area >= self.min_area:
                filtered.append(contour)
        
        return filtered
    
    def contour_to_shapely_polygon(self, contour: np.ndarray) -> Optional[Polygon]:
        """
        Convert OpenCV contour to Shapely Polygon with validation.
        
        Args:
            contour: OpenCV contour array
        
        Returns:
            Shapely Polygon object or None if conversion fails
        """
        if not SHAPELY_AVAILABLE:
            return None
        
        try:
            # Extract coordinates
            coords = contour.reshape(-1, 2).tolist()
            
            # Need at least 3 points for a polygon
            if len(coords) < 3:
                return None
            
            # Create polygon
            polygon = Polygon(coords)
            
            # Validate and fix if needed
            if not polygon.is_valid:
                polygon = make_valid(polygon)
            
            # Apply optional simplification
            if self.shapely_tolerance is not None and self.shapely_tolerance > 0:
                polygon = polygon.simplify(
                    self.shapely_tolerance,
                    preserve_topology=True
                )
            
            return polygon
            
        except Exception as e:
            print(f"Warning: Failed to convert contour to Shapely polygon: {e}")
            return None
    
    def detect_boundaries(self, mask: np.ndarray) -> List[Dict]:
        """
        Detect building boundaries using comprehensive GIS-ready pipeline.
        
        Pipeline:
        1. Preprocess mask (morphological closing + opening)
        2. Extract external contours
        3. Filter small objects
        4. Simplify contours with Douglas-Peucker
        5. Convert to Shapely polygons (optional)
        6. Extract metadata (area, perimeter, bbox)
        
        Args:
            mask: Binary segmentation mask (H, W) with values 0 or 255
        
        Returns:
            List of building dictionaries with GIS-ready polygon data
        """
        # Step 1: Preprocess mask
        preprocessed = self.preprocess_mask(mask)
        
        # Step 2: Extract contours
        contours = self.extract_contours(preprocessed)
        
        # Step 3: Filter small objects
        filtered_contours = self.filter_small_objects(contours)
        
        buildings = []
        
        # Step 4-6: Process each contour
        for idx, contour in enumerate(filtered_contours):
            # Simplify contour
            simplified = self.simplify_contour(contour)
            
            # Calculate metrics
            area = cv2.contourArea(simplified)
            perimeter = cv2.arcLength(simplified, True)
            
            # Get bounding box
            x, y, w, h = cv2.boundingRect(simplified)
            
            # Extract coordinates
            coordinates = simplified.reshape(-1, 2).tolist()
            
            # Build result dictionary
            building = {
                'id': idx + 1,
                'area': float(area),
                'perimeter': float(perimeter),
                'coordinates': coordinates,
                'bbox': [int(x), int(y), int(w), int(h)],
                'num_points': len(coordinates)
            }
            
            # Optional: Add Shapely-derived fields (WKT only, not the object itself)
            if SHAPELY_AVAILABLE:
                shapely_poly = self.contour_to_shapely_polygon(simplified)
                if shapely_poly is not None:
                    building['shapely_area'] = float(shapely_poly.area)
                    building['shapely_wkt'] = shapely_poly.wkt
            
            buildings.append(building)
        
        return buildings
    
    def draw_boundaries(
        self,
        image: np.ndarray,
        buildings: List[Dict],
        color: Tuple[int, int, int] = (0, 255, 0),
        thickness: int = 2
    ) -> np.ndarray:
        """
        Draw building boundaries on image.
        
        Args:
            image: Input image (H, W, 3)
            buildings: List of building polygons from detect_boundaries()
            color: RGB color for boundaries
            thickness: Line thickness
        
        Returns:
            Image with boundaries drawn
        """
        result = image.copy()
        
        for building in buildings:
            coords = np.array(building['coordinates'], dtype=np.int32)
            cv2.polylines(result, [coords], True, color, thickness)
        
        return result
