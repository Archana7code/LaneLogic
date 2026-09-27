# """
# LaneLogic - PERSON 2: Space & Cause Analysis
# ==============================================
# Role in the pipeline: the "understanding" part.

# Input:
#   - detections.json produced by PERSON 1 (list of per-frame vehicle records:
#     vehicle_id, vehicle_type, bbox, position, timestamp, confidence,
#     movement_state).
#   - roi_config.json describing the road polygon, an optional signal/queue
#     zone polygon, and school-zone active hours.

# What this file does:
#   1. Loads the road ROI polygon and computes its area.
#   2. Groups Person 1's detections into fixed-length time windows
#      (default 10 seconds).
#   3. For each window, computes:
#        - vehicle count / traffic density
#        - road occupancy % (sum of vehicle-box area inside the ROI /
#          ROI area)
#        - approximate blocked road space % (occupancy from vehicles that
#          are NOT "moving", i.e. signal_waiting + parked)
#   4. Applies transparent, explainable RULE-BASED logic (no trained model,
#      since no labeled cause dataset exists) to guess the most likely cause
#      of blockage in that window, e.g.:
#        - "traffic_signal_queue"  : many vehicles waiting inside the
#                                     configured queue zone
#        - "illegal_parking"       : many "parked" vehicles outside the
#                                     queue zone, spread along the roadside
#        - "loading_unloading"     : one or two trucks/buses "parked" for a
#                                     long single stretch outside the queue
#                                     zone
#        - "school_drop_off"       : a cluster of cars stopped briefly,
#                                     only during configured school hours
#        - "general_congestion"    : high density but movement_state mostly
#                                     "moving" (slow-moving traffic, not a
#                                     stationary blockage)
#        - "normal"                : low density / low occupancy
#   5. Writes one JSON record per time window for PERSON 3 (backend/API)
#      and, downstream, PERSON 4 (recurrence & recommendation).

# This module intentionally never claims a guaranteed ML accuracy number -
# every "cause" is a rule-based, explainable label, not a model prediction.

# Run example:
#   python main.py --detections detections.json --roi roi_config.json \
#                   --output analysis.json --window-seconds 10
# """

# import argparse
# import json
# from collections import defaultdict
# from datetime import datetime, time as dtime

# from shapely.geometry import Polygon, box as shapely_box


# def load_roi(roi_path):
#     with open(roi_path) as f:
#         roi = json.load(f)
#     roi["_road_polygon_shape"] = Polygon(roi["road_polygon"])
#     if roi.get("signal_queue_zone"):
#         roi["_queue_zone_shape"] = Polygon(roi["signal_queue_zone"]["polygon"])
#     else:
#         roi["_queue_zone_shape"] = None
#     return roi


# def load_detections(detections_path):
#     with open(detections_path) as f:
#         return json.load(f)


# def group_into_windows(records, window_seconds):
#     windows = defaultdict(list)
#     for r in records:
#         window_index = int(r["timestamp"] // window_seconds)
#         windows[window_index].append(r)
#     return dict(sorted(windows.items()))


# def vehicle_box_area_inside_roi(record, road_polygon):
#     x1, y1, x2, y2 = record["bbox"]
#     vbox = shapely_box(x1, y1, x2, y2)
#     if not vbox.is_valid or vbox.area == 0:
#         return 0.0
#     inter = vbox.intersection(road_polygon)
#     return inter.area


# def is_inside_queue_zone(record, queue_zone_shape):
#     if queue_zone_shape is None:
#         return False
#     x, y = record["position"]
#     from shapely.geometry import Point
#     return queue_zone_shape.contains(Point(x, y))


# def in_school_hours(clock_time_str, school_hours):
#     if not school_hours:
#         return False
#     fmt = "%H:%M"
#     t = datetime.strptime(clock_time_str, fmt).time()
#     start = datetime.strptime(school_hours["start"], fmt).time()
#     end = datetime.strptime(school_hours["end"], fmt).time()
#     return start <= t <= end


# def classify_cause(window_records, roi, occupancy_pct, blocked_pct, wall_clock_time=None):
#     """
#     Transparent rule-based cause classifier.
#     Every threshold below is a tunable demo constant, not a learned weight.
#     """
#     if occupancy_pct < 15:
#         return "normal", "Low road occupancy; no significant blockage detected."

#     non_moving = [r for r in window_records if r["movement_state"] != "moving"]
#     parked = [r for r in window_records if r["movement_state"] == "parked"]
#     waiting = [r for r in window_records if r["movement_state"] == "signal_waiting"]

#     queue_zone_shape = roi.get("_queue_zone_shape")
#     in_queue = [r for r in non_moving if is_inside_queue_zone(r, queue_zone_shape)]

#     # Rule 1: majority of stopped vehicles are inside the configured
#     # signal/queue polygon -> signal queue, not a road obstruction.
#     if non_moving and len(in_queue) / len(non_moving) >= 0.6:
#         return (
#             "traffic_signal_queue",
#             f"{len(in_queue)} of {len(non_moving)} stationary vehicles are "
#             f"inside the configured signal/queue zone.",
#         )

#     outside_queue_parked = [r for r in parked if not is_inside_queue_zone(r, queue_zone_shape)]

#     # Rule 2: one or two large, long-parked vehicles (truck/bus) outside
#     # the queue zone -> likely loading/unloading.
#     heavy_parked = [r for r in outside_queue_parked if r["vehicle_type"] in ("truck", "bus")]
#     if 1 <= len(heavy_parked) <= 2 and len(outside_queue_parked) <= 3:
#         return (
#             "loading_unloading",
#             f"{len(heavy_parked)} truck/bus vehicle(s) parked for an extended "
#             f"period outside the signal zone, consistent with loading/unloading.",
#         )

#     # Rule 3: several small vehicles parked along the roadside, spread out,
#     # outside the queue zone, during school hours -> school drop-off.
#     school_hours = roi.get("school_zone_active_hours")
#     small_waiting_or_parked = [
#         r for r in (waiting + outside_queue_parked)
#         if r["vehicle_type"] in ("car", "motorcycle")
#     ]
#     if wall_clock_time and in_school_hours(wall_clock_time, school_hours) and len(small_waiting_or_parked) >= 3:
#         return (
#             "school_drop_off",
#             f"{len(small_waiting_or_parked)} cars/two-wheelers briefly stopped "
#             f"during the configured school drop-off window "
#             f"({school_hours['start']}-{school_hours['end']}).",
#         )

#     # Rule 4: many vehicles parked outside the queue zone, spread along the
#     # road, not matching the loading pattern -> generic illegal parking.
#     if len(outside_queue_parked) >= 3:
#         return (
#             "illegal_parking",
#             f"{len(outside_queue_parked)} vehicles parked outside the "
#             f"signal/queue zone for an extended duration.",
#         )

#     # Rule 5: high occupancy but vehicles are still mostly "moving" ->
#     # slow-moving congestion rather than a stationary obstruction.
#     if blocked_pct < 10 and occupancy_pct >= 40:
#         return "general_congestion", "High vehicle density with vehicles still moving; likely slow-moving traffic."

#     return "unclassified", "Occupancy is elevated but no rule matched a specific cause confidently."


# def analyze(detections, roi, window_seconds):
#     windows = group_into_windows(detections, window_seconds)
#     road_polygon = roi["_road_polygon_shape"]
#     road_area = road_polygon.area

#     results = []
#     for window_index, records in windows.items():
#         # Only keep one record per vehicle_id per window (its latest state)
#         # to avoid over-counting the same vehicle across frames in a window.
#         latest_by_vehicle = {}
#         for r in records:
#             latest_by_vehicle[r["vehicle_id"]] = r
#         window_records = list(latest_by_vehicle.values())

#         total_area = sum(
#             vehicle_box_area_inside_roi(r, road_polygon) for r in window_records
#         )
#         blocked_area = sum(
#             vehicle_box_area_inside_roi(r, road_polygon)
#             for r in window_records
#             if r["movement_state"] != "moving"
#         )

#         occupancy_pct = round(100.0 * total_area / road_area, 2) if road_area else 0.0
#         blocked_pct = round(100.0 * blocked_area / road_area, 2) if road_area else 0.0
#         occupancy_pct = min(occupancy_pct, 100.0)
#         blocked_pct = min(blocked_pct, 100.0)

#         cause, explanation = classify_cause(window_records, roi, occupancy_pct, blocked_pct)

#         results.append(
#             {
#                 "road_id": roi["road_id"],
#                 "road_name": roi["road_name"],
#                 "window_index": window_index,
#                 "window_start_seconds": window_index * window_seconds,
#                 "window_end_seconds": (window_index + 1) * window_seconds,
#                 "vehicle_count": len(window_records),
#                 "occupancy_pct": occupancy_pct,
#                 "blocked_pct": blocked_pct,
#                 "cause": cause,
#                 "cause_explanation": explanation,
#                 "vehicle_type_breakdown": _type_breakdown(window_records),
#             }
#         )

#     return results


# def _type_breakdown(records):
#     breakdown = defaultdict(int)
#     for r in records:
#         breakdown[r["vehicle_type"]] += 1
#     return dict(breakdown)


# def main():
#     parser = argparse.ArgumentParser(description="LaneLogic Person 2: Space & Cause Analysis")
#     parser.add_argument("--detections", default="../person1_detection/detections.json",
#                          help="Path to Person 1's detections.json")
#     parser.add_argument("--roi", default="roi_config.json",
#                          help="Path to roi_config.json")
#     parser.add_argument("--output", default="analysis.json",
#                          help="Path to write window-level analysis JSON")
#     parser.add_argument("--window-seconds", type=int, default=10,
#                          help="Time window size in seconds for aggregation")
#     args = parser.parse_args()

#     roi = load_roi(args.roi)
#     detections = load_detections(args.detections)
#     results = analyze(detections, roi, args.window_seconds)

#     with open(args.output, "w") as f:
#         json.dump(results, f, indent=2)

#     print(f"[Person2] Analyzed {len(detections)} detection records into "
#           f"{len(results)} time windows -> {args.output}")
#     for r in results[:5]:
#         print(f"  window {r['window_index']}: occupancy={r['occupancy_pct']}% "
#               f"blocked={r['blocked_pct']}% cause={r['cause']}")


# if __name__ == "__main__":
#     main()









# """
# LaneLogic - PERSON 2: Space & Cause Analysis
# =============================================

# Role:
#     Understand how much of the road is occupied/blocked and determine
#     the most likely cause using transparent rule-based logic.

# INPUT FROM PERSON 1:
#     detections.json

# Each detection contains:
#     vehicle_id
#     vehicle_type
#     bbox
#     position
#     timestamp
#     confidence
#     movement_state

# INPUT:
#     roi_config.json

# MAIN JOB:
#     1. Load road ROI.
#     2. Divide detections into time windows.
#     3. Count unique vehicles.
#     4. Calculate road occupancy.
#     5. Calculate blocked road occupancy.
#     6. Estimate occupied road area in square meters.
#     7. Calculate space usage percentage.
#     8. Assign severity / priority.
#     9. Determine likely cause.
#    10. Produce JSON for Person 3 backend.

# IMPORTANT:
#     Occupancy is calculated from vehicle bounding-box area inside
#     the configured road polygon.

#     Example:
#         Road area = 20m x 120m = 2400m²
#         Vehicle-covered area = 1200m²

#         occupancy = 1200 / 2400 * 100
#                   = 50%

#     This is an APPROXIMATE road-space occupancy measure.
#     Exact physical width in meters requires camera calibration/
#     perspective transformation.
# """

# import argparse
# import requests
# import json
# from collections import defaultdict
# from datetime import datetime

# from shapely.geometry import Polygon, Point
# from shapely.geometry import box as shapely_box


# # ============================================================
# # DEFAULT SETTINGS
# # ============================================================

# DEFAULT_WINDOW_SECONDS = 2
# BACKEND_URL = "http://localhost:8000"

# # Occupancy / severity thresholds.
# # These are transparent demo thresholds and can be tuned later.
# LOW_OCCUPANCY_PCT = 20.0
# MODERATE_OCCUPANCY_PCT = 40.0
# HIGH_OCCUPANCY_PCT = 60.0
# CRITICAL_OCCUPANCY_PCT = 80.0

# # Blocked-space thresholds.
# LOW_BLOCKED_PCT = 10.0
# MODERATE_BLOCKED_PCT = 25.0
# HIGH_BLOCKED_PCT = 40.0
# CRITICAL_BLOCKED_PCT = 60.0


# # ============================================================
# # LOAD ROI CONFIG
# # ============================================================

# def load_roi(roi_path):
#     with open(roi_path, "r", encoding="utf-8") as f:
#         roi = json.load(f)

#     # ----------------------------
#     # Validate road polygon
#     # ----------------------------
#     if "road_polygon" not in roi:
#         raise ValueError("roi_config.json must contain 'road_polygon'.")

#     if len(roi["road_polygon"]) < 3:
#         raise ValueError("road_polygon must contain at least 3 points.")

#     road_polygon = Polygon(roi["road_polygon"])

#     if not road_polygon.is_valid:
#         road_polygon = road_polygon.buffer(0)

#     if road_polygon.is_empty:
#         raise ValueError("Invalid road_polygon.")

#     roi["_road_polygon_shape"] = road_polygon

#     # ----------------------------
#     # Signal / queue zone
#     # ----------------------------
#     if roi.get("signal_queue_zone"):
#         queue_polygon = Polygon(
#             roi["signal_queue_zone"]["polygon"]
#         )

#         if not queue_polygon.is_valid:
#             queue_polygon = queue_polygon.buffer(0)

#         roi["_queue_zone_shape"] = queue_polygon
#     else:
#         roi["_queue_zone_shape"] = None

#     return roi


# # ============================================================
# # LOAD PERSON 1 DETECTIONS
# # ============================================================

# def load_detections(detections_path):
#     with open(detections_path, "r", encoding="utf-8") as f:
#         data = json.load(f)

#     if not isinstance(data, list):
#         raise ValueError(
#             "detections.json must contain a list of detection records."
#         )

#     return data


# # ============================================================
# # GROUP DETECTIONS INTO TIME WINDOWS
# # ============================================================

# def group_into_windows(records, window_seconds):
#     windows = defaultdict(list)

#     for record in records:
#         timestamp = float(record.get("timestamp", 0.0))

#         window_index = int(timestamp // window_seconds)

#         windows[window_index].append(record)

#     return dict(sorted(windows.items()))


# # ============================================================
# # VEHICLE AREA INSIDE ROAD ROI
# # ============================================================

# def vehicle_box_area_inside_roi(record, road_polygon):
#     bbox = record.get("bbox")

#     if not bbox or len(bbox) != 4:
#         return 0.0

#     x1, y1, x2, y2 = map(float, bbox)

#     if x2 <= x1 or y2 <= y1:
#         return 0.0

#     vehicle_box = shapely_box(x1, y1, x2, y2)

#     if not vehicle_box.is_valid or vehicle_box.area <= 0:
#         return 0.0

#     intersection = vehicle_box.intersection(road_polygon)

#     if intersection.is_empty:
#         return 0.0

#     return float(intersection.area)


# # ============================================================
# # QUEUE ZONE CHECK
# # ============================================================

# def is_inside_queue_zone(record, queue_zone_shape):
#     if queue_zone_shape is None:
#         return False

#     position = record.get("position")

#     if not position or len(position) != 2:
#         return False

#     x, y = map(float, position)

#     return queue_zone_shape.contains(Point(x, y))


# # ============================================================
# # SCHOOL HOURS
# # ============================================================

# def in_school_hours(clock_time_str, school_hours):
#     if not clock_time_str or not school_hours:
#         return False

#     try:
#         fmt = "%H:%M"

#         current_time = datetime.strptime(
#             clock_time_str,
#             fmt
#         ).time()

#         start_time = datetime.strptime(
#             school_hours["start"],
#             fmt
#         ).time()

#         end_time = datetime.strptime(
#             school_hours["end"],
#             fmt
#         ).time()

#         return start_time <= current_time <= end_time

#     except (ValueError, KeyError):
#         return False


# # ============================================================
# # SEVERITY / PRIORITY
# # ============================================================

# def calculate_severity(occupancy_pct, blocked_pct):
#     """
#     Priority is based mainly on road-space occupancy.

#     blocked_pct is also considered because stationary blockage
#     is more problematic than normal moving traffic.
#     """

#     # Critical:
#     # Very high overall occupancy OR very high blocked space.
#     if (
#         occupancy_pct >= CRITICAL_OCCUPANCY_PCT
#         or blocked_pct >= CRITICAL_BLOCKED_PCT
#     ):
#         return "critical", 4

#     # High:
#     if (
#         occupancy_pct >= HIGH_OCCUPANCY_PCT
#         or blocked_pct >= HIGH_BLOCKED_PCT
#     ):
#         return "high", 3

#     # Moderate:
#     if (
#         occupancy_pct >= MODERATE_OCCUPANCY_PCT
#         or blocked_pct >= MODERATE_BLOCKED_PCT
#     ):
#         return "moderate", 2

#     # Low:
#     if (
#         occupancy_pct >= LOW_OCCUPANCY_PCT
#         or blocked_pct >= LOW_BLOCKED_PCT
#     ):
#         return "low", 1

#     return "normal", 0


# # ============================================================
# # CAUSE CLASSIFICATION
# # ============================================================

# def classify_cause(
#     window_records,
#     roi,
#     occupancy_pct,
#     blocked_pct,
#     wall_clock_time=None
# ):
#     """
#     Explainable rule-based cause classifier.

#     IMPORTANT:
#         This is NOT an ML prediction.
#         It is a transparent rule-based interpretation.
#     """

#     if occupancy_pct < LOW_OCCUPANCY_PCT:
#         return (
#             "normal",
#             "Low road-space occupancy; no significant blockage detected."
#         )

#     # --------------------------------------------------------
#     # Split vehicles by state
#     # --------------------------------------------------------

#     non_moving = [
#         r
#         for r in window_records
#         if r.get("movement_state") != "moving"
#     ]

#     parked = [
#         r
#         for r in window_records
#         if r.get("movement_state") == "parked"
#     ]

#     waiting = [
#         r
#         for r in window_records
#         if r.get("movement_state") == "signal_waiting"
#     ]

#     # --------------------------------------------------------
#     # Signal queue
#     # --------------------------------------------------------

#     queue_zone_shape = roi.get("_queue_zone_shape")

#     in_queue = [
#         r
#         for r in non_moving
#         if is_inside_queue_zone(
#             r,
#             queue_zone_shape
#         )
#     ]

#     if (
#         non_moving
#         and len(in_queue) / len(non_moving) >= 0.60
#     ):
#         return (
#             "traffic_signal_queue",
#             f"{len(in_queue)} of {len(non_moving)} "
#             f"stationary vehicles are inside the configured "
#             f"signal/queue zone."
#         )

#     # --------------------------------------------------------
#     # Parked vehicles outside queue zone
#     # --------------------------------------------------------

#     outside_queue_parked = [
#         r
#         for r in parked
#         if not is_inside_queue_zone(
#             r,
#             queue_zone_shape
#         )
#     ]

#     # --------------------------------------------------------
#     # Loading / unloading
#     # --------------------------------------------------------

#     heavy_parked = [
#         r
#         for r in outside_queue_parked
#         if r.get("vehicle_type") in ("truck", "bus")
#     ]

#     if (
#         1 <= len(heavy_parked) <= 2
#         and len(outside_queue_parked) <= 3
#     ):
#         return (
#             "loading_unloading",
#             f"{len(heavy_parked)} truck/bus vehicle(s) "
#             f"parked outside the signal zone, consistent "
#             f"with loading/unloading."
#         )

#     # --------------------------------------------------------
#     # School drop-off
#     # --------------------------------------------------------

#     school_hours = roi.get(
#         "school_zone_active_hours"
#     )

#     small_stopped = [
#         r
#         for r in (waiting + outside_queue_parked)
#         if r.get("vehicle_type")
#         in ("car", "motorcycle", "bicycle")
#     ]

#     if (
#         wall_clock_time
#         and in_school_hours(
#             wall_clock_time,
#             school_hours
#         )
#         and len(small_stopped) >= 3
#     ):
#         return (
#             "school_drop_off",
#             f"{len(small_stopped)} cars/two-wheelers "
#             f"stopped during the configured school "
#             f"drop-off period."
#         )

#     # --------------------------------------------------------
#     # Illegal parking
#     # --------------------------------------------------------

#     if len(outside_queue_parked) >= 3:
#         return (
#             "illegal_parking",
#             f"{len(outside_queue_parked)} vehicles parked "
#             f"outside the signal/queue zone."
#         )

#     # --------------------------------------------------------
#     # General congestion
#     # --------------------------------------------------------

#     if (
#         blocked_pct < LOW_BLOCKED_PCT
#         and occupancy_pct >= MODERATE_OCCUPANCY_PCT
#     ):
#         return (
#             "general_congestion",
#             "High road-space occupancy with most vehicles "
#             "still moving; likely slow-moving congestion."
#         )

#         # --------------------------------------------------------
#     # Single parked vehicle / unclear obstruction
#     # --------------------------------------------------------

#     if len(outside_queue_parked) >= 1:
#         return (
#             "illegal_parking",
#             f"{len(outside_queue_parked)} vehicle(s) marked as parked "
#             f"outside the signal/queue zone. Further verification "
#             f"is recommended."
#         )

#     # --------------------------------------------------------
#     # Elevated but unclear
#     # --------------------------------------------------------

#     return (
#         "unclassified",
#         "Road-space occupancy is elevated, but the available "
#         "vehicle states and configured zones do not identify "
#         "a specific cause."
#     )


# # ============================================================
# # VEHICLE TYPE BREAKDOWN
# # ============================================================

# def type_breakdown(records):
#     breakdown = defaultdict(int)

#     for record in records:
#         vehicle_type = record.get(
#             "vehicle_type",
#             "unknown"
#         )

#         breakdown[vehicle_type] += 1

#     return dict(breakdown)


# # ============================================================
# # MOVEMENT STATE BREAKDOWN
# # ============================================================

# def state_breakdown(records):
#     breakdown = {
#         "moving": 0,
#         "signal_waiting": 0,
#         "parked": 0,
#         "unknown": 0,
#     }

#     for record in records:
#         state = record.get(
#             "movement_state",
#             "unknown"
#         )

#         if state not in breakdown:
#             state = "unknown"

#         breakdown[state] += 1

#     return breakdown


# # ============================================================
# # MAIN ANALYSIS
# # ============================================================

# def analyze(
#     detections,
#     roi,
#     window_seconds,
#     road_id_override=None,
#     road_name_override=None
# ):
#     windows = group_into_windows(
#         detections,
#         window_seconds
#     )

#     road_polygon = roi["_road_polygon_shape"]

#     road_pixel_area = road_polygon.area

#     if road_pixel_area <= 0:
#         raise ValueError(
#             "Road ROI area must be greater than zero."
#         )

#     # --------------------------------------------------------
#     # Physical road dimensions
#     # --------------------------------------------------------

#     road_length_meters = float(
#         roi.get("road_length_meters", 0)
#     )

#     road_width_meters = float(
#         roi.get("road_width_meters", 0)
#     )

#     physical_road_area_m2 = (
#         road_length_meters * road_width_meters
#     )

#     results = []

#     # ========================================================
#     # PROCESS EACH TIME WINDOW
#     # ========================================================

#     for window_index, records in windows.items():

#         # ----------------------------------------------------
#         # Keep only latest observation of each vehicle
#         # ----------------------------------------------------

#         latest_by_vehicle = {}

#         for record in records:
#             vehicle_id = record.get("vehicle_id")

#             if vehicle_id is None:
#                 continue

#             old_record = latest_by_vehicle.get(
#                 vehicle_id
#             )

#             if (
#                 old_record is None
#                 or float(record.get("timestamp", 0))
#                 >= float(old_record.get("timestamp", 0))
#             ):
#                 latest_by_vehicle[vehicle_id] = record

#         window_records = list(
#             latest_by_vehicle.values()
#         )

#         # ----------------------------------------------------
#         # Calculate total occupied vehicle area
#         # ----------------------------------------------------

#         total_vehicle_area_pixels = 0.0
#         blocked_vehicle_area_pixels = 0.0

#         for record in window_records:

#             vehicle_area = (
#                 vehicle_box_area_inside_roi(
#                     record,
#                     road_polygon
#                 )
#             )

#             total_vehicle_area_pixels += vehicle_area

#             if record.get("movement_state") == "parked":
#                 blocked_vehicle_area_pixels += vehicle_area

#         # ----------------------------------------------------
#         # Overall road-space occupancy
#         # ----------------------------------------------------

#         occupancy_pct = 0.0

#         if road_pixel_area > 0:
#             occupancy_pct = (
#                 100.0
#                 * total_vehicle_area_pixels
#                 / road_pixel_area
#             )

#         occupancy_pct = min(
#             max(occupancy_pct, 0.0),
#             100.0
#         )

#         # ----------------------------------------------------
#         # Blocked road-space occupancy
#         # ----------------------------------------------------

#         blocked_pct = 0.0

#         if road_pixel_area > 0:
#             blocked_pct = (
#                 100.0
#                 * blocked_vehicle_area_pixels
#                 / road_pixel_area
#             )

#         blocked_pct = min(
#             max(blocked_pct, 0.0),
#             100.0
#         )

#         occupancy_pct = round(
#             occupancy_pct,
#             2
#         )

#         blocked_pct = round(
#             blocked_pct,
#             2
#         )

#         # ----------------------------------------------------
#         # Convert occupancy to approximate physical area
#         # ----------------------------------------------------

#         occupied_area_m2 = None
#         blocked_area_m2 = None

#         if physical_road_area_m2 > 0:

#             occupied_area_m2 = round(
#                 physical_road_area_m2
#                 * occupancy_pct
#                 / 100.0,
#                 2
#             )

#             blocked_area_m2 = round(
#                 physical_road_area_m2
#                 * blocked_pct
#                 / 100.0,
#                 2
#             )

#         # ----------------------------------------------------
#         # Approximate equivalent width occupied
#         #
#         # Example:
#         # road width = 20m
#         # occupancy = 50%
#         #
#         # equivalent width = 10m
#         #
#         # IMPORTANT:
#         # This is an equivalent/normalized width, not a
#         # perspective-correct physical measurement.
#         # ----------------------------------------------------

#         equivalent_occupied_width_m = None
#         equivalent_blocked_width_m = None

#         if road_width_meters > 0:

#             equivalent_occupied_width_m = round(
#                 road_width_meters
#                 * occupancy_pct
#                 / 100.0,
#                 2
#             )

#             equivalent_blocked_width_m = round(
#                 road_width_meters
#                 * blocked_pct
#                 / 100.0,
#                 2
#             )

#         # ----------------------------------------------------
#         # Severity / priority
#         # ----------------------------------------------------

#         severity, priority_score = calculate_severity(
#             occupancy_pct,
#             blocked_pct
#         )

#         # ----------------------------------------------------
#         # Cause
#         # ----------------------------------------------------

#         cause, explanation = classify_cause(
#             window_records,
#             roi,
#             occupancy_pct,
#             blocked_pct,
#             wall_clock_time=None
#         )

#         # ----------------------------------------------------
#         # Final result
#         # ----------------------------------------------------

#         results.append(
#             {
#                 "road_id": (
#                     road_id_override
#                     or roi["road_id"]
#                 ),

#                 "road_name": (
#                     road_name_override
#                     or roi["road_name"]
#                 ),

#                 "window_index": window_index,

#                 "window_start_seconds": (
#                     window_index
#                     * window_seconds
#                 ),

#                 "window_end_seconds": (
#                     (window_index + 1)
#                     * window_seconds
#                 ),

#                 # ----------------------------
#                 # Vehicle information
#                 # ----------------------------

#                 "vehicle_count": len(
#                     window_records
#                 ),

#                 "vehicle_type_breakdown":
#                     type_breakdown(
#                         window_records
#                     ),

#                 "movement_state_breakdown":
#                     state_breakdown(
#                         window_records
#                     ),

#                 # ----------------------------
#                 # Space utilization
#                 # ----------------------------

#                 "road_length_meters":
#                     road_length_meters,

#                 "road_width_meters":
#                     road_width_meters,

#                 "road_area_m2":
#                     round(
#                         physical_road_area_m2,
#                         2
#                     )
#                     if physical_road_area_m2 > 0
#                     else None,

#                 "occupancy_pct":
#                     occupancy_pct,

#                 "blocked_pct":
#                     blocked_pct,

#                 "occupied_area_m2":
#                     occupied_area_m2,

#                 "blocked_area_m2":
#                     blocked_area_m2,

#                 "equivalent_occupied_width_meters":
#                     equivalent_occupied_width_m,

#                 "equivalent_blocked_width_meters":
#                     equivalent_blocked_width_m,

#                 # ----------------------------
#                 # Priority
#                 # ----------------------------

#                 "severity":
#                     severity,

#                 "priority_score":
#                     priority_score,

#                 # ----------------------------
#                 # Cause
#                 # ----------------------------

#                 "cause":
#                     cause,

#                 "cause_explanation":
#                     explanation,
#             }
#         )

#     return results


# # ============================================================
# # COMMAND LINE
# # ============================================================

# def main():

#     parser = argparse.ArgumentParser(
#         description=(
#             "LaneLogic Person 2 - "
#             "Space & Cause Analysis"
#         )
#     )

#     parser.add_argument(
#         "--detections",
#         default=(
#             "../person1_detection/"
#             "output/detections.json"
#         ),
#         help=(
#             "Path to Person 1 detections.json"
#         )
#     )

#     parser.add_argument(
#         "--roi",
#         default="roi_config.json",
#         help="Path to roi_config.json"
#     )

#     parser.add_argument(
#         "--output",
#         default="analysis.json",
#         help=(
#             "Path to output analysis JSON"
#         )
#     )

#     parser.add_argument(
#         "--window-seconds",
#         type=int,
#         default=DEFAULT_WINDOW_SECONDS,
#         help=(
#             "Time window size in seconds"
#         )
#     )

#     # --------------------------------------------------------
#     # Road identity overrides
#     # --------------------------------------------------------

#     parser.add_argument(
#         "--road-id",
#         default=None,
#         help=(
#             "Override road ID, e.g. ROAD_001"
#         )
#     )

#     parser.add_argument(
#         "--road-name",
#         default=None,
#         help=(
#             "Override road name, e.g. Traffic 1"
#         )
#     )

#     args = parser.parse_args()

#     # --------------------------------------------------------
#     # Load input
#     # --------------------------------------------------------

#     roi = load_roi(
#         args.roi
#     )

#     detections = load_detections(
#         args.detections
#     )

#     # --------------------------------------------------------
#     # Analyze
#     # --------------------------------------------------------

#     results = analyze(
#         detections=detections,
#         roi=roi,
#         window_seconds=args.window_seconds,
#         road_id_override=args.road_id,
#         road_name_override=args.road_name
#     )

#     # --------------------------------------------------------
#     # Save
#     # --------------------------------------------------------

#     with open(
#         args.output,
#         "w",
#         encoding="utf-8"
#     ) as f:

#         json.dump(
#             results,
#             f,
#             indent=2
#         )

#             # --------------------------------------------------------
#     # Send analysis to Person 3 backend
#     # --------------------------------------------------------

#     try:
#         response = requests.post(
#             f"{BACKEND_URL}/analysis/bulk",
#             json={"observations": results},
#             timeout=10
#         )

#         if response.ok:
#             print("✓ Analysis sent to Person 3 backend")
#         else:
#             print(
#                 f"✗ Backend rejected analysis: "
#                 f"{response.status_code}"
#             )
#             print(response.text)

#     except requests.RequestException as e:
#         print(
#             f"✗ Could not connect to Person 3 backend: {e}"
#         )

#     # --------------------------------------------------------
#     # Console summary
#     # --------------------------------------------------------

#     print()
#     print("=" * 65)
#     print("LANELOGIC - PERSON 2 ANALYSIS")
#     print("=" * 65)

#     print(
#         f"Road ID   : "
#         f"{args.road_id or roi['road_id']}"
#     )

#     print(
#         f"Road Name : "
#         f"{args.road_name or roi['road_name']}"
#     )

#     print(
#         f"Detections: {len(detections)}"
#     )

#     print(
#         f"Windows   : {len(results)}"
#     )

#     print(
#         f"Output    : {args.output}"
#     )

#     print("-" * 65)

#     for result in results[:10]:

#         print(
#             f"Window {result['window_index']:>3} | "
#             f"Vehicles: {result['vehicle_count']:>2} | "
#             f"Occupancy: "
#             f"{result['occupancy_pct']:>6.2f}% | "
#             f"Blocked: "
#             f"{result['blocked_pct']:>6.2f}% | "
#             f"Priority: "
#             f"{result['severity']:<8} | "
#             f"Cause: "
#             f"{result['cause']}"
#         )

#         if (
#             result[
#                 "equivalent_occupied_width_meters"
#             ] is not None
#         ):
#             print(
#                 " " * 20
#                 + "Equivalent occupied width: "
#                 f"{result['equivalent_occupied_width_meters']} m "
#                 f"/ "
#                 f"{result['road_width_meters']} m"
#             )

#     print("=" * 65)


# if __name__ == "__main__":
#     main()











# """
# LaneLogic - PERSON 2: Space & Cause Analysis
# =============================================

# Role:
#     Understand how much of the road is occupied/blocked and determine
#     the most likely cause using transparent rule-based logic.

# PERSON 1 INPUTS:
#     1. detections.json / detections1.json
#        Complete detection file for offline analysis.

#     2. detection_stream.jsonl
#        Phase-wise detection stream for real-time processing.

# REAL-TIME FLOW:

#     Person 1
#         ↓
#     detection_stream.jsonl
#         ↓
#     Person 2
#         ↓
#     Analyze one phase
#         ↓
#     POST to Person 3 backend
#         ↓
#     Website updates

# IMPORTANT:
#     The existing space/cause analysis logic is preserved.

#     Person 2 processes each phase as soon as it appears in
#     detection_stream.jsonl.

#     One phase is normally 5 seconds, controlled by Person 1.
# """

# import argparse
# import json
# import time
# import requests

# from collections import defaultdict
# from datetime import datetime

# from shapely.geometry import Polygon, Point
# from shapely.geometry import box as shapely_box


# # ============================================================
# # DEFAULT SETTINGS
# # ============================================================

# DEFAULT_WINDOW_SECONDS = 2

# BACKEND_URL = "http://localhost:8000"

# DEFAULT_PHASE_POLL_SECONDS = 0.5


# # ============================================================
# # OCCUPANCY / SEVERITY THRESHOLDS
# # ============================================================

# LOW_OCCUPANCY_PCT = 20.0
# MODERATE_OCCUPANCY_PCT = 40.0
# HIGH_OCCUPANCY_PCT = 60.0
# CRITICAL_OCCUPANCY_PCT = 80.0


# # ============================================================
# # BLOCKED-SPACE THRESHOLDS
# # ============================================================

# LOW_BLOCKED_PCT = 10.0
# MODERATE_BLOCKED_PCT = 25.0
# HIGH_BLOCKED_PCT = 40.0
# CRITICAL_BLOCKED_PCT = 60.0


# # ============================================================
# # LOAD ROI CONFIG
# # ============================================================

# def load_roi(roi_path):

#     with open(
#         roi_path,
#         "r",
#         encoding="utf-8"
#     ) as f:

#         roi = json.load(f)

#     # --------------------------------------------------------
#     # Validate road polygon
#     # --------------------------------------------------------

#     if "road_polygon" not in roi:

#         raise ValueError(
#             "roi_config.json must contain 'road_polygon'."
#         )

#     if len(roi["road_polygon"]) < 3:

#         raise ValueError(
#             "road_polygon must contain at least 3 points."
#         )

#     road_polygon = Polygon(
#         roi["road_polygon"]
#     )

#     if not road_polygon.is_valid:

#         road_polygon = road_polygon.buffer(0)

#     if road_polygon.is_empty:

#         raise ValueError(
#             "Invalid road_polygon."
#         )

#     roi["_road_polygon_shape"] = road_polygon

#     # --------------------------------------------------------
#     # Signal / queue zone
#     # --------------------------------------------------------

#     if roi.get("signal_queue_zone"):

#         queue_polygon = Polygon(
#             roi["signal_queue_zone"]["polygon"]
#         )

#         if not queue_polygon.is_valid:

#             queue_polygon = queue_polygon.buffer(0)

#         roi["_queue_zone_shape"] = queue_polygon

#     else:

#         roi["_queue_zone_shape"] = None

#     return roi


# # ============================================================
# # LOAD NORMAL PERSON 1 DETECTIONS
# # ============================================================

# def load_detections(detections_path):

#     with open(
#         detections_path,
#         "r",
#         encoding="utf-8"
#     ) as f:

#         data = json.load(f)

#     if not isinstance(data, list):

#         raise ValueError(
#             "detections.json must contain a list of detection records."
#         )

#     return data


# # ============================================================
# # GROUP DETECTIONS INTO TIME WINDOWS
# # ============================================================

# def group_into_windows(
#     records,
#     window_seconds
# ):

#     windows = defaultdict(list)

#     for record in records:

#         timestamp = float(
#             record.get(
#                 "timestamp",
#                 0.0
#             )
#         )

#         window_index = int(
#             timestamp // window_seconds
#         )

#         windows[window_index].append(
#             record
#         )

#     return dict(
#         sorted(
#             windows.items()
#         )
#     )


# # ============================================================
# # VEHICLE AREA INSIDE ROAD ROI
# # ============================================================

# def vehicle_box_area_inside_roi(
#     record,
#     road_polygon
# ):

#     bbox = record.get("bbox")

#     if not bbox or len(bbox) != 4:

#         return 0.0

#     x1, y1, x2, y2 = map(
#         float,
#         bbox
#     )

#     if x2 <= x1 or y2 <= y1:

#         return 0.0

#     vehicle_box = shapely_box(
#         x1,
#         y1,
#         x2,
#         y2
#     )

#     if (
#         not vehicle_box.is_valid
#         or vehicle_box.area <= 0
#     ):

#         return 0.0

#     intersection = vehicle_box.intersection(
#         road_polygon
#     )

#     if intersection.is_empty:

#         return 0.0

#     return float(
#         intersection.area
#     )


# # ============================================================
# # QUEUE ZONE CHECK
# # ============================================================

# def is_inside_queue_zone(
#     record,
#     queue_zone_shape
# ):

#     if queue_zone_shape is None:

#         return False

#     position = record.get(
#         "position"
#     )

#     if not position or len(position) != 2:

#         return False

#     x, y = map(
#         float,
#         position
#     )

#     return queue_zone_shape.contains(
#         Point(x, y)
#     )


# # ============================================================
# # SCHOOL HOURS
# # ============================================================

# def in_school_hours(
#     clock_time_str,
#     school_hours
# ):

#     if not clock_time_str or not school_hours:

#         return False

#     try:

#         fmt = "%H:%M"

#         current_time = datetime.strptime(
#             clock_time_str,
#             fmt
#         ).time()

#         start_time = datetime.strptime(
#             school_hours["start"],
#             fmt
#         ).time()

#         end_time = datetime.strptime(
#             school_hours["end"],
#             fmt
#         ).time()

#         return (
#             start_time
#             <= current_time
#             <= end_time
#         )

#     except (
#         ValueError,
#         KeyError
#     ):

#         return False


# # ============================================================
# # SEVERITY / PRIORITY
# # ============================================================

# def calculate_severity(
#     occupancy_pct,
#     blocked_pct
# ):

#     if (
#         occupancy_pct >= CRITICAL_OCCUPANCY_PCT
#         or blocked_pct >= CRITICAL_BLOCKED_PCT
#     ):

#         return "critical", 4

#     if (
#         occupancy_pct >= HIGH_OCCUPANCY_PCT
#         or blocked_pct >= HIGH_BLOCKED_PCT
#     ):

#         return "high", 3

#     if (
#         occupancy_pct >= MODERATE_OCCUPANCY_PCT
#         or blocked_pct >= MODERATE_BLOCKED_PCT
#     ):

#         return "moderate", 2

#     if (
#         occupancy_pct >= LOW_OCCUPANCY_PCT
#         or blocked_pct >= LOW_BLOCKED_PCT
#     ):

#         return "low", 1

#     return "normal", 0


# # ============================================================
# # CAUSE CLASSIFICATION
# # ============================================================

# def classify_cause(
#     window_records,
#     roi,
#     occupancy_pct,
#     blocked_pct,
#     wall_clock_time=None
# ):

#     """
#     Explainable rule-based cause classifier.

#     This is NOT an ML prediction.
#     It is a transparent rule-based interpretation.
#     """

#     if occupancy_pct < LOW_OCCUPANCY_PCT:

#         return (
#             "normal",
#             "Low road-space occupancy; no significant blockage detected."
#         )

#     # --------------------------------------------------------
#     # Split vehicles by state
#     # --------------------------------------------------------

#     non_moving = [
#         r
#         for r in window_records
#         if r.get("movement_state") != "moving"
#     ]

#     parked = [
#         r
#         for r in window_records
#         if r.get("movement_state") == "parked"
#     ]

#     waiting = [
#         r
#         for r in window_records
#         if r.get("movement_state") == "signal_waiting"
#     ]

#     # --------------------------------------------------------
#     # Signal queue
#     # --------------------------------------------------------

#     queue_zone_shape = roi.get(
#         "_queue_zone_shape"
#     )

#     in_queue = [
#         r
#         for r in non_moving
#         if is_inside_queue_zone(
#             r,
#             queue_zone_shape
#         )
#     ]

#     if (
#         non_moving
#         and len(in_queue) / len(non_moving) >= 0.60
#     ):

#         return (
#             "traffic_signal_queue",
#             f"{len(in_queue)} of {len(non_moving)} "
#             f"stationary vehicles are inside the configured "
#             f"signal/queue zone."
#         )

#     # --------------------------------------------------------
#     # Parked vehicles outside queue zone
#     # --------------------------------------------------------

#     outside_queue_parked = [
#         r
#         for r in parked
#         if not is_inside_queue_zone(
#             r,
#             queue_zone_shape
#         )
#     ]

#     # --------------------------------------------------------
#     # Loading / unloading
#     # --------------------------------------------------------

#     heavy_parked = [
#         r
#         for r in outside_queue_parked
#         if r.get("vehicle_type")
#         in ("truck", "bus")
#     ]

#     if (
#         1 <= len(heavy_parked) <= 2
#         and len(outside_queue_parked) <= 3
#     ):

#         return (
#             "loading_unloading",
#             f"{len(heavy_parked)} truck/bus vehicle(s) "
#             f"parked outside the signal zone, consistent "
#             f"with loading/unloading."
#         )

#     # --------------------------------------------------------
#     # School drop-off
#     # --------------------------------------------------------

#     school_hours = roi.get(
#         "school_zone_active_hours"
#     )

#     small_stopped = [
#         r
#         for r in (
#             waiting
#             + outside_queue_parked
#         )
#         if r.get("vehicle_type")
#         in (
#             "car",
#             "motorcycle",
#             "bicycle"
#         )
#     ]

#     if (
#         wall_clock_time
#         and in_school_hours(
#             wall_clock_time,
#             school_hours
#         )
#         and len(small_stopped) >= 3
#     ):

#         return (
#             "school_drop_off",
#             f"{len(small_stopped)} cars/two-wheelers "
#             f"stopped during the configured school "
#             f"drop-off period."
#         )

#     # --------------------------------------------------------
#     # Illegal parking
#     # --------------------------------------------------------

#     if len(outside_queue_parked) >= 3:

#         return (
#             "illegal_parking",
#             f"{len(outside_queue_parked)} vehicles parked "
#             f"outside the signal/queue zone."
#         )

#     # --------------------------------------------------------
#     # General congestion
#     # --------------------------------------------------------

#     if (
#         blocked_pct < LOW_BLOCKED_PCT
#         and occupancy_pct >= MODERATE_OCCUPANCY_PCT
#     ):

#         return (
#             "general_congestion",
#             "High road-space occupancy with most vehicles "
#             "still moving; likely slow-moving congestion."
#         )

#     # --------------------------------------------------------
#     # Single parked vehicle / unclear obstruction
#     # --------------------------------------------------------

#     if len(outside_queue_parked) >= 1:

#         return (
#             "illegal_parking",
#             f"{len(outside_queue_parked)} vehicle(s) marked as parked "
#             f"outside the signal/queue zone. Further verification "
#             f"is recommended."
#         )

#     # --------------------------------------------------------
#     # Elevated but unclear
#     # --------------------------------------------------------

#     return (
#         "unclassified",
#         "Road-space occupancy is elevated, but the available "
#         "vehicle states and configured zones do not identify "
#         "a specific cause."
#     )


# # ============================================================
# # VEHICLE TYPE BREAKDOWN
# # ============================================================

# def type_breakdown(records):

#     breakdown = defaultdict(int)

#     for record in records:

#         vehicle_type = record.get(
#             "vehicle_type",
#             "unknown"
#         )

#         breakdown[vehicle_type] += 1

#     return dict(
#         breakdown
#     )


# # ============================================================
# # MOVEMENT STATE BREAKDOWN
# # ============================================================

# def state_breakdown(records):

#     breakdown = {
#         "moving": 0,
#         "signal_waiting": 0,
#         "parked": 0,
#         "unknown": 0,
#     }

#     for record in records:

#         state = record.get(
#             "movement_state",
#             "unknown"
#         )

#         if state not in breakdown:

#             state = "unknown"

#         breakdown[state] += 1

#     return breakdown


# # ============================================================
# # MAIN ANALYSIS
# # ============================================================

# def analyze(
#     detections,
#     roi,
#     window_seconds,
#     road_id_override=None,
#     road_name_override=None
# ):

#     windows = group_into_windows(
#         detections,
#         window_seconds
#     )

#     road_polygon = roi[
#         "_road_polygon_shape"
#     ]

#     road_pixel_area = road_polygon.area

#     if road_pixel_area <= 0:

#         raise ValueError(
#             "Road ROI area must be greater than zero."
#         )

#     # --------------------------------------------------------
#     # Physical road dimensions
#     # --------------------------------------------------------

#     road_length_meters = float(
#         roi.get(
#             "road_length_meters",
#             0
#         )
#     )

#     road_width_meters = float(
#         roi.get(
#             "road_width_meters",
#             0
#         )
#     )

#     physical_road_area_m2 = (
#         road_length_meters
#         * road_width_meters
#     )

#     results = []

#     # ========================================================
#     # PROCESS EACH TIME WINDOW
#     # ========================================================

#     for window_index, records in windows.items():

#         # ----------------------------------------------------
#         # Keep latest observation of each vehicle
#         # ----------------------------------------------------

#         latest_by_vehicle = {}

#         for record in records:

#             vehicle_id = record.get(
#                 "vehicle_id"
#             )

#             if vehicle_id is None:

#                 continue

#             old_record = latest_by_vehicle.get(
#                 vehicle_id
#             )

#             if (
#                 old_record is None
#                 or float(
#                     record.get(
#                         "timestamp",
#                         0
#                     )
#                 )
#                 >= float(
#                     old_record.get(
#                         "timestamp",
#                         0
#                     )
#                 )
#             ):

#                 latest_by_vehicle[
#                     vehicle_id
#                 ] = record

#         window_records = list(
#             latest_by_vehicle.values()
#         )

#         # ----------------------------------------------------
#         # Calculate total occupied vehicle area
#         # ----------------------------------------------------

#         total_vehicle_area_pixels = 0.0

#         blocked_vehicle_area_pixels = 0.0

#         for record in window_records:

#             vehicle_area = (
#                 vehicle_box_area_inside_roi(
#                     record,
#                     road_polygon
#                 )
#             )

#             total_vehicle_area_pixels += (
#                 vehicle_area
#             )

#             if (
#                 record.get(
#                     "movement_state"
#                 )
#                 == "parked"
#             ):

#                 blocked_vehicle_area_pixels += (
#                     vehicle_area
#                 )

#         # ----------------------------------------------------
#         # Overall road-space occupancy
#         # ----------------------------------------------------

#         occupancy_pct = 0.0

#         if road_pixel_area > 0:

#             occupancy_pct = (
#                 100.0
#                 * total_vehicle_area_pixels
#                 / road_pixel_area
#             )

#         occupancy_pct = min(
#             max(
#                 occupancy_pct,
#                 0.0
#             ),
#             100.0
#         )

#         # ----------------------------------------------------
#         # Blocked road-space occupancy
#         # ----------------------------------------------------

#         blocked_pct = 0.0

#         if road_pixel_area > 0:

#             blocked_pct = (
#                 100.0
#                 * blocked_vehicle_area_pixels
#                 / road_pixel_area
#             )

#         blocked_pct = min(
#             max(
#                 blocked_pct,
#                 0.0
#             ),
#             100.0
#         )

#         occupancy_pct = round(
#             occupancy_pct,
#             2
#         )

#         blocked_pct = round(
#             blocked_pct,
#             2
#         )

#         # ----------------------------------------------------
#         # Convert occupancy to approximate physical area
#         # ----------------------------------------------------

#         occupied_area_m2 = None

#         blocked_area_m2 = None

#         if physical_road_area_m2 > 0:

#             occupied_area_m2 = round(
#                 physical_road_area_m2
#                 * occupancy_pct
#                 / 100.0,
#                 2
#             )

#             blocked_area_m2 = round(
#                 physical_road_area_m2
#                 * blocked_pct
#                 / 100.0,
#                 2
#             )

#         # ----------------------------------------------------
#         # Equivalent width
#         # ----------------------------------------------------

#         equivalent_occupied_width_m = None

#         equivalent_blocked_width_m = None

#         if road_width_meters > 0:

#             equivalent_occupied_width_m = round(
#                 road_width_meters
#                 * occupancy_pct
#                 / 100.0,
#                 2
#             )

#             equivalent_blocked_width_m = round(
#                 road_width_meters
#                 * blocked_pct
#                 / 100.0,
#                 2
#             )

#         # ----------------------------------------------------
#         # Severity
#         # ----------------------------------------------------

#         severity, priority_score = (
#             calculate_severity(
#                 occupancy_pct,
#                 blocked_pct
#             )
#         )

#         # ----------------------------------------------------
#         # Cause
#         # ----------------------------------------------------

#         cause, explanation = (
#             classify_cause(
#                 window_records,
#                 roi,
#                 occupancy_pct,
#                 blocked_pct,
#                 wall_clock_time=None
#             )
#         )

#         # ----------------------------------------------------
#         # Final result
#         # ----------------------------------------------------

#         results.append(
#             {
#                 "road_id": (
#                     road_id_override
#                     or roi["road_id"]
#                 ),

#                 "road_name": (
#                     road_name_override
#                     or roi["road_name"]
#                 ),

#                 "window_index":
#                     window_index,

#                 "window_start_seconds":
#                     (
#                         window_index
#                         * window_seconds
#                     ),

#                 "window_end_seconds":
#                     (
#                         (window_index + 1)
#                         * window_seconds
#                     ),

#                 # ----------------------------
#                 # Vehicle information
#                 # ----------------------------

#                 "vehicle_count":
#                     len(window_records),

#                 "vehicle_type_breakdown":
#                     type_breakdown(
#                         window_records
#                     ),

#                 "movement_state_breakdown":
#                     state_breakdown(
#                         window_records
#                     ),

#                 # ----------------------------
#                 # Space utilization
#                 # ----------------------------

#                 "road_length_meters":
#                     road_length_meters,

#                 "road_width_meters":
#                     road_width_meters,

#                 "road_area_m2":
#                     (
#                         round(
#                             physical_road_area_m2,
#                             2
#                         )
#                         if physical_road_area_m2 > 0
#                         else None
#                     ),

#                 "occupancy_pct":
#                     occupancy_pct,

#                 "blocked_pct":
#                     blocked_pct,

#                 "occupied_area_m2":
#                     occupied_area_m2,

#                 "blocked_area_m2":
#                     blocked_area_m2,

#                 "equivalent_occupied_width_meters":
#                     equivalent_occupied_width_m,

#                 "equivalent_blocked_width_meters":
#                     equivalent_blocked_width_m,

#                 # ----------------------------
#                 # Priority
#                 # ----------------------------

#                 "severity":
#                     severity,

#                 "priority_score":
#                     priority_score,

#                 # ----------------------------
#                 # Cause
#                 # ----------------------------

#                 "cause":
#                     cause,

#                 "cause_explanation":
#                     explanation,
#             }
#         )

#     return results


# # ============================================================
# # SEND ANALYSIS TO PERSON 3
# # ============================================================

# def send_to_backend(results):

#     if not results:

#         return False

#     try:

#         response = requests.post(
#             f"{BACKEND_URL}/analysis/bulk",
#             json={
#                 "observations": results
#             },
#             timeout=10
#         )

#         if response.ok:

#             print(
#                 "✓ Analysis sent to Person 3 backend"
#             )

#             return True

#         print(
#             f"✗ Backend rejected analysis: "
#             f"{response.status_code}"
#         )

#         print(
#             response.text
#         )

#         return False

#     except requests.RequestException as e:

#         print(
#             f"✗ Could not connect to Person 3 backend: {e}"
#         )

#         return False


# # ============================================================
# # SAVE COMPLETE ANALYSIS
# # ============================================================

# def save_complete_analysis(
#     results,
#     output_path
# ):

#     with open(
#         output_path,
#         "w",
#         encoding="utf-8"
#     ) as f:

#         json.dump(
#             results,
#             f,
#             indent=2
#         )


# # ============================================================
# # APPEND PHASE ANALYSIS TO JSONL
# # ============================================================

# def append_phase_output(
#     phase_number,
#     phase_start,
#     phase_end,
#     results,
#     output_path
# ):

#     phase_output = {
#         "phase": phase_number,
#         "start_time": phase_start,
#         "end_time": phase_end,
#         "record_count": len(results),
#         "observations": results
#     }

#     with open(
#         output_path,
#         "a",
#         encoding="utf-8"
#     ) as f:

#         f.write(
#             json.dumps(
#                 phase_output
#             )
#             + "\n"
#         )


# # ============================================================
# # PRINT PHASE SUMMARY
# # ============================================================

# def print_phase_summary(
#     phase_number,
#     phase_start,
#     phase_end,
#     detections,
#     results
# ):

#     print()
#     print("=" * 70)

#     print(
#         f"LANELOGIC - PERSON 2 - PHASE {phase_number}"
#     )

#     print("=" * 70)

#     print(
#         f"Phase     : {phase_start:.2f}s "
#         f"→ {phase_end:.2f}s"
#     )

#     print(
#         f"Detections: {len(detections)}"
#     )

#     print(
#         f"Windows   : {len(results)}"
#     )

#     print("-" * 70)

#     for result in results:

#         print(
#             f"Window {result['window_index']:>3} | "
#             f"Vehicles: {result['vehicle_count']:>2} | "
#             f"Occupancy: "
#             f"{result['occupancy_pct']:>6.2f}% | "
#             f"Blocked: "
#             f"{result['blocked_pct']:>6.2f}% | "
#             f"Priority: "
#             f"{result['severity']:<9} | "
#             f"Cause: "
#             f"{result['cause']}"
#         )

#     print("=" * 70)


# # ============================================================
# # REAL-TIME PHASE PROCESSOR
# # ============================================================

# def process_phase_stream(
#     phase_input,
#     roi,
#     output,
#     phase_output,
#     window_seconds,
#     road_id_override=None,
#     road_name_override=None,
#     poll_seconds=DEFAULT_PHASE_POLL_SECONDS
# ):

#     print()
#     print("=" * 70)
#     print("LANELOGIC - PERSON 2 REAL-TIME MODE")
#     print("=" * 70)

#     print(
#         f"Phase input : {phase_input}"
#     )

#     print(
#         f"Analysis    : {output}"
#     )

#     print(
#         f"Phase output: {phase_output}"
#     )

#     print(
#         f"Backend     : {BACKEND_URL}"
#     )

#     print()
#     print(
#         "Waiting for Person 1 phases..."
#     )

#     print(
#         "Press Ctrl+C to stop."
#     )

#     # --------------------------------------------------------
#     # All analysis results
#     # --------------------------------------------------------

#     all_results = []

#     # --------------------------------------------------------
#     # Number of lines already processed
#     # --------------------------------------------------------

#     processed_lines = 0

#     # --------------------------------------------------------
#     # Create phase analysis file fresh
#     # --------------------------------------------------------

#     with open(
#         phase_output,
#         "w",
#         encoding="utf-8"
#     ):
#         pass

#     try:

#         while True:

#             # ------------------------------------------------
#             # If Person 1 has not created the file yet
#             # ------------------------------------------------

#             try:

#                 with open(
#                     phase_input,
#                     "r",
#                     encoding="utf-8"
#                 ) as f:

#                     lines = f.readlines()

#             except FileNotFoundError:

#                 time.sleep(
#                     poll_seconds
#                 )

#                 continue

#             # ------------------------------------------------
#             # Process new phase lines
#             # ------------------------------------------------

#             if processed_lines < len(lines):

#                 new_lines = lines[
#                     processed_lines:
#                 ]

#                 for line in new_lines:

#                     line = line.strip()

#                     if not line:

#                         processed_lines += 1

#                         continue

#                     try:

#                         phase_data = json.loads(
#                             line
#                         )

#                     except json.JSONDecodeError as e:

#                         print(
#                             f"⚠ Could not read phase: {e}"
#                         )

#                         processed_lines += 1

#                         continue

#                     # ----------------------------------------
#                     # Read phase information
#                     # ----------------------------------------

#                     phase_number = phase_data.get(
#                         "phase",
#                         processed_lines + 1
#                     )

#                     phase_start = float(
#                         phase_data.get(
#                             "start_time",
#                             0.0
#                         )
#                     )

#                     phase_end = float(
#                         phase_data.get(
#                             "end_time",
#                             phase_start
#                         )
#                     )

#                     detections = phase_data.get(
#                         "detections",
#                         []
#                     )

#                     if not isinstance(
#                         detections,
#                         list
#                     ):

#                         print(
#                             f"⚠ Phase {phase_number} "
#                             f"has invalid detections."
#                         )

#                         processed_lines += 1

#                         continue

#                     print()
#                     print(
#                         f"→ New Phase {phase_number} received"
#                     )

#                     # ----------------------------------------
#                     # Analyze this phase
#                     # ----------------------------------------

#                     results = analyze(
#                         detections=detections,
#                         roi=roi,
#                         window_seconds=window_seconds,
#                         road_id_override=road_id_override,
#                         road_name_override=road_name_override
#                     )

#                     # ----------------------------------------
#                     # Add phase metadata
#                     # ----------------------------------------

#                     for result in results:

#                         result[
#                             "phase"
#                         ] = phase_number

#                         result[
#                             "phase_start_seconds"
#                         ] = phase_start

#                         result[
#                             "phase_end_seconds"
#                         ] = phase_end

#                     # ----------------------------------------
#                     # Save locally
#                     # ----------------------------------------

#                     all_results.extend(
#                         results
#                     )

#                     save_complete_analysis(
#                         all_results,
#                         output
#                     )

#                     append_phase_output(
#                         phase_number,
#                         phase_start,
#                         phase_end,
#                         results,
#                         phase_output
#                     )

#                     # ----------------------------------------
#                     # Send immediately to backend
#                     # ----------------------------------------

#                     send_to_backend(
#                         results
#                     )

#                     # ----------------------------------------
#                     # Console
#                     # ----------------------------------------

#                     print_phase_summary(
#                         phase_number,
#                         phase_start,
#                         phase_end,
#                         detections,
#                         results
#                     )

#                     processed_lines += 1

#             # ------------------------------------------------
#             # Wait for next phase
#             # ------------------------------------------------

#             time.sleep(
#                 poll_seconds
#             )

#     except KeyboardInterrupt:

#         print()
#         print(
#             "Person 2 real-time processing stopped."
#         )


# # ============================================================
# # OFFLINE MODE
# # ============================================================

# def process_offline(
#     detections_path,
#     roi,
#     output,
#     window_seconds,
#     road_id_override=None,
#     road_name_override=None
# ):

#     detections = load_detections(
#         detections_path
#     )

#     results = analyze(
#         detections=detections,
#         roi=roi,
#         window_seconds=window_seconds,
#         road_id_override=road_id_override,
#         road_name_override=road_name_override
#     )

#     save_complete_analysis(
#         results,
#         output
#     )

#     send_to_backend(
#         results
#     )

#     print()
#     print("=" * 70)
#     print("LANELOGIC - PERSON 2 ANALYSIS")
#     print("=" * 70)

#     print(
#         f"Detections: {len(detections)}"
#     )

#     print(
#         f"Windows   : {len(results)}"
#     )

#     print(
#         f"Output    : {output}"
#     )

#     print("-" * 70)

#     for result in results[:10]:

#         print(
#             f"Window {result['window_index']:>3} | "
#             f"Vehicles: {result['vehicle_count']:>2} | "
#             f"Occupancy: "
#             f"{result['occupancy_pct']:>6.2f}% | "
#             f"Blocked: "
#             f"{result['blocked_pct']:>6.2f}% | "
#             f"Priority: "
#             f"{result['severity']:<9} | "
#             f"Cause: "
#             f"{result['cause']}"
#         )

#     print("=" * 70)


# # ============================================================
# # COMMAND LINE
# # ============================================================

# def main():

#     parser = argparse.ArgumentParser(
#         description=(
#             "LaneLogic Person 2 - "
#             "Space & Cause Analysis"
#         )
#     )

#     # --------------------------------------------------------
#     # Normal/offline detections input
#     # --------------------------------------------------------

#     parser.add_argument(
#         "--detections",
#         default=(
#             "../person1_detection/"
#             "output/detections.json"
#         ),
#         help=(
#             "Path to Person 1 complete detections JSON."
#         )
#     )

#     # --------------------------------------------------------
#     # Real-time phase input
#     # --------------------------------------------------------

#     parser.add_argument(
#         "--phase-input",
#         default=None,
#         help=(
#             "Path to Person 1 detection_stream.jsonl "
#             "for real-time phase processing."
#         )
#     )

#     # --------------------------------------------------------
#     # ROI
#     # --------------------------------------------------------

#     parser.add_argument(
#         "--roi",
#         default="roi_config.json",
#         help="Path to roi_config.json"
#     )

#     # --------------------------------------------------------
#     # Final complete analysis
#     # --------------------------------------------------------

#     parser.add_argument(
#         "--output",
#         default="analysis.json",
#         help=(
#             "Path to complete analysis JSON."
#         )
#     )

#     # --------------------------------------------------------
#     # Phase analysis output
#     # --------------------------------------------------------

#     parser.add_argument(
#         "--phase-output",
#         default="analysis_stream.jsonl",
#         help=(
#             "Path to phase-wise analysis JSONL."
#         )
#     )

#     # --------------------------------------------------------
#     # Analysis window
#     # --------------------------------------------------------

#     parser.add_argument(
#         "--window-seconds",
#         type=int,
#         default=DEFAULT_WINDOW_SECONDS,
#         help=(
#             "Analysis window size in seconds."
#         )
#     )

#     # --------------------------------------------------------
#     # Polling interval
#     # --------------------------------------------------------

#     parser.add_argument(
#         "--poll-seconds",
#         type=float,
#         default=DEFAULT_PHASE_POLL_SECONDS,
#         help=(
#             "How often Person 2 checks for new phases."
#         )
#     )

#     # --------------------------------------------------------
#     # Road identity
#     # --------------------------------------------------------

#     parser.add_argument(
#         "--road-id",
#         default=None,
#         help=(
#             "Override road ID, e.g. ROAD_001"
#         )
#     )

#     parser.add_argument(
#         "--road-name",
#         default=None,
#         help=(
#             "Override road name, e.g. Traffic 1"
#         )
#     )

#     args = parser.parse_args()

#     # --------------------------------------------------------
#     # Load ROI
#     # --------------------------------------------------------

#     roi = load_roi(
#         args.roi
#     )

#     # ========================================================
#     # REAL-TIME MODE
#     # ========================================================

#     if args.phase_input:

#         process_phase_stream(
#             phase_input=args.phase_input,
#             roi=roi,
#             output=args.output,
#             phase_output=args.phase_output,
#             window_seconds=args.window_seconds,
#             road_id_override=args.road_id,
#             road_name_override=args.road_name,
#             poll_seconds=args.poll_seconds
#         )

#         return

#     # ========================================================
#     # OFFLINE MODE
#     # ========================================================

#     process_offline(
#         detections_path=args.detections,
#         roi=roi,
#         output=args.output,
#         window_seconds=args.window_seconds,
#         road_id_override=args.road_id,
#         road_name_override=args.road_name
#     )


# # ============================================================
# # ENTRY POINT
# # ============================================================

# if __name__ == "__main__":

#     main()














import argparse
import json
import time
from pathlib import Path
from collections import defaultdict
from datetime import datetime

import requests
from shapely.geometry import Polygon, box


# ============================================================
# CONFIG
# ============================================================

DEFAULT_WINDOW_SECONDS = 2
DEFAULT_POLL_SECONDS = 0.5

BACKEND_URL = "http://localhost:8000"

OCCUPANCY_THRESHOLDS = {
    "low": 20,
    "moderate": 40,
    "high": 60,
    "critical": 80,
}

BLOCKED_THRESHOLDS = {
    "low": 10,
    "moderate": 25,
    "high": 40,
    "critical": 60,
}


# ============================================================
# ROI
# ============================================================

def load_roi(path):

    with open(
        path,
        "r",
        encoding="utf-8",
    ) as f:

        config = json.load(f)

    if "road_polygon" not in config:

        raise ValueError(
            "roi_config.json must contain "
            "'road_polygon'"
        )

    road_polygon = config[
        "road_polygon"
    ]

    result = dict(config)

    # --------------------------------------------------------
    # Road polygon
    # --------------------------------------------------------

    result["_road_polygon_shape"] = Polygon(
        road_polygon
    )

    # --------------------------------------------------------
    # Signal / queue zone
    #
    # Supports:
    # {
    #   "signal_queue_zone": {
    #       "comment": "...",
    #       "polygon": [...]
    #   }
    # }
    #
    # and also a direct polygon list.
    # --------------------------------------------------------

    queue_zone = result.get(
        "signal_queue_zone"
    )

    if queue_zone:

        if isinstance(
            queue_zone,
            dict
        ):

            queue_polygon = queue_zone.get(
                "polygon",
                []
            )

        else:

            queue_polygon = queue_zone

        if queue_polygon:

            result[
                "_queue_zone_shape"
            ] = Polygon(
                queue_polygon
            )

        else:

            result[
                "_queue_zone_shape"
            ] = None

    else:

        result[
            "_queue_zone_shape"
        ] = None

    # IMPORTANT:
    # load_roi() must return the processed
    # configuration.
    return result


# ============================================================
# INPUT
# ============================================================

def load_detections(path):

    with open(
        path,
        "r",
        encoding="utf-8",
    ) as f:

        data = json.load(f)

    if not isinstance(
        data,
        list
    ):

        raise ValueError(
            "detections.json must contain "
            "a list"
        )

    return data


# ============================================================
# WINDOWING
# ============================================================

def group_into_windows(
    detections,
    window_seconds,
):

    windows = defaultdict(list)

    for detection in detections:

        timestamp = float(
            detection.get(
                "timestamp",
                0,
            )
        )

        window_index = int(
            timestamp
            // window_seconds
        )

        windows[
            window_index
        ].append(
            detection
        )

    return windows


# ============================================================
# ROI AREA
# ============================================================

def vehicle_box_area_inside_roi(
    bbox,
    road_polygon,
):

    x1, y1, x2, y2 = bbox

    vehicle_shape = box(
        x1,
        y1,
        x2,
        y2,
    )

    intersection = (
        vehicle_shape.intersection(
            road_polygon
        )
    )

    return intersection.area


def is_inside_queue_zone(
    position,
    queue_zone,
):

    if queue_zone is None:

        return False

    x, y = position

    return queue_zone.covers(
        box(
            x,
            y,
            x,
            y,
        )
    )


# ============================================================
# SCHOOL HOURS
# ============================================================

def in_school_hours(
    hour,
    config,
):

    # Your roi_config.json uses:
    # "school_zone_active_hours"
    #
    # Keep compatibility with the older:
    # "school_hours"

    school_config = config.get(
        "school_zone_active_hours"
    )

    if not school_config:

        school_config = config.get(
            "school_hours"
        )

    if not school_config:

        return False

    start = school_config.get(
        "start",
        "07:30",
    )

    end = school_config.get(
        "end",
        "09:00",
    )

    # --------------------------------------------------------
    # Handle HH:MM strings
    # --------------------------------------------------------

    if isinstance(
        start,
        str
    ):

        try:

            start_hour = int(
                start.split(":")[0]
            )

            start_minute = int(
                start.split(":")[1]
            )

            start_value = (
                start_hour
                + start_minute / 60
            )

        except (
            ValueError,
            IndexError,
        ):

            start_value = 7.5

    else:

        start_value = float(
            start
        )

    if isinstance(
        end,
        str
    ):

        try:

            end_hour = int(
                end.split(":")[0]
            )

            end_minute = int(
                end.split(":")[1]
            )

            end_value = (
                end_hour
                + end_minute / 60
            )

        except (
            ValueError,
            IndexError,
        ):

            end_value = 9.0

    else:

        end_value = float(
            end
        )

    return (
        start_value
        <= hour
        < end_value
    )


# ============================================================
# SEVERITY
# ============================================================

def calculate_severity(
    occupancy_pct,
    blocked_pct,
):

    occupancy_score = 0

    if (
        occupancy_pct
        >= OCCUPANCY_THRESHOLDS[
            "critical"
        ]
    ):

        occupancy_score = 4

    elif (
        occupancy_pct
        >= OCCUPANCY_THRESHOLDS[
            "high"
        ]
    ):

        occupancy_score = 3

    elif (
        occupancy_pct
        >= OCCUPANCY_THRESHOLDS[
            "moderate"
        ]
    ):

        occupancy_score = 2

    elif (
        occupancy_pct
        >= OCCUPANCY_THRESHOLDS[
            "low"
        ]
    ):

        occupancy_score = 1

    blocked_score = 0

    if (
        blocked_pct
        >= BLOCKED_THRESHOLDS[
            "critical"
        ]
    ):

        blocked_score = 4

    elif (
        blocked_pct
        >= BLOCKED_THRESHOLDS[
            "high"
        ]
    ):

        blocked_score = 3

    elif (
        blocked_pct
        >= BLOCKED_THRESHOLDS[
            "moderate"
        ]
    ):

        blocked_score = 2

    elif (
        blocked_pct
        >= BLOCKED_THRESHOLDS[
            "low"
        ]
    ):

        blocked_score = 1

    score = max(
        occupancy_score,
        blocked_score,
    )

    names = {
        0: "normal",
        1: "low",
        2: "moderate",
        3: "high",
        4: "critical",
    }

    return (
        names[score],
        score,
    )


# ============================================================
# CAUSE
# ============================================================

def classify_cause(
    records,
    occupancy_pct,
    blocked_pct,
    config,
    window_start_seconds,
):

    if occupancy_pct < 20:

        return (
            "normal",
            "Low road-space occupancy; "
            "no significant blockage detected.",
        )

    queue_count = 0
    parked_outside_queue = 0
    loading_count = 0
    school_stopped = 0
    small_stopped = 0

    for record in records:

        state = record.get(
            "movement_state",
            "unknown",
        )

        if state not in (
            "signal_waiting",
            "parked",
        ):

            continue

        position = record.get(
            "position",
            [0, 0],
        )

        # ----------------------------------------------------
        # Queue
        # ----------------------------------------------------

        if (
            state
            == "signal_waiting"
            and record.get(
                "in_waiting_zone",
                False,
            )
        ):

            queue_count += 1

        # ----------------------------------------------------
        # Parked outside queue
        # ----------------------------------------------------

        if (
            state == "parked"
            and not record.get(
                "in_waiting_zone",
                False,
            )
        ):

            parked_outside_queue += 1

        vehicle_type = record.get(
            "vehicle_type",
            "",
        )

        # ----------------------------------------------------
        # Loading / unloading
        # ----------------------------------------------------

        if (
            state == "parked"
            and vehicle_type in (
                "truck",
                "bus",
            )
        ):

            loading_count += 1

        # ----------------------------------------------------
        # Small vehicles
        # ----------------------------------------------------

        if vehicle_type in (
            "car",
            "motorcycle",
            "bicycle",
        ):

            small_stopped += 1

    hour = int(
        window_start_seconds
        // 3600
    ) % 24

    # --------------------------------------------------------
    # Traffic signal queue
    # --------------------------------------------------------

    if (
        queue_count >= 3
        and blocked_pct >= 10
    ):

        return (
            "traffic_signal_queue",
            "Multiple stationary vehicles "
            "detected near the configured "
            "signal/queue zone.",
        )

    # --------------------------------------------------------
    # Loading / unloading
    # --------------------------------------------------------

    if (
        loading_count >= 1
        and parked_outside_queue <= 3
    ):

        return (
            "loading_unloading",
            "Truck/bus stopping pattern "
            "suggests possible loading or "
            "unloading activity.",
        )

    # --------------------------------------------------------
    # School drop-off
    # --------------------------------------------------------

    if (
        in_school_hours(
            hour,
            config,
        )
        and small_stopped >= 3
    ):

        return (
            "school_dropoff",
            "Multiple small vehicles are "
            "stopped during the configured "
            "school-hour period.",
        )

    # --------------------------------------------------------
    # Multiple parked vehicles
    # --------------------------------------------------------

    if parked_outside_queue >= 3:

        return (
            "illegal_parking",
            f"{parked_outside_queue} vehicle(s) "
            "marked as parked outside the "
            "signal/queue zone.",
        )

    # --------------------------------------------------------
    # General congestion
    # --------------------------------------------------------

    if (
        blocked_pct < 10
        and occupancy_pct >= 40
    ):

        return (
            "general_congestion",
            "Road occupancy is elevated "
            "without a strong obstruction "
            "pattern.",
        )

    # --------------------------------------------------------
    # Single parked vehicle
    # --------------------------------------------------------

    if parked_outside_queue == 1:

        return (
            "illegal_parking",
            "1 vehicle marked as parked "
            "outside the signal/queue zone. "
            "Further verification is recommended.",
        )

    return (
        "unclassified",
        "Road-space occupancy is elevated, "
        "but the available vehicle states "
        "and configured zones do not identify "
        "a specific cause.",
    )


# ============================================================
# BREAKDOWNS
# ============================================================

def type_breakdown(records):

    result = defaultdict(int)

    for record in records:

        result[
            record.get(
                "vehicle_type",
                "unknown",
            )
        ] += 1

    return dict(result)


def state_breakdown(records):

    result = {
        "moving": 0,
        "signal_waiting": 0,
        "parked": 0,
        "unknown": 0,
    }

    for record in records:

        state = record.get(
            "movement_state",
            "unknown",
        )

        if state not in result:

            state = "unknown"

        result[state] += 1

    return result


# ============================================================
# ANALYSIS
# ============================================================

def analyze(
    detections,
    roi_config,
    window_seconds,
    road_id,
    road_name,
):

    windows = group_into_windows(
        detections,
        window_seconds,
    )

    road_polygon = roi_config[
        "_road_polygon_shape"
    ]

    queue_zone = roi_config[
        "_queue_zone_shape"
    ]

    road_length = roi_config.get(
        "road_length_meters"
    )

    road_width = roi_config.get(
        "road_width_meters"
    )

    results = []

    for window_index in sorted(
        windows.keys()
    ):

        records = windows[
            window_index
        ]

        # ----------------------------------------------------
        # Keep latest observation per vehicle
        # ----------------------------------------------------

        latest = {}

        for record in records:

            vehicle_id = record.get(
                "vehicle_id"
            )

            timestamp = float(
                record.get(
                    "timestamp",
                    0,
                )
            )

            if (
                vehicle_id not in latest
                or timestamp
                > float(
                    latest[
                        vehicle_id
                    ].get(
                        "timestamp",
                        0,
                    )
                )
            ):

                latest[
                    vehicle_id
                ] = record

        records = list(
            latest.values()
        )

        # ----------------------------------------------------
        # Calculate areas
        # ----------------------------------------------------

        total_area = 0.0
        blocked_area = 0.0

        for record in records:

            bbox = record.get(
                "bbox",
                [0, 0, 0, 0],
            )

            inside_area = (
                vehicle_box_area_inside_roi(
                    bbox,
                    road_polygon,
                )
            )

            total_area += inside_area

            if record.get(
                "movement_state"
            ) == "parked":

                blocked_area += (
                    inside_area
                )

        # ----------------------------------------------------
        # Road physical area
        # ----------------------------------------------------

        road_area = (
            road_length
            * road_width
            if road_length
            and road_width
            else 0
        )

        # ----------------------------------------------------
        # Occupancy
        # ----------------------------------------------------

        if road_area > 0:

            occupancy_pct = min(
                100,
                (
                    total_area
                    / road_area
                )
                * 100,
            )

            blocked_pct = min(
                100,
                (
                    blocked_area
                    / road_area
                )
                * 100,
            )

        else:

            occupancy_pct = 0.0
            blocked_pct = 0.0

        # ----------------------------------------------------
        # Severity
        # ----------------------------------------------------

        severity, priority = (
            calculate_severity(
                occupancy_pct,
                blocked_pct,
            )
        )

        # ----------------------------------------------------
        # Cause
        # ----------------------------------------------------

        cause, explanation = (
            classify_cause(
                records,
                occupancy_pct,
                blocked_pct,
                roi_config,
                window_index
                * window_seconds,
            )
        )

        # ----------------------------------------------------
        # Physical estimates
        # ----------------------------------------------------

        occupied_area_m2 = 0.0
        blocked_area_m2 = 0.0

        if road_area > 0:

            occupied_area_m2 = (
                occupancy_pct
                / 100
                * road_area
            )

            blocked_area_m2 = (
                blocked_pct
                / 100
                * road_area
            )

        equivalent_occupied_width = 0.0
        equivalent_blocked_width = 0.0

        if (
            road_length
            and road_length > 0
        ):

            equivalent_occupied_width = (
                occupied_area_m2
                / road_length
            )

            equivalent_blocked_width = (
                blocked_area_m2
                / road_length
            )

        # ----------------------------------------------------
        # Window times
        # ----------------------------------------------------

        window_start = (
            window_index
            * window_seconds
        )

        window_end = (
            window_start
            + window_seconds
        )

        # ----------------------------------------------------
        # Final result
        # ----------------------------------------------------

        result = {
            "road_id": road_id,

            "road_name": road_name,

            "window_index": (
                window_index
            ),

            "window_start_seconds": (
                window_start
            ),

            "window_end_seconds": (
                window_end
            ),

            "vehicle_count": len(
                records
            ),

            "vehicle_type_breakdown": (
                type_breakdown(records)
            ),

            "movement_state_breakdown": (
                state_breakdown(records)
            ),

            "road_length_meters": (
                road_length
            ),

            "road_width_meters": (
                road_width
            ),

            "road_area_m2": road_area,

            "occupancy_pct": round(
                occupancy_pct,
                2,
            ),

            "blocked_pct": round(
                blocked_pct,
                2,
            ),

            "occupied_area_m2": round(
                occupied_area_m2,
                2,
            ),

            "blocked_area_m2": round(
                blocked_area_m2,
                2,
            ),

            "equivalent_occupied_width_meters": (
                round(
                    equivalent_occupied_width,
                    2,
                )
            ),

            "equivalent_blocked_width_meters": (
                round(
                    equivalent_blocked_width,
                    2,
                )
            ),

            "severity": severity,

            "priority_score": priority,

            "cause": cause,

            "cause_explanation": explanation,
        }

        results.append(
            result
        )

    return results


# ============================================================
# BACKEND
# ============================================================

def send_to_backend(
    results,
    backend_url,
):

    if not results:
        return

    try:

        response = requests.post(
            f"{backend_url}/analysis/bulk",
            json={
                "observations": results
            },
            timeout=5,
        )

        response.raise_for_status()

        print(
            "✓ Sent analysis to "
            "Person 3 backend"
        )

    except requests.RequestException as e:

        print(
            "✗ Could not connect to "
            "Person 3 backend: "
            f"{e}"
        )


# ============================================================
# SAVE PHASE
# ============================================================

def save_phase_output(
    path,
    payload,
):

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(
        path,
        "a",
        encoding="utf-8",
    ) as f:

        f.write(
            json.dumps(
                payload
            )
            + "\n"
        )


# ============================================================
# PROCESS ONE VIDEO
# ============================================================

def process_video(
    phase_input,
    roi_config,
    analysis_output,
    phase_output,
    window_seconds,
    backend_url,
    road_id,
    road_name,
):

    processed_phases = set()

    all_analysis = []

    print(
        "\n============================================================"
    )

    print(
        "PERSON 2"
    )

    print(
        f"Road: {road_id}"
    )

    print(
        f"Name: {road_name}"
    )

    print(
        f"Input: {phase_input}"
    )

    print(
        "============================================================"
    )

    # --------------------------------------------------------
    # Start clean for this video's analysis output.
    # --------------------------------------------------------

    if phase_output.exists():

        phase_output.unlink()

    last_line_count = 0

    while True:

        if not phase_input.exists():

            time.sleep(
                DEFAULT_POLL_SECONDS
            )

            continue

        try:

            with open(
                phase_input,
                "r",
                encoding="utf-8",
            ) as f:

                lines = f.readlines()

        except OSError:

            time.sleep(
                DEFAULT_POLL_SECONDS
            )

            continue

        # ----------------------------------------------------
        # File was recreated.
        # ----------------------------------------------------

        if (
            len(lines)
            < last_line_count
        ):

            processed_phases.clear()

            last_line_count = 0

        last_line_count = len(
            lines
        )

        # ----------------------------------------------------
        # Process new phases
        # ----------------------------------------------------

        for line in lines:

            line = line.strip()

            if not line:
                continue

            try:

                phase = json.loads(
                    line
                )

            except json.JSONDecodeError:

                continue

            phase_id = phase.get(
                "phase_id"
            )

            if not phase_id:

                phase_id = (
                    f"{phase.get('road_id', road_id)}"
                    f"_PHASE_"
                    f"{phase.get('phase', 0)}"
                )

            if (
                phase_id
                in processed_phases
            ):

                continue

            phase_road_id = phase.get(
                "road_id",
                road_id,
            )

            if (
                phase_road_id
                != road_id
            ):

                continue

            processed_phases.add(
                phase_id
            )

            print(
                f"\n→ New Phase "
                f"{phase.get('phase')} "
                f"received"
            )

            observations = phase.get(
                "observations",
                [],
            )

            if not observations:

                print(
                    "  Phase contains "
                    "no observations."
                )

                continue

            # ------------------------------------------------
            # Analyze this phase
            # ------------------------------------------------

            results = analyze(
                observations,
                roi_config,
                window_seconds,
                road_id,
                road_name,
            )

            phase_start = phase.get(
                "start_time",
                0,
            )

            phase_end = phase.get(
                "end_time",
                0,
            )

            # ------------------------------------------------
            # Add phase metadata
            # ------------------------------------------------

            for result in results:

                result[
                    "phase"
                ] = phase.get(
                    "phase"
                )

                result[
                    "phase_start_seconds"
                ] = phase_start

                result[
                    "phase_end_seconds"
                ] = phase_end

                result[
                    "phase_id"
                ] = phase_id

                result[
                    "source"
                ] = phase.get(
                    "source",
                    "",
                )

            # ------------------------------------------------
            # Store all analysis
            # ------------------------------------------------

            all_analysis.extend(
                results
            )

            # ------------------------------------------------
            # Save phase stream
            # ------------------------------------------------

            payload = {
                "phase_id": phase_id,

                "phase": phase.get(
                    "phase"
                ),

                "road_id": road_id,

                "road_name": road_name,

                "source": phase.get(
                    "source",
                    "",
                ),

                "start_time": phase_start,

                "end_time": phase_end,

                "record_count": len(
                    results
                ),

                "observations": results,
            }

            save_phase_output(
                phase_output,
                payload,
            )

            # ------------------------------------------------
            # Send to backend
            # ------------------------------------------------

            send_to_backend(
                results,
                backend_url,
            )

            print(
                f"✓ Phase "
                f"{phase.get('phase')} "
                f"analysed: "
                f"{len(results)} windows"
            )

        # ----------------------------------------------------
        # Person 1 creates .done when video finishes.
        # ----------------------------------------------------

        done_file = (
            phase_input.with_suffix(
                ".done"
            )
        )

        if done_file.exists():

            remaining_new = False

            for line in lines:

                line = line.strip()

                if not line:
                    continue

                try:

                    phase = json.loads(
                        line
                    )

                except json.JSONDecodeError:

                    continue

                phase_id = phase.get(
                    "phase_id"
                )

                if not phase_id:
                    continue

                if (
                    phase_id
                    in processed_phases
                ):
                    continue

                if (
                    phase.get(
                        "road_id"
                    )
                    != road_id
                ):
                    continue

                remaining_new = True
                break

            if not remaining_new:

                break

        time.sleep(
            DEFAULT_POLL_SECONDS
        )

    # --------------------------------------------------------
    # Final analysis file
    # --------------------------------------------------------

    analysis_output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(
        analysis_output,
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            all_analysis,
            f,
            indent=2,
        )

    print(
        "\n✓ Video analysis completed"
    )

    print(
        f"Analysis: {analysis_output}"
    )

    print(
        f"Total analysis windows: "
        f"{len(all_analysis)}"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--phase-input",
        required=True,
    )

    parser.add_argument(
        "--roi",
        default="roi_config.json",
    )

    parser.add_argument(
        "--output",
        required=True,
    )

    parser.add_argument(
        "--phase-output",
        required=True,
    )

    parser.add_argument(
        "--window-seconds",
        type=float,
        default=DEFAULT_WINDOW_SECONDS,
    )

    parser.add_argument(
        "--backend-url",
        default=BACKEND_URL,
    )

    parser.add_argument(
        "--road-id",
        required=True,
    )

    parser.add_argument(
        "--road-name",
        required=True,
    )

    args = parser.parse_args()

    # --------------------------------------------------------
    # Load ROI
    # --------------------------------------------------------

    roi_config = load_roi(
        args.roi
    )

    # --------------------------------------------------------
    # Process video
    # --------------------------------------------------------

    process_video(
        Path(
            args.phase_input
        ),

        roi_config,

        Path(
            args.output
        ),

        Path(
            args.phase_output
        ),

        args.window_seconds,

        args.backend_url,

        args.road_id,

        args.road_name,
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()