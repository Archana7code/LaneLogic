
# import argparse
# import csv
# import json
# import math
# import time
# from collections import Counter, deque
# from pathlib import Path

# import cv2
# import torch
# from ultralytics import YOLO


# # =====================================================================
# # PERSON 1 — VEHICLE DETECTION, TRACKING & SMART STOP DETECTION
# # LaneLogic / SIH 2026
# # =====================================================================

# BASE_DIR = Path(__file__).resolve().parent


# # =====================================================================
# # DEFAULT CONFIGURATION
# # =====================================================================

# # COCO vehicle classes
# VEHICLE_CLASS_IDS = {
#     1: "bicycle",
#     2: "car",
#     3: "motorcycle",
#     5: "bus",
#     7: "truck",
# }


# # =====================================================================
# # DETECTION
# # =====================================================================

# DEFAULT_MODEL = "yolov8s.pt"
# DEFAULT_CONFIDENCE = 0.40
# DEFAULT_IOU = 0.50
# DEFAULT_IMAGE_SIZE = 640


# # =====================================================================
# # TRACKING
# # =====================================================================

# TRACK_BUFFER = 120
# TRACK_HIGH_THRESH = 0.60
# TRACK_LOW_THRESH = 0.10
# NEW_TRACK_THRESH = 0.70
# MATCH_THRESH = 0.80


# # =====================================================================
# # MOVEMENT ANALYSIS
# # =====================================================================

# POSITION_HISTORY_SECONDS = 2.0
# STOP_MOVEMENT_RATIO = 0.25


# # =====================================================================
# # VEHICLE STATE
# # =====================================================================

# # Traffic-signal waiting
# WAITING_TIME_THRESHOLD_SECONDS = 3.0

# # IMPORTANT:
# # Parked threshold is EXACTLY 5 seconds.
# PARKED_TIME_THRESHOLD_SECONDS = 5.0

# # No additional confirmation delay.
# PARKED_CONFIRMATION_SECONDS = 0.0


# # =====================================================================
# # CLASS SMOOTHING
# # =====================================================================

# CLASS_HISTORY_LENGTH = 15


# # =====================================================================
# # DUPLICATE FILTERING
# # =====================================================================

# DUPLICATE_IOU_THRESHOLD = 0.60


# # =====================================================================
# # ROAD
# # =====================================================================

# ROAD_ID = "ROAD_001"


# # =====================================================================
# # ZONES
# # =====================================================================

# # Set these according to the actual video if needed.
# #
# # WAITING_ZONE:
# #   Traffic signal / stop-line region.
# #
# # PARKING_ZONE:
# #   Actual parking/loading area.
# #
# # If WAITING_ZONE is None:
# #   stationary vehicles are not specifically identified
# #   as signal waiting based on location.
# #
# # If PARKING_ZONE is None:
# #   stationary vehicles can become parked after 5 seconds,
# #   provided they are not inside WAITING_ZONE.
# #
# # Example:
# #
# # WAITING_ZONE = [300, 150, 650, 300]
# # PARKING_ZONE = [700, 250, 950, 520]

# WAITING_ZONE = None
# PARKING_ZONE = None


# # =====================================================================
# # HELPER FUNCTIONS
# # =====================================================================

# def get_center(bbox):
#     x1, y1, x2, y2 = bbox

#     return (
#         (x1 + x2) / 2.0,
#         (y1 + y2) / 2.0
#     )


# def pixel_distance(point_a, point_b):
#     return math.hypot(
#         point_a[0] - point_b[0],
#         point_a[1] - point_b[1]
#     )


# def bbox_height(bbox):
#     x1, y1, x2, y2 = bbox

#     return max(
#         1.0,
#         y2 - y1
#     )


# def normalized_movement(
#     previous_position,
#     current_position,
#     bbox
# ):
#     """
#     Normalize movement using vehicle bounding-box height.
#     """

#     movement = pixel_distance(
#         previous_position,
#         current_position
#     )

#     return movement / bbox_height(bbox)


# def point_inside_zone(point, zone):

#     if zone is None:
#         return False

#     x, y = point

#     x1, y1, x2, y2 = zone

#     return (
#         x1 <= x <= x2
#         and
#         y1 <= y <= y2
#     )


# def calculate_iou(box_a, box_b):

#     xa1, ya1, xa2, ya2 = box_a
#     xb1, yb1, xb2, yb2 = box_b

#     inter_x1 = max(xa1, xb1)
#     inter_y1 = max(ya1, yb1)

#     inter_x2 = min(xa2, xb2)
#     inter_y2 = min(ya2, yb2)

#     inter_width = max(
#         0.0,
#         inter_x2 - inter_x1
#     )

#     inter_height = max(
#         0.0,
#         inter_y2 - inter_y1
#     )

#     intersection = (
#         inter_width *
#         inter_height
#     )

#     area_a = (
#         max(0.0, xa2 - xa1) *
#         max(0.0, ya2 - ya1)
#     )

#     area_b = (
#         max(0.0, xb2 - xb1) *
#         max(0.0, yb2 - yb1)
#     )

#     union = (
#         area_a +
#         area_b -
#         intersection
#     )

#     if union <= 0:
#         return 0.0

#     return intersection / union


# # =====================================================================
# # TRACK STATE
# # =====================================================================

# class TrackState:

#     def __init__(
#         self,
#         track_id,
#         vehicle_type
#     ):

#         self.track_id = track_id

#         self.vehicle_type = vehicle_type

#         self.centers = deque(
#             maxlen=60
#         )

#         self.timestamps = deque(
#             maxlen=60
#         )

#         self.stationary_since = None

#         self.last_seen_frame = -1

#         self.class_history = deque(
#             maxlen=CLASS_HISTORY_LENGTH
#         )

#         self.status = "moving"

#         self.last_movement_ratio = None

#         self.last_seen_timestamp = 0.0


#     def update(
#         self,
#         center,
#         timestamp,
#         bbox
#     ):

#         self.centers.append(center)

#         self.timestamps.append(timestamp)

#         self.last_seen_timestamp = timestamp

#         movement_ratio = None

#         # -------------------------------------------------------------
#         # Determine movement using short history
#         # -------------------------------------------------------------

#         if len(self.centers) >= 2:

#             old_position = self.centers[0]

#             old_timestamp = self.timestamps[0]

#             time_difference = (
#                 timestamp -
#                 old_timestamp
#             )

#             if time_difference > 0.5:

#                 movement_ratio = normalized_movement(
#                     old_position,
#                     center,
#                     bbox
#                 )

#         self.last_movement_ratio = movement_ratio

#         # IMPORTANT:
#         # If movement_ratio is unavailable, vehicle is NOT considered
#         # stationary.
#         is_stationary = (
#             movement_ratio is not None
#             and
#             movement_ratio < STOP_MOVEMENT_RATIO
#         )

#         if is_stationary:

#             if self.stationary_since is None:

#                 self.stationary_since = timestamp

#         else:

#             self.stationary_since = None

#             self.status = "moving"

#         return self.stationary_duration(
#             timestamp
#         )


#     def stationary_duration(
#         self,
#         timestamp
#     ):

#         if self.stationary_since is None:

#             return 0.0

#         return max(
#             0.0,
#             timestamp -
#             self.stationary_since
#         )


# # =====================================================================
# # VEHICLE DETECTOR / TRACKER
# # =====================================================================

# class VehicleDetectorTracker:

#     def __init__(
#         self,
#         model_path,
#         confidence
#     ):

#         print(
#             f"[Person1] Loading model: {model_path}"
#         )

#         self.model = YOLO(
#             model_path
#         )

#         self.confidence = confidence

#         self.tracks = {}

#         self.seen_ids = set()


#     # -----------------------------------------------------------------
#     # Duplicate removal
#     # -----------------------------------------------------------------

#     def deduplicate_boxes(
#         self,
#         boxes,
#         confidences,
#         class_ids,
#         track_ids
#     ):

#         if len(boxes) <= 1:

#             return (
#                 boxes,
#                 confidences,
#                 class_ids,
#                 track_ids
#             )

#         keep = [True] * len(boxes)

#         order = sorted(
#             range(len(boxes)),
#             key=lambda i: confidences[i],
#             reverse=True
#         )

#         for a in range(
#             len(order)
#         ):

#             i = order[a]

#             if not keep[i]:
#                 continue

#             for b in range(
#                 a + 1,
#                 len(order)
#             ):

#                 j = order[b]

#                 if not keep[j]:
#                     continue

#                 overlap = calculate_iou(
#                     boxes[i],
#                     boxes[j]
#                 )

#                 if (
#                     overlap >=
#                     DUPLICATE_IOU_THRESHOLD
#                 ):

#                     keep[j] = False

#         return (
#             [
#                 box
#                 for box, flag
#                 in zip(boxes, keep)
#                 if flag
#             ],

#             [
#                 c
#                 for c, flag
#                 in zip(confidences, keep)
#                 if flag
#             ],

#             [
#                 c
#                 for c, flag
#                 in zip(class_ids, keep)
#                 if flag
#             ],

#             [
#                 t
#                 for t, flag
#                 in zip(track_ids, keep)
#                 if flag
#             ]
#         )


#     # -----------------------------------------------------------------
#     # Process one frame
#     # -----------------------------------------------------------------

#     def process_frame(
#         self,
#         frame,
#         frame_index,
#         timestamp
#     ):

#         results = self.model.track(
#             frame,
#             persist=True,
#             tracker="bytetrack.yaml",
#             classes=list(
#                 VEHICLE_CLASS_IDS.keys()
#             ),
#             conf=self.confidence,
#             iou=DEFAULT_IOU,
#             imgsz=DEFAULT_IMAGE_SIZE,
#             half=torch.cuda.is_available(),
#             verbose=False
#         )

#         records = []

#         if not results:
#             return records

#         result = results[0]

#         if (
#             result.boxes is None
#             or
#             result.boxes.id is None
#         ):
#             return records

#         boxes = (
#             result.boxes.xyxy
#             .cpu()
#             .numpy()
#             .tolist()
#         )

#         confidences = (
#             result.boxes.conf
#             .cpu()
#             .numpy()
#             .tolist()
#         )

#         class_ids = (
#             result.boxes.cls
#             .cpu()
#             .numpy()
#             .astype(int)
#             .tolist()
#         )

#         track_ids = (
#             result.boxes.id
#             .cpu()
#             .numpy()
#             .astype(int)
#             .tolist()
#         )

#         (
#             boxes,
#             confidences,
#             class_ids,
#             track_ids
#         ) = self.deduplicate_boxes(
#             boxes,
#             confidences,
#             class_ids,
#             track_ids
#         )

#         processed_ids = set()

#         for (
#             bbox,
#             confidence,
#             class_id,
#             track_id
#         ) in zip(
#             boxes,
#             confidences,
#             class_ids,
#             track_ids
#         ):

#             if (
#                 class_id
#                 not in VEHICLE_CLASS_IDS
#             ):
#                 continue

#             if track_id in processed_ids:
#                 continue

#             processed_ids.add(track_id)

#             x1, y1, x2, y2 = bbox

#             center = get_center(
#                 bbox
#             )

#             vehicle_type = (
#                 VEHICLE_CLASS_IDS[
#                     class_id
#                 ]
#             )

#             # ---------------------------------------------------------
#             # Create track if new
#             # ---------------------------------------------------------

#             if track_id not in self.tracks:

#                 self.tracks[track_id] = (
#                     TrackState(
#                         track_id,
#                         vehicle_type
#                     )
#                 )

#             track = self.tracks[
#                 track_id
#             ]

#             track.last_seen_frame = (
#                 frame_index
#             )

#             track.class_history.append(
#                 class_id
#             )

#             # ---------------------------------------------------------
#             # Stable class voting
#             # ---------------------------------------------------------

#             stable_class_id = Counter(
#                 track.class_history
#             ).most_common(1)[0][0]

#             stable_vehicle_type = (
#                 VEHICLE_CLASS_IDS[
#                     stable_class_id
#                 ]
#             )

#             track.vehicle_type = (
#                 stable_vehicle_type
#             )

#             # ---------------------------------------------------------
#             # Movement
#             # ---------------------------------------------------------

#             stationary_duration = (
#                 track.update(
#                     center,
#                     timestamp,
#                     bbox
#                 )
#             )

#             # ---------------------------------------------------------
#             # Zones
#             # ---------------------------------------------------------

#             in_waiting_zone = (
#                 point_inside_zone(
#                     center,
#                     WAITING_ZONE
#                 )
#             )

#             in_parking_zone = (
#                 point_inside_zone(
#                     center,
#                     PARKING_ZONE
#                 )
#             )

#             # ---------------------------------------------------------
#             # State classification
#             # ---------------------------------------------------------

#             if track.stationary_since is None:

#                 movement_state = "moving"

#             else:

#                 # -----------------------------------------------------
#                 # Traffic signal / queue waiting gets first priority
#                 # -----------------------------------------------------

#                 if (
#                     in_waiting_zone
#                     and
#                     stationary_duration
#                     >=
#                     WAITING_TIME_THRESHOLD_SECONDS
#                 ):

#                     movement_state = (
#                         "signal_waiting"
#                     )

#                 # -----------------------------------------------------
#                 # Parked vehicle
#                 #
#                 # Exactly 5 seconds stationary.
#                 #
#                 # If a parking zone is configured, vehicle must be
#                 # inside it.
#                 #
#                 # If no parking zone is configured, stationary duration
#                 # alone is enough, as long as it isn't in waiting zone.
#                 # -----------------------------------------------------

#                 elif (
#                     not in_waiting_zone
#                     and
#                     stationary_duration
#                     >= (
#                         PARKED_TIME_THRESHOLD_SECONDS
#                         +
#                         PARKED_CONFIRMATION_SECONDS
#                     )
#                     and
#                     (
#                         PARKING_ZONE is None
#                         or
#                         in_parking_zone
#                     )
#                 ):

#                     movement_state = "parked"

#                 # -----------------------------------------------------
#                 # Stationary but not yet parked
#                 # -----------------------------------------------------

#                 else:

#                     movement_state = (
#                         "signal_waiting"
#                     )

#             track.status = (
#                 movement_state
#             )

#             self.seen_ids.add(
#                 track_id
#             )

#             # ---------------------------------------------------------
#             # Output record
#             # ---------------------------------------------------------

#             record = {

#                 "road_id": ROAD_ID,

#                 "frame_index": int(
#                     frame_index
#                 ),

#                 "timestamp": round(
#                     timestamp,
#                     3
#                 ),

#                 "vehicle_id": int(
#                     track_id
#                 ),

#                 "vehicle_type": (
#                     stable_vehicle_type
#                 ),

#                 "bbox": [
#                     round(
#                         float(v),
#                         1
#                     )
#                     for v in bbox
#                 ],

#                 "position": [
#                     round(
#                         float(center[0]),
#                         1
#                     ),
#                     round(
#                         float(center[1]),
#                         1
#                     )
#                 ],

#                 "confidence": round(
#                     float(confidence),
#                     3
#                 ),

#                 "movement_state": (
#                     movement_state
#                 ),

#                 "stationary_duration": round(
#                     stationary_duration,
#                     1
#                 ),

#                 "in_waiting_zone": bool(
#                     in_waiting_zone
#                 ),

#                 "in_parking_zone": bool(
#                     in_parking_zone
#                 ),
#             }

#             records.append(
#                 record
#             )

#         return records


# # =====================================================================
# # INPUT
# # =====================================================================

# def open_source(source):

#     try:

#         source_value = int(
#             source
#         )

#     except (
#         TypeError,
#         ValueError
#     ):

#         source_value = source

#     capture = cv2.VideoCapture(
#         source_value
#     )

#     if not capture.isOpened():

#         raise RuntimeError(
#             f"Could not open video source: {source}"
#         )

#     return capture


# # =====================================================================
# # VIDEO OVERLAY
# # =====================================================================

# def draw_overlay(
#     frame,
#     records
# ):

#     colors = {

#         "moving": (
#             0,
#             200,
#             0
#         ),

#         "signal_waiting": (
#             0,
#             200,
#             255
#         ),

#         "parked": (
#             0,
#             0,
#             255
#         ),
#     }

#     for record in records:

#         x1, y1, x2, y2 = [
#             int(v)
#             for v in record["bbox"]
#         ]

#         state = record[
#             "movement_state"
#         ]

#         color = colors.get(
#             state,
#             (
#                 255,
#                 255,
#                 255
#             )
#         )

#         cv2.rectangle(
#             frame,
#             (x1, y1),
#             (x2, y2),
#             color,
#             2
#         )

#         label = (
#             f"ID {record['vehicle_id']} | "
#             f"{record['vehicle_type']} | "
#             f"{state}"
#         )

#         cv2.putText(
#             frame,
#             label,
#             (
#                 x1,
#                 max(
#                     20,
#                     y1 - 8
#                 )
#             ),
#             cv2.FONT_HERSHEY_SIMPLEX,
#             0.5,
#             color,
#             2,
#             cv2.LINE_AA
#         )

#     return frame


# # =====================================================================
# # OUTPUT
# # =====================================================================

# def write_outputs(
#     records,
#     json_path,
#     csv_path
# ):

#     json_path = Path(
#         json_path
#     )

#     csv_path = Path(
#         csv_path
#     )

#     json_path.parent.mkdir(
#         parents=True,
#         exist_ok=True
#     )

#     csv_path.parent.mkdir(
#         parents=True,
#         exist_ok=True
#     )

#     # ---------------------------------------------------------------
#     # JSON
#     # ---------------------------------------------------------------

#     with open(
#         json_path,
#         "w",
#         encoding="utf-8"
#     ) as file:

#         json.dump(
#             records,
#             file,
#             indent=2
#         )

#     # ---------------------------------------------------------------
#     # CSV
#     # ---------------------------------------------------------------

#     fieldnames = [

#         "road_id",
#         "frame_index",
#         "timestamp",
#         "vehicle_id",
#         "vehicle_type",
#         "bbox",
#         "position",
#         "confidence",
#         "movement_state",
#         "stationary_duration",
#         "in_waiting_zone",
#         "in_parking_zone",
#     ]

#     with open(
#         csv_path,
#         "w",
#         newline="",
#         encoding="utf-8"
#     ) as file:

#         writer = csv.DictWriter(
#             file,
#             fieldnames=fieldnames
#         )

#         writer.writeheader()

#         for record in records:

#             row = dict(
#                 record
#             )

#             row["bbox"] = json.dumps(
#                 row["bbox"]
#             )

#             row["position"] = json.dumps(
#                 row["position"]
#             )

#             writer.writerow(
#                 row
#             )

#     print(
#         f"[Person1] JSON: {json_path}"
#     )

#     print(
#         f"[Person1] CSV : {csv_path}"
#     )


# # =====================================================================
# # MAIN
# # =====================================================================

# def main():

#     parser = argparse.ArgumentParser(
#         description=(
#             "LaneLogic Person 1 - "
#             "Vehicle Detection & Tracking"
#         )
#     )

#     parser.add_argument(
#         "--source",
#         required=True,
#         help=(
#             "Prerecorded video path. "
#             "Example: videos/traffic1.mp4"
#         )
#     )

#     parser.add_argument(
#         "--model",
#         default=DEFAULT_MODEL,
#         help="YOLO model weights"
#     )

#     parser.add_argument(
#         "--output",
#         default="output/detections.json",
#         help="JSON output path"
#     )

#     parser.add_argument(
#         "--csv",
#         default="output/vehicle_data.csv",
#         help="CSV output path"
#     )

#     parser.add_argument(
#         "--resize-width",
#         type=int,
#         default=960,
#         help="Maximum frame width"
#     )

#     parser.add_argument(
#         "--show",
#         action="store_true",
#         help="Show annotated video"
#     )

#     parser.add_argument(
#         "--max-frames",
#         type=int,
#         default=0,
#         help="Maximum frames; 0 = complete video"
#     )

#     args = parser.parse_args()

#     # ---------------------------------------------------------------
#     # Model
#     # ---------------------------------------------------------------

#     tracker = VehicleDetectorTracker(
#         model_path=args.model,
#         confidence=DEFAULT_CONFIDENCE
#     )

#     # ---------------------------------------------------------------
#     # Video
#     # ---------------------------------------------------------------

#     capture = open_source(
#         args.source
#     )

#     fps = capture.get(
#         cv2.CAP_PROP_FPS
#     )

#     if not fps or fps <= 0:

#         fps = 30.0

#     total_frames = int(
#         capture.get(
#             cv2.CAP_PROP_FRAME_COUNT
#         )
#     )

#     print()
#     print("=" * 60)
#     print("LaneLogic - PERSON 1")
#     print("Vehicle Detection & Tracking")
#     print("=" * 60)

#     print(
#         f"Source       : {args.source}"
#     )

#     print(
#         f"Model        : {args.model}"
#     )

#     print(
#         f"FPS          : {fps:.2f}"
#     )

#     print(
#         f"Total frames : {total_frames}"
#     )

#     print(
#         f"Road ID      : {ROAD_ID}"
#     )

#     print(
#         "Parked after : 5.0 seconds"
#     )

#     print("=" * 60)
#     print()

#     all_records = []

#     frame_index = 0

#     processing_start = time.time()

#     # ---------------------------------------------------------------
#     # Process video
#     # ---------------------------------------------------------------

#     while True:

#         ok, frame = capture.read()

#         if not ok:
#             break

#         # -----------------------------------------------------------
#         # Resize only if larger than target width
#         # -----------------------------------------------------------

#         if (
#             args.resize_width
#             and
#             frame.shape[1]
#             > args.resize_width
#         ):

#             scale = (
#                 args.resize_width /
#                 frame.shape[1]
#             )

#             frame = cv2.resize(
#                 frame,
#                 (
#                     args.resize_width,
#                     int(
#                         frame.shape[0] *
#                         scale
#                     )
#                 )
#             )

#         # -----------------------------------------------------------
#         # IMPORTANT:
#         # Use VIDEO TIME, not processing time.
#         # -----------------------------------------------------------

#         timestamp = (
#             frame_index /
#             fps
#         )

#         records = tracker.process_frame(
#             frame,
#             frame_index,
#             timestamp
#         )

#         all_records.extend(
#             records
#         )

#         # -----------------------------------------------------------
#         # Preview
#         # -----------------------------------------------------------

#         if args.show:

#             annotated = draw_overlay(
#                 frame.copy(),
#                 records
#             )

#             cv2.imshow(
#                 "LaneLogic - Person 1",
#                 annotated
#             )

#             key = (
#                 cv2.waitKey(1)
#                 & 0xFF
#             )

#             if key == ord("q"):

#                 print(
#                     "\n[Person1] "
#                     "Stopped by user."
#                 )

#                 break

#         frame_index += 1

#         if (
#             args.max_frames
#             and
#             frame_index
#             >= args.max_frames
#         ):

#             break

#     # ---------------------------------------------------------------
#     # Cleanup
#     # ---------------------------------------------------------------

#     capture.release()

#     if args.show:
#         cv2.destroyAllWindows()

#     # ---------------------------------------------------------------
#     # Final duplicate safety
#     #
#     # One vehicle can appear only once per frame.
#     # ---------------------------------------------------------------

#     unique_records = []

#     seen_frame_vehicle = set()

#     for record in all_records:

#         key = (
#             record["frame_index"],
#             record["vehicle_id"]
#         )

#         if key in seen_frame_vehicle:
#             continue

#         seen_frame_vehicle.add(
#             key
#         )

#         unique_records.append(
#             record
#         )

#     # ---------------------------------------------------------------
#     # Write outputs
#     # ---------------------------------------------------------------

#     write_outputs(
#         unique_records,
#         args.output,
#         args.csv
#     )

#     processing_time = (
#         time.time()
#         -
#         processing_start
#     )

#     print()
#     print("=" * 60)
#     print("PROCESSING COMPLETE")
#     print("=" * 60)

#     print(
#         f"Frames processed : {frame_index}"
#     )

#     print(
#         f"Records exported : {len(unique_records)}"
#     )

#     print(
#         f"Unique vehicles  : {len(tracker.seen_ids)}"
#     )

#     print(
#         f"Processing time  : {processing_time:.1f}s"
#     )

#     print(
#         f"JSON             : {args.output}"
#     )

#     print(
#         f"CSV              : {args.csv}"
#     )

#     print("=" * 60)


# if __name__ == "__main__":
#     main()










import argparse
import csv
import json
import math
import time
from collections import Counter, deque
from pathlib import Path
from datetime import datetime, timezone

import cv2
import torch
from ultralytics import YOLO


# =====================================================================
# LANELOGIC - PERSON 1
# Indian-road object detection + ByteTrack + obstruction event engine
# =====================================================================
# IMPORTANT:
# 1. A standard yolov8s.pt does NOT contain Indian-specific classes such
#    as auto-rickshaw/e-rickshaw/stall/garbage. Use a custom model for
#    those classes (example: models/lanelogic_indian.pt).
# 2. The code still supports yolov8s.pt as a fallback for development.
# 3. PARKED_TIME_THRESHOLD_SECONDS intentionally remains 5 seconds for
#    the current demo/test videos.
# 4. --source accepts a video file, webcam index, RTSP URL, HTTP stream,
#    etc. Therefore the same detector can later run on CCTV.
# =====================================================================

BASE_DIR = Path(__file__).resolve().parent

# ---------------------------------------------------------------------
# Model / detection defaults
# ---------------------------------------------------------------------
DEFAULT_MODEL = "yolov8s.pt"
DEFAULT_CONFIDENCE = 0.40
DEFAULT_IOU = 0.50
DEFAULT_IMAGE_SIZE = 640

# ---------------------------------------------------------------------
# Tracking defaults
# ---------------------------------------------------------------------
TRACKER_CONFIG = "bytetrack.yaml"
POSITION_HISTORY_SECONDS = 2.0
STOP_MOVEMENT_RATIO = 0.25
TRACK_TIMEOUT_SECONDS = 2.0

# ---------------------------------------------------------------------
# State thresholds
# ---------------------------------------------------------------------
WAITING_TIME_THRESHOLD_SECONDS = 3.0
PARKED_TIME_THRESHOLD_SECONDS = 5.0
PARKED_CONFIRMATION_SECONDS = 0.0

# ---------------------------------------------------------------------
# Output / batching
# ---------------------------------------------------------------------
DEFAULT_EVENT_BATCH_SECONDS = 5.0
MODEL_VERSION = "person1-v2"
SCHEMA_VERSION = "1.0"

# ---------------------------------------------------------------------
# Road configuration
# ---------------------------------------------------------------------
ROAD_ID = "ROAD_001"
CAMERA_ID = "CAMERA_001"
ROAD_NAME = "Unknown Road"

# Optional image-space zones: [x1, y1, x2, y2]
WAITING_ZONE = None
PARKING_ZONE = None
ROAD_ROI = None

# ---------------------------------------------------------------------
# COCO fallback labels. These IDs are only for the standard fallback
# model. Custom Indian models are read dynamically from model.names.
# ---------------------------------------------------------------------
COCO_NAMES = {
    1: "bicycle",
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck",
}

VEHICLE_LABELS = {
    "bicycle", "bike", "motorcycle", "motorbike", "scooter",
    "car", "auto", "auto_rickshaw", "autorickshaw", "rickshaw",
    "e_rickshaw", "e-rickshaw", "erickshaw", "three_wheeler",
    "three-wheeler", "bus", "truck", "van", "tempo", "minibus",
    "cycle_rickshaw", "cycle-rickshaw", "tractor", "trailer",
}

STATIC_OBSTRUCTION_LABELS = {
    "stall", "shop_stall", "roadside_stall", "cart", "vendor_cart",
    "pushcart", "handcart", "garbage", "trash", "waste", "debris",
    "construction", "construction_material", "barrier", "road_barrier",
    "roadblock", "obstacle", "dump", "piled_waste", "container",
}

WAITING_LABELS = {"signal_waiting", "traffic_light_waiting"}


# =====================================================================
# HELPERS
# =====================================================================

def normalize_label(label):
    return str(label).strip().lower().replace(" ", "_")


def object_category(label):
    n = normalize_label(label)
    if n in VEHICLE_LABELS:
        return "vehicle"
    if n in STATIC_OBSTRUCTION_LABELS:
        return "static_obstruction"
    return "other"


def get_center(bbox):
    x1, y1, x2, y2 = bbox
    return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)


def pixel_distance(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def bbox_height(bbox):
    return max(1.0, bbox[3] - bbox[1])


def normalized_movement(old_position, new_position, bbox):
    return pixel_distance(old_position, new_position) / bbox_height(bbox)


def point_inside_zone(point, zone):
    if zone is None:
        return False
    x, y = point
    x1, y1, x2, y2 = zone
    return x1 <= x <= x2 and y1 <= y <= y2


def calculate_iou(a, b):
    xa1, ya1, xa2, ya2 = a
    xb1, yb1, xb2, yb2 = b
    ix1, iy1 = max(xa1, xb1), max(ya1, yb1)
    ix2, iy2 = min(xa2, xb2), min(ya2, yb2)
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    intersection = iw * ih
    area_a = max(0.0, xa2 - xa1) * max(0.0, ya2 - ya1)
    area_b = max(0.0, xb2 - xb1) * max(0.0, yb2 - yb1)
    union = area_a + area_b - intersection
    return intersection / union if union > 0 else 0.0


def utc_now_iso():
    return datetime.now(timezone.utc).isoformat()


def safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


# =====================================================================
# TRACK STATE
# =====================================================================

class TrackState:
    def __init__(self, track_id, label, category):
        self.track_id = int(track_id)
        self.label = label
        self.category = category
        self.centers = deque(maxlen=60)
        self.timestamps = deque(maxlen=60)
        self.class_history = deque(maxlen=15)
        self.stationary_since = None
        self.last_seen_timestamp = 0.0
        self.last_seen_frame = -1
        self.last_bbox = None
        self.last_confidence = 0.0
        self.status = "moving"
        self.last_movement_ratio = None
        self.active_event = None

    def update(self, center, timestamp, bbox, class_id, confidence, label):
        self.centers.append(center)
        self.timestamps.append(timestamp)
        self.last_bbox = bbox
        self.last_confidence = confidence
        self.last_seen_timestamp = timestamp
        self.class_history.append(int(class_id))
        self.label = label

        movement_ratio = None
        if len(self.centers) >= 2:
            old_position = self.centers[0]
            old_timestamp = self.timestamps[0]
            dt = timestamp - old_timestamp
            if dt > 0.5:
                movement_ratio = normalized_movement(old_position, center, bbox)

        self.last_movement_ratio = movement_ratio
        stationary = movement_ratio is not None and movement_ratio < STOP_MOVEMENT_RATIO

        if stationary:
            if self.stationary_since is None:
                self.stationary_since = timestamp
        else:
            self.stationary_since = None
            self.status = "moving"

        return self.stationary_duration(timestamp)

    def stationary_duration(self, timestamp):
        if self.stationary_since is None:
            return 0.0
        return max(0.0, timestamp - self.stationary_since)


# =====================================================================
# PERSON 1 DETECTOR
# =====================================================================

class VehicleDetectorTracker:
    def __init__(self, model_path, confidence, allowed_labels=None):
        print(f"[Person1] Loading model: {model_path}")
        self.model = YOLO(model_path)
        self.confidence = confidence
        self.tracks = {}
        self.seen_ids = set()
        self.allowed_labels = {
            normalize_label(x) for x in allowed_labels
        } if allowed_labels else None
        self.model_names = self._get_model_names()
        print(f"[Person1] Model classes: {len(self.model_names)}")

    def _get_model_names(self):
        names = getattr(self.model, "names", {})
        if isinstance(names, dict):
            return {int(k): str(v) for k, v in names.items()}
        return {i: str(v) for i, v in enumerate(names)}

    def label_for_class(self, class_id):
        if class_id in self.model_names:
            return self.model_names[class_id]
        return COCO_NAMES.get(class_id, f"class_{class_id}")

    def should_keep(self, label):
        if self.allowed_labels is None:
            # For the standard COCO model, only keep relevant road classes.
            if self.model_names and set(self.model_names.values()) == set(COCO_NAMES.values()):
                return normalize_label(label) in VEHICLE_LABELS
            # For a custom model, process all classes because the model was
            # specifically trained for the project's object vocabulary.
            return True
        return normalize_label(label) in self.allowed_labels

    def deduplicate_boxes(self, boxes, confidences, class_ids, track_ids):
        if len(boxes) <= 1:
            return boxes, confidences, class_ids, track_ids

        keep = [True] * len(boxes)
        order = sorted(range(len(boxes)), key=lambda i: confidences[i], reverse=True)
        for a, i in enumerate(order):
            if not keep[i]:
                continue
            for j in order[a + 1:]:
                if not keep[j]:
                    continue
                if calculate_iou(boxes[i], boxes[j]) >= 0.60:
                    # Never discard two different classes just because they overlap.
                    if class_ids[i] == class_ids[j]:
                        keep[j] = False

        return (
            [x for x, k in zip(boxes, keep) if k],
            [x for x, k in zip(confidences, keep) if k],
            [x for x, k in zip(class_ids, keep) if k],
            [x for x, k in zip(track_ids, keep) if k],
        )

    def process_frame(self, frame, frame_index, timestamp):
        results = self.model.track(
            frame,
            persist=True,
            tracker=TRACKER_CONFIG,
            conf=self.confidence,
            iou=DEFAULT_IOU,
            imgsz=DEFAULT_IMAGE_SIZE,
            half=torch.cuda.is_available(),
            verbose=False,
        )

        records = []
        if not results:
            return records

        result = results[0]
        if result.boxes is None or result.boxes.id is None:
            return records

        boxes = result.boxes.xyxy.cpu().numpy().tolist()
        confidences = result.boxes.conf.cpu().numpy().tolist()
        class_ids = result.boxes.cls.cpu().numpy().astype(int).tolist()
        track_ids = result.boxes.id.cpu().numpy().astype(int).tolist()

        boxes, confidences, class_ids, track_ids = self.deduplicate_boxes(
            boxes, confidences, class_ids, track_ids
        )

        processed_ids = set()

        for bbox, confidence, class_id, track_id in zip(
            boxes, confidences, class_ids, track_ids
        ):
            if track_id in processed_ids:
                continue
            processed_ids.add(track_id)

            label = self.label_for_class(class_id)
            if not self.should_keep(label):
                continue

            category = object_category(label)
            center = get_center(bbox)

            if track_id not in self.tracks:
                self.tracks[track_id] = TrackState(track_id, label, category)

            track = self.tracks[track_id]
            track.last_seen_frame = frame_index
            stationary_duration = track.update(
                center, timestamp, bbox, class_id, float(confidence), label
            )

            in_waiting_zone = point_inside_zone(center, WAITING_ZONE)
            in_parking_zone = point_inside_zone(center, PARKING_ZONE)
            in_road_roi = point_inside_zone(center, ROAD_ROI) if ROAD_ROI else True

            # Static objects are obstructions when detected inside the road ROI.
            # They do not use vehicle/signal-waiting semantics.
            if category == "static_obstruction":
                movement_state = "static_obstruction" if in_road_roi else "off_road"
            elif track.stationary_since is None:
                movement_state = "moving"
            elif in_waiting_zone and stationary_duration >= WAITING_TIME_THRESHOLD_SECONDS:
                movement_state = "signal_waiting"
            elif (
                not in_waiting_zone
                and stationary_duration >= PARKED_TIME_THRESHOLD_SECONDS + PARKED_CONFIRMATION_SECONDS
                and (PARKING_ZONE is None or in_parking_zone)
            ):
                movement_state = "parked"
            else:
                # Important: do NOT call every short stationary period
                # "signal_waiting". It is simply temporarily stopped.
                movement_state = "temporarily_stopped"

            track.status = movement_state
            self.seen_ids.add(track_id)

            record = {
                "schema_version": SCHEMA_VERSION,
                "road_id": ROAD_ID,
                "camera_id": CAMERA_ID,
                "frame_index": int(frame_index),
                "timestamp": round(float(timestamp), 3),
                "vehicle_id": int(track_id),
                "object_type": category,
                "vehicle_type": label if category == "vehicle" else None,
                "obstruction_type": label if category == "static_obstruction" else None,
                "bbox": [round(float(v), 1) for v in bbox],
                "position": [round(float(center[0]), 1), round(float(center[1]), 1)],
                "confidence": round(float(confidence), 3),
                "movement_state": movement_state,
                "stationary_duration": round(float(stationary_duration), 1),
                "movement_ratio": (
                    round(float(track.last_movement_ratio), 3)
                    if track.last_movement_ratio is not None else None
                ),
                "in_waiting_zone": bool(in_waiting_zone),
                "in_parking_zone": bool(in_parking_zone),
                "in_road_roi": bool(in_road_roi),
                "model_version": MODEL_VERSION,
            }
            records.append(record)

        return records

    def close_expired_tracks(self, timestamp):
        ended = []
        for track_id, track in list(self.tracks.items()):
            if timestamp - track.last_seen_timestamp > TRACK_TIMEOUT_SECONDS:
                if track.active_event is not None:
                    event = dict(track.active_event)
                    event["end_time"] = track.last_seen_timestamp
                    event["duration_sec"] = round(
                        max(0.0, track.last_seen_timestamp - event["start_time"]), 2
                    )
                    event["status"] = "ended"
                    ended.append(event)
                del self.tracks[track_id]
        return ended


# =====================================================================
# EVENT ENGINE
# =====================================================================

class ObstructionEventEngine:
    """Converts frame records into persistent obstruction events."""

    def __init__(self):
        self.events = []

    def update(self, records, timestamp):
        emitted = []
        obstruction_keys = set()

        for record in records:
            track_id = record["vehicle_id"]
            track_key = (record["object_type"], track_id)

            # A confirmed obstruction creates/updates one persistent event.
            is_obstruction = (
                record["movement_state"] in {"parked", "static_obstruction"}
                and record.get("in_road_roi", True)
            )

            if not is_obstruction:
                # If an existing obstruction starts moving, end that event.
                for event in self.events:
                    if event.get("_active_key") == track_key and event["status"] == "active":
                        event["end_time"] = round(timestamp, 3)
                        event["duration_sec"] = round(
                            max(0.0, timestamp - event["start_time"]), 2
                        )
                        event["status"] = "ended"
                        emitted.append(self._public_event(event))
                continue

            obstruction_keys.add(track_key)
            existing = next(
                (e for e in self.events if e.get("_active_key") == track_key and e["status"] == "active"),
                None,
            )

            if existing is None:
                event = {
                    "schema_version": SCHEMA_VERSION,
                    "event_id": f"{ROAD_ID}-{CAMERA_ID}-{track_id}-{int(timestamp * 1000)}",
                    "road_id": ROAD_ID,
                    "camera_id": CAMERA_ID,
                    "vehicle_id": track_id if record["object_type"] == "vehicle" else None,
                    "vehicle_type": record.get("vehicle_type"),
                    "obstruction_type": record.get("obstruction_type"),
                    "object_type": record["object_type"],
                    "start_time": round(timestamp, 3),
                    "end_time": None,
                    "duration_sec": 0.0,
                    "location": {
                        "road_id": ROAD_ID,
                        "image_x": record["position"][0],
                        "image_y": record["position"][1],
                    },
                    "occupied_width_m": None,
                    "road_space_loss_pct": None,
                    "recurrence_score": None,
                    "cause": None,
                    "cause_confidence": None,
                    "severity": None,
                    "detection_confidence": record["confidence"],
                    "model_version": MODEL_VERSION,
                    "status": "active",
                    "last_seen_timestamp": round(timestamp, 3),
                    "evidence": {
                        "movement_state": record["movement_state"],
                        "stationary_duration_at_creation": record["stationary_duration"],
                        "frame_index": record["frame_index"],
                    },
                    "_active_key": track_key,
                }
                self.events.append(event)
                existing = event

            existing["end_time"] = round(timestamp, 3)
            existing["last_seen_timestamp"] = round(timestamp, 3)
            existing["duration_sec"] = round(
                max(0.0, timestamp - existing["start_time"]), 2
            )
            existing["detection_confidence"] = max(
                existing["detection_confidence"], record["confidence"]
            )

        # Do not close an event merely because this frame has no detection:
        # tracker timeout is handled by close_missing_events().
        return emitted

    def close_missing_events(self, timestamp, timeout=TRACK_TIMEOUT_SECONDS):
        ended = []
        for event in self.events:
            if event["status"] != "active":
                continue
            last_seen = event.get("last_seen_timestamp", event["start_time"])
            if timestamp - last_seen >= timeout:
                event["end_time"] = round(last_seen, 3)
                event["duration_sec"] = round(
                    max(0.0, last_seen - event["start_time"]), 2
                )
                event["status"] = "ended"
                ended.append(self._public_event(event))
        return ended

    def finalize(self, timestamp):
        ended = []
        for event in self.events:
            if event["status"] == "active":
                event["end_time"] = round(timestamp, 3)
                event["duration_sec"] = round(
                    max(0.0, timestamp - event["start_time"]), 2
                )
                event["status"] = "ended"
                ended.append(self._public_event(event))
        return ended

    @staticmethod
    def _public_event(event):
        clean = dict(event)
        clean.pop("_active_key", None)
        return clean

    def public_events(self):
        return [self._public_event(e) for e in self.events]


# =====================================================================
# INPUT / OUTPUT
# =====================================================================

def open_source(source):
    try:
        source_value = int(source)
    except (TypeError, ValueError):
        source_value = source

    capture = cv2.VideoCapture(source_value)
    if not capture.isOpened():
        raise RuntimeError(f"Could not open video/camera source: {source}")
    return capture


def draw_overlay(frame, records, events):
    colors = {
        "moving": (0, 200, 0),
        "temporarily_stopped": (255, 180, 0),
        "signal_waiting": (0, 200, 255),
        "parked": (0, 0, 255),
        "static_obstruction": (255, 0, 255),
        "off_road": (150, 150, 150),
    }

    for record in records:
        x1, y1, x2, y2 = [int(v) for v in record["bbox"]]
        state = record["movement_state"]
        color = colors.get(state, (255, 255, 255))
        label = record.get("vehicle_type") or record.get("obstruction_type") or record["object_type"]
        text = f"ID {record['vehicle_id']} | {label} | {state}"
        if record["stationary_duration"] > 0:
            text += f" | {record['stationary_duration']:.1f}s"

        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        cv2.putText(
            frame, text, (x1, max(20, y1 - 8)),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2, cv2.LINE_AA
        )

    active_count = sum(1 for e in events if e["status"] == "active")
    cv2.putText(
        frame,
        f"Active obstruction events: {active_count}",
        (15, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 255),
        2,
        cv2.LINE_AA,
    )
    return frame


def write_json(records, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)


def append_jsonl(items, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item) + "\n")


def write_csv(records, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "schema_version", "road_id", "camera_id", "frame_index", "timestamp",
        "vehicle_id", "object_type", "vehicle_type", "obstruction_type", "bbox",
        "position", "confidence", "movement_state", "stationary_duration",
        "movement_ratio", "in_waiting_zone", "in_parking_zone", "in_road_roi",
        "model_version",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for record in records:
            row = dict(record)
            row["bbox"] = json.dumps(row["bbox"])
            row["position"] = json.dumps(row["position"])
            writer.writerow(row)


# =====================================================================
# MAIN
# =====================================================================

def main():
    parser = argparse.ArgumentParser(
        description="LaneLogic Person 1 - Indian traffic detection, tracking and obstruction events"
    )
    parser.add_argument("--source", required=True, help="Video path, webcam index, RTSP/HTTP stream")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="YOLO weights (.pt)")
    parser.add_argument("--confidence", type=float, default=DEFAULT_CONFIDENCE)
    parser.add_argument("--output", default="output/detections.json")
    parser.add_argument("--events-output", default="output/obstruction_events.json")
    parser.add_argument("--event-stream", default="output/event_stream.jsonl")
    parser.add_argument("--csv", default="output/vehicle_data.csv")
    parser.add_argument("--resize-width", type=int, default=960)
    parser.add_argument("--show", action="store_true")
    parser.add_argument("--max-frames", type=int, default=0)
    parser.add_argument("--live", action="store_true", help="Treat source as a live stream/camera")
    parser.add_argument("--event-batch-seconds", type=float, default=DEFAULT_EVENT_BATCH_SECONDS)
    parser.add_argument(
        "--classes",
        default="",
        help="Optional comma-separated labels to keep, e.g. car,auto_rickshaw,e_rickshaw,stall,garbage"
    )
    args = parser.parse_args()

    allowed_labels = [x.strip() for x in args.classes.split(",") if x.strip()] or None

    tracker = VehicleDetectorTracker(
        model_path=args.model,
        confidence=args.confidence,
        allowed_labels=allowed_labels,
    )
    event_engine = ObstructionEventEngine()

    capture = open_source(args.source)
    fps = capture.get(cv2.CAP_PROP_FPS)
    if not fps or fps <= 0:
        fps = 30.0

    is_file = Path(str(args.source)).exists()
    live_mode = args.live or not is_file
    total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT)) if is_file else 0

    print("=" * 68)
    print("LaneLogic - PERSON 1")
    print("Indian Object Detection + ByteTrack + Obstruction Events")
    print("=" * 68)
    print(f"Source       : {args.source}")
    print(f"Mode         : {'LIVE' if live_mode else 'REPLAY'}")
    print(f"Model        : {args.model}")
    print(f"Confidence   : {args.confidence}")
    print(f"FPS           : {fps:.2f}")
    print(f"Road ID      : {ROAD_ID}")
    print(f"Camera ID    : {CAMERA_ID}")
    print("Parked after : 5.0 seconds")
    print(f"Event batch  : {args.event_batch_seconds:.1f}s")
    print("=" * 68)

    all_records = []
    frame_index = 0
    last_event_emit = 0.0
    processing_start = time.time()

    # Remove an old JSONL stream so a fresh run starts clean.
    stream_path = Path(args.event_stream)
    if stream_path.exists():
        stream_path.unlink()

    while True:
        ok, frame = capture.read()
        if not ok:
            if live_mode:
                # Camera/RTSP streams can temporarily return no frame.
                time.sleep(0.05)
                continue
            break

        if args.resize_width and frame.shape[1] > args.resize_width:
            scale = args.resize_width / frame.shape[1]
            frame = cv2.resize(frame, (
                args.resize_width,
                int(frame.shape[0] * scale),
            ))

        # Replay uses video time. Live uses elapsed wall-clock time so
        # event duration reflects the actual stream rather than frame count.
        if live_mode:
            timestamp = time.time() - processing_start
        else:
            timestamp = frame_index / fps

        records = tracker.process_frame(frame, frame_index, timestamp)
        all_records.extend(records)
        event_engine.update(records, timestamp)

        # End active tracks/events after a short detection gap or movement.
        tracker.close_expired_tracks(timestamp)
        event_engine.close_missing_events(timestamp)

        # Periodic event snapshots: this is the "phased" live output.
        if timestamp - last_event_emit >= args.event_batch_seconds:
            active_events = [
                e for e in event_engine.public_events()
                if e["status"] == "active"
            ]
            if active_events:
                append_jsonl(active_events, args.event_stream)
            last_event_emit = timestamp

        if args.show:
            annotated = draw_overlay(
                frame.copy(), records, event_engine.public_events()
            )
            cv2.imshow("LaneLogic - Person 1", annotated)
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break

        frame_index += 1

        if args.max_frames and frame_index >= args.max_frames:
            break

    capture.release()
    if args.show:
        cv2.destroyAllWindows()

    final_time = (frame_index / fps) if not live_mode else (time.time() - processing_start)
    event_engine.finalize(final_time)

    # Remove duplicate frame/track records.
    unique_records = []
    seen = set()
    for record in all_records:
        key = (record["frame_index"], record["vehicle_id"])
        if key in seen:
            continue
        seen.add(key)
        unique_records.append(record)

    public_events = event_engine.public_events()

    write_json(unique_records, args.output)
    write_json(public_events, args.events_output)
    write_csv(unique_records, args.csv)

    # Ensure final event state is available to the stream consumer.
    append_jsonl(public_events, args.event_stream)

    print()
    print("=" * 68)
    print("PROCESSING COMPLETE")
    print("=" * 68)
    print(f"Frames processed : {frame_index}")
    print(f"Detection rows   : {len(unique_records)}")
    print(f"Unique tracks    : {len(tracker.seen_ids)}")
    print(f"Obstruction evts : {len(public_events)}")
    print(f"JSON             : {args.output}")
    print(f"Events JSON      : {args.events_output}")
    print(f"Event stream     : {args.event_stream}")
    print(f"CSV              : {args.csv}")
    print("=" * 68)


if __name__ == "__main__":
    main()
