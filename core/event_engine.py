"""
LaneLogic - Obstruction Event Engine
=====================================
Transforms vehicle-level detection tracks into time-bounded, deduplicated
canonical ObstructionEvent records. Handles event start, continuation,
temporary occlusion/disappearance tolerance, and event closure.
"""

from typing import Dict, List, Optional, Any
import math
from shapely.geometry import Polygon, box

from core.contracts import ObstructionEvent
from core.config import (
    DEFAULT_STATIONARY_THRESHOLD_SEC,
    DEFAULT_MAX_DISAPPEARANCE_GAP_SEC,
    DEFAULT_ROAD_WIDTH_M,
    DEFAULT_ROAD_LENGTH_M,
    SEVERITY_LEVELS,
)


def _safe_float(val: Any, default: float = 0.0) -> float:
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


class ObstructionEventEngine:
    """
    Stateful event builder that monitors vehicle tracks over time and aggregates
    stationary/parked vehicle states into distinct, bounded obstruction events.
    """

    def __init__(
        self,
        stationary_threshold_sec: float = DEFAULT_STATIONARY_THRESHOLD_SEC,
        max_disappearance_gap_sec: float = DEFAULT_MAX_DISAPPEARANCE_GAP_SEC,
        road_width_m: float = DEFAULT_ROAD_WIDTH_M,
        road_length_m: float = DEFAULT_ROAD_LENGTH_M,
        road_polygon: Optional[List[List[float]]] = None,
        queue_polygon: Optional[List[List[float]]] = None,
    ):
        self.stationary_threshold_sec = stationary_threshold_sec
        self.max_disappearance_gap_sec = max_disappearance_gap_sec
        self.road_width_m = road_width_m
        self.road_length_m = road_length_m
        self.road_poly = Polygon(road_polygon) if road_polygon and len(road_polygon) >= 3 else None
        self.queue_poly = Polygon(queue_polygon) if queue_polygon and len(queue_polygon) >= 3 else None

        # Active state: vehicle_id -> event dict
        self.active_events: Dict[int, Dict[str, Any]] = {}
        # Completed events list
        self.finalized_events: List[ObstructionEvent] = []
        # Last observed timestamp
        self.current_timestamp: float = 0.0
        # Track seen (vehicle_id, timestamp) to ignore frame duplicates
        self._seen_observations: set = set()

    def reset(self):
        """Reset internal state to process a new stream or batch independently."""
        self.active_events.clear()
        self.finalized_events.clear()
        self.current_timestamp = 0.0
        self._seen_observations.clear()

    def _calculate_occupied_metrics(self, bbox: List[float]) -> tuple[float, float, float]:
        """
        Estimate occupied road width and space loss percentage using road ROI geometry.
        Returns (occupied_width_m, occupied_area_m2, road_space_loss_pct).
        """
        if not self.road_poly or self.road_poly.area <= 0:
            # Fallback estimation if no polygon is provided
            box_w = max(0.0, bbox[2] - bbox[0]) if len(bbox) >= 4 else 0.0
            occ_width = min(self.road_width_m, 1.8)
            loss_pct = (occ_width / max(1.0, self.road_width_m)) * 100.0
            return occ_width, occ_width * 4.0, round(loss_pct, 2)

        if not bbox or len(bbox) < 4:
            return 0.0, 0.0, 0.0

        x1, y1, x2, y2 = bbox
        vbox = box(x1, y1, x2, y2)
        if not vbox.is_valid or vbox.is_empty:
            return 0.0, 0.0, 0.0

        intersection = vbox.intersection(self.road_poly)
        inter_area_px = intersection.area

        if inter_area_px <= 0:
            return 0.0, 0.0, 0.0

        road_poly_area_px = self.road_poly.area
        space_loss_pct = min(100.0, (inter_area_px / road_poly_area_px) * 100.0)

        # Usable road physical area
        road_physical_area_m2 = self.road_width_m * self.road_length_m
        occupied_area_m2 = (space_loss_pct / 100.0) * road_physical_area_m2
        occupied_width_m = occupied_area_m2 / max(1.0, self.road_length_m)

        return round(occupied_width_m, 2), round(occupied_area_m2, 2), round(space_loss_pct, 2)

    def _determine_initial_cause(self, vehicle_type: str, in_queue: bool, duration: float) -> tuple[str, float]:
        """Transparent heuristic for initial cause based on vehicle type and context."""
        if in_queue:
            return "traffic_signal_queue", 0.70
        if vehicle_type in ("truck", "bus"):
            return "loading_unloading", 0.75
        if vehicle_type == "motorcycle":
            return "unclassified" if duration < 10.0 else "illegal_parking", 0.60
        return "illegal_parking", 0.70

    def feed_observation(self, observation: Dict[str, Any]) -> List[ObstructionEvent]:
        """
        Process a single vehicle observation. Returns any events that ended or were finalized.
        Handles missing fields, deduplicates redundant timestamps, and manages gap tolerance.
        """
        if not observation or not isinstance(observation, dict):
            return []

        if "vehicle_id" not in observation or observation.get("vehicle_id") is None:
            return []

        try:
            vehicle_id = int(observation["vehicle_id"])
        except (ValueError, TypeError):
            return []

        try:
            timestamp = float(observation.get("timestamp", 0.0))
        except (ValueError, TypeError):
            timestamp = self.current_timestamp

        obs_key = (vehicle_id, round(timestamp, 3))
        if obs_key in self._seen_observations:
            # Duplicate observation in stream/batch - skip processing
            return []
        self._seen_observations.add(obs_key)

        self.current_timestamp = max(self.current_timestamp, timestamp)

        vehicle_type = str(observation.get("vehicle_type") or "car")
        road_id = str(observation.get("road_id") or "ROAD_001")
        camera_id = str(observation.get("camera_id") or "CAM_01")
        movement_state = str(observation.get("movement_state") or "moving")
        stationary_duration = float(observation.get("stationary_duration") or 0.0)
        bbox = observation.get("bbox") or [0.0, 0.0, 0.0, 0.0]
        if "position" in observation and observation["position"]:
            position = list(observation["position"])
        elif len(bbox) >= 4:
            position = [(bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2]
        else:
            position = [0.0, 0.0]

        in_waiting_zone = bool(observation.get("in_waiting_zone", False))

        # Check queue zone override
        if self.queue_poly and not in_waiting_zone and len(position) >= 2:
            p_box = box(position[0], position[1], position[0], position[1])
            if self.queue_poly.covers(p_box):
                in_waiting_zone = True

        is_obstructing = (
            movement_state == "parked"
            or (stationary_duration >= self.stationary_threshold_sec and not in_waiting_zone)
        )

        completed: List[ObstructionEvent] = []

        if is_obstructing:
            occupied_w, occ_area, loss_pct = self._calculate_occupied_metrics(bbox)

            if vehicle_id not in self.active_events:
                # Start new event with deterministic ID based on road, camera, vehicle, and start time
                start_time = round(max(0.0, timestamp - stationary_duration), 2)
                event_id = f"EVT_{road_id}_{camera_id}_{vehicle_id}_{int(start_time * 100)}"
                init_cause, init_conf = self._determine_initial_cause(vehicle_type, in_waiting_zone, stationary_duration)

                self.active_events[vehicle_id] = {
                    "event_id": event_id,
                    "road_id": road_id,
                    "camera_id": camera_id,
                    "vehicle_id": vehicle_id,
                    "vehicle_type": vehicle_type,
                    "start_time": start_time,
                    "end_time": timestamp,
                    "duration_sec": stationary_duration,
                    "location": position,
                    "bbox": bbox,
                    "road_width_m": self.road_width_m,
                    "occupied_width_m": occupied_w,
                    "road_space_loss_pct": loss_pct,
                    "recurrence_score": 0.0,
                    "cause": init_cause,
                    "cause_confidence": init_conf,
                    "cause_explanation": f"Vehicle stationary for {stationary_duration:.1f}s outside queue zone.",
                    "severity": self._calc_severity(stationary_duration, loss_pct),
                    "status": "active",
                    "last_seen_timestamp": timestamp,
                    "metadata": {
                        "peak_loss_pct": loss_pct,
                        "occupied_area_m2": occ_area,
                        "sample_count": 1,
                    },
                }
            else:
                # Update ongoing event
                ev = self.active_events[vehicle_id]
                ev["end_time"] = timestamp
                ev["duration_sec"] = round(timestamp - ev["start_time"], 2)
                ev["location"] = position
                ev["bbox"] = bbox
                ev["occupied_width_m"] = occupied_w
                ev["road_space_loss_pct"] = loss_pct
                ev["last_seen_timestamp"] = timestamp
                ev["severity"] = self._calc_severity(ev["duration_sec"], loss_pct)
                ev["metadata"]["peak_loss_pct"] = max(ev["metadata"]["peak_loss_pct"], loss_pct)
                ev["metadata"]["sample_count"] += 1
        else:
            # Vehicle is moving or waiting in queue
            if vehicle_id in self.active_events:
                # Close the event
                ev_data = self.active_events.pop(vehicle_id)
                ev_data["status"] = "ended"
                event = ObstructionEvent(**ev_data)
                self.finalized_events.append(event)
                completed.append(event)

        # Check for expired/abandoned tracks that stopped reporting beyond max_disappearance_gap_sec
        expired_ids = []
        for v_id, ev_data in self.active_events.items():
            if timestamp - ev_data["last_seen_timestamp"] > self.max_disappearance_gap_sec:
                expired_ids.append(v_id)

        for v_id in expired_ids:
            ev_data = self.active_events.pop(v_id)
            ev_data["end_time"] = ev_data["last_seen_timestamp"]
            ev_data["duration_sec"] = round(ev_data["last_seen_timestamp"] - ev_data["start_time"], 2)
            ev_data["status"] = "ended"
            event = ObstructionEvent(**ev_data)
            self.finalized_events.append(event)
            completed.append(event)

        return completed

    def flush(self) -> List[ObstructionEvent]:
        """Finalize all remaining active events at end of stream/video."""
        remaining = []
        for ev_data in list(self.active_events.values()):
            ev_data["status"] = "ended"
            event = ObstructionEvent(**ev_data)
            self.finalized_events.append(event)
            remaining.append(event)
        self.active_events.clear()
        return remaining

    def process_batch(self, detections: List[Dict[str, Any]]) -> List[ObstructionEvent]:
        """Process an entire list of detections chronologically and return finalized events."""
        self.reset()
        if not detections:
            return []
        valid_dets = [d for d in detections if isinstance(d, dict) and d.get("vehicle_id") is not None]
        sorted_dets = sorted(valid_dets, key=lambda d: _safe_float(d.get("timestamp", 0.0), 0.0))
        for det in sorted_dets:
            self.feed_observation(det)
        self.flush()
        return list(self.finalized_events)

    def _calc_severity(self, duration_sec: float, space_loss_pct: float) -> str:
        """Transparent multi-factor severity scoring based on duration and space loss."""
        crit = SEVERITY_LEVELS["critical"]
        if space_loss_pct >= crit["min_loss_pct"] or duration_sec >= crit["min_duration_sec"]:
            return "critical"
        high = SEVERITY_LEVELS["high"]
        if space_loss_pct >= high["min_loss_pct"] or duration_sec >= high["min_duration_sec"]:
            return "high"
        mod = SEVERITY_LEVELS["moderate"]
        if space_loss_pct >= mod["min_loss_pct"] or duration_sec >= mod["min_duration_sec"]:
            return "moderate"
        low = SEVERITY_LEVELS["low"]
        if space_loss_pct >= low["min_loss_pct"] or duration_sec >= low["min_duration_sec"]:
            return "low"
        return "normal"
