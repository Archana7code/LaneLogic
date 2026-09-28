"""
LaneLogic - Geometry & Road-Space Measurement
==============================================
Provides dimensional verification, image-space geometric occupancy estimation,
and optional 4-point homography/perspective projection calibration.
"""

from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import cv2
from shapely.geometry import Polygon, box


class PerspectiveCalibrator:
    """
    Handles perspective homography projection when calibration points are provided,
    mapping camera perspective to a top-down ground-plane approximation.
    """

    def __init__(
        self,
        src_points: Optional[List[List[float]]] = None,
        dst_width_m: float = 10.0,
        dst_length_m: float = 120.0,
        pixels_per_meter: float = 10.0,
    ):
        self.is_calibrated = False
        self.src_points = src_points
        self.dst_width_m = dst_width_m
        self.dst_length_m = dst_length_m
        self.dst_width_px = dst_width_m * pixels_per_meter
        self.dst_length_px = dst_length_m * pixels_per_meter
        self.pixels_per_meter = pixels_per_meter
        self.matrix = None
        self.inv_matrix = None

        if src_points and len(src_points) == 4:
            src = np.array(src_points, dtype=np.float32)
            # Standard top-down destination rectangle: [top-left, top-right, bottom-right, bottom-left]
            dst = np.array([
                [0, 0],
                [self.dst_width_px, 0],
                [self.dst_width_px, self.dst_length_px],
                [0, self.dst_length_px],
            ], dtype=np.float32)

            self.matrix = cv2.getPerspectiveTransform(src, dst)
            self.inv_matrix = cv2.getPerspectiveTransform(dst, src)
            self.is_calibrated = True

    def transform_point(self, point: Tuple[float, float]) -> Tuple[float, float]:
        """Transform image point (x, y) to top-down coordinates in meters."""
        if not self.is_calibrated or self.matrix is None:
            return point
        pts = np.array([[[point[0], point[1]]]], dtype=np.float32)
        transformed = cv2.perspectiveTransform(pts, self.matrix)
        x_m = float(transformed[0][0][0]) / self.pixels_per_meter
        y_m = float(transformed[0][0][1]) / self.pixels_per_meter
        return x_m, y_m

    def transform_polygon(self, pts: List[List[float]]) -> List[Tuple[float, float]]:
        """Transform list of image points [[x, y], ...] to top-down coordinates in meters."""
        if not self.is_calibrated or self.matrix is None or not pts:
            return [tuple(p) for p in pts]
        arr = np.array([[p[0], p[1]] for p in pts], dtype=np.float32).reshape(-1, 1, 2)
        transformed = cv2.perspectiveTransform(arr, self.matrix)
        result = []
        for pt in transformed:
            result.append((float(pt[0][0]) / self.pixels_per_meter, float(pt[0][1]) / self.pixels_per_meter))
        return result


def calculate_road_space_metrics(
    vehicle_bboxes: List[List[float]],
    road_polygon_pts: List[List[float]],
    road_length_meters: float,
    road_width_meters: float,
    calibrator: Optional[PerspectiveCalibrator] = None,
) -> Dict[str, Any]:
    """
    Audited, dimensionally consistent road space measurement:
    - Normalizes image vehicle box intersections against image road polygon area.
    - Uses unary_union to prevent double-counting overlapping vehicle bounding boxes.
    - Estimates physical square meters and equivalent blocked/occupied width.
    - When calibrated homography exists, projects vehicle ground footprint to calibrated metric ground plane.
    - Distinguishes geometric loss approximation from traffic capacity.
    """
    from shapely.ops import unary_union

    road_poly = Polygon(road_polygon_pts) if road_polygon_pts and len(road_polygon_pts) >= 3 else None
    road_poly_px_area = road_poly.area if road_poly else 0.0

    if road_poly is None or road_poly_px_area <= 0:
        return {
            "occupancy_pct": 0.0,
            "occupied_area_m2": 0.0,
            "occupied_width_meters": 0.0,
            "road_area_m2": round(road_length_meters * road_width_meters, 2),
            "is_calibrated_homography": False,
            "measurement_method": "geometric_polygon_ratio",
        }

    is_calibrated = bool(calibrator and calibrator.is_calibrated)

    if is_calibrated and calibrator is not None:
        # Calibrated Homography path:
        # Project each vehicle's bottom road-contact footprint to top-down ground plane (in meters)
        ground_road_poly = box(0.0, 0.0, calibrator.dst_width_m, calibrator.dst_length_m)
        calibrated_road_area_m2 = calibrator.dst_width_m * calibrator.dst_length_m

        ground_polys = []
        for bbox in vehicle_bboxes:
            if not bbox or len(bbox) < 4:
                continue
            x1, y1, x2, y2 = bbox
            # Contact footprint: bottom region of bbox where vehicle contacts road
            footprint_img = [[x1, y1], [x2, y1], [x2, y2], [x1, y2]]
            footprint_m = calibrator.transform_polygon(footprint_img)
            if len(footprint_m) >= 3:
                g_poly = Polygon(footprint_m)
                if g_poly.is_valid and not g_poly.is_empty:
                    inter_ground = g_poly.intersection(ground_road_poly)
                    if not inter_ground.is_empty and inter_ground.area > 0:
                        ground_polys.append(inter_ground)

        if ground_polys:
            union_ground = unary_union(ground_polys)
            occupied_area_m2 = min(calibrated_road_area_m2, union_ground.area)
        else:
            occupied_area_m2 = 0.0

        occupancy_pct = (occupied_area_m2 / calibrated_road_area_m2) * 100.0 if calibrated_road_area_m2 > 0 else 0.0
        occupied_width_m = occupied_area_m2 / max(1.0, calibrator.dst_length_m)

        return {
            "occupancy_pct": round(occupancy_pct, 2),
            "occupied_area_m2": round(occupied_area_m2, 2),
            "occupied_width_meters": round(occupied_width_m, 2),
            "road_area_m2": round(calibrated_road_area_m2, 2),
            "is_calibrated_homography": True,
            "measurement_method": "homography_calibrated",
        }

    # Image-Space Geometric Ratio path:
    valid_inters = []
    for bbox in vehicle_bboxes:
        if not bbox or len(bbox) < 4:
            continue
        v_box = box(bbox[0], bbox[1], bbox[2], bbox[3])
        if v_box.is_valid and not v_box.is_empty:
            inter = v_box.intersection(road_poly)
            if not inter.is_empty and inter.area > 0:
                valid_inters.append(inter)

    if valid_inters:
        # Unary union ensures overlapping bounding boxes are not double-counted
        union_inter = unary_union(valid_inters)
        total_intersection_px = union_inter.area
    else:
        total_intersection_px = 0.0

    # Image-space percentage of road area occupied
    occupancy_pct = min(100.0, (total_intersection_px / road_poly_px_area) * 100.0)

    # Physical road area
    road_area_m2 = road_length_meters * road_width_meters
    occupied_area_m2 = (occupancy_pct / 100.0) * road_area_m2
    occupied_width_m = occupied_area_m2 / max(1.0, road_length_meters)

    return {
        "occupancy_pct": round(occupancy_pct, 2),
        "occupied_area_m2": round(occupied_area_m2, 2),
        "occupied_width_meters": round(occupied_width_m, 2),
        "road_area_m2": round(road_area_m2, 2),
        "is_calibrated_homography": False,
        "measurement_method": "geometric_polygon_ratio",
    }
