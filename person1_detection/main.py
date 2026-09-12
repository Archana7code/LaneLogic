
import argparse
import csv
import json
import math
import time
from collections import Counter, deque
from pathlib import Path

import cv2
import torch
from ultralytics import YOLO


# =====================================================================
# PERSON 1 — VEHICLE DETECTION, TRACKING & SMART STOP DETECTION
# LaneLogic / SIH 2026
# =====================================================================

BASE_DIR = Path(__file__).resolve().parent


# =====================================================================
# DEFAULT CONFIGURATION
# =====================================================================

# COCO vehicle classes
VEHICLE_CLASS_IDS = {
    1: "bicycle",
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck",
}


# =====================================================================
# DETECTION
# =====================================================================

DEFAULT_MODEL = "yolov8s.pt"
DEFAULT_CONFIDENCE = 0.40
DEFAULT_IOU = 0.50
DEFAULT_IMAGE_SIZE = 640


# =====================================================================
# TRACKING
# =====================================================================

TRACK_BUFFER = 120
TRACK_HIGH_THRESH = 0.60
TRACK_LOW_THRESH = 0.10
NEW_TRACK_THRESH = 0.70
MATCH_THRESH = 0.80


# =====================================================================
# MOVEMENT ANALYSIS
# =====================================================================

POSITION_HISTORY_SECONDS = 2.0
STOP_MOVEMENT_RATIO = 0.25


# =====================================================================
# VEHICLE STATE
# =====================================================================

# Traffic-signal waiting
WAITING_TIME_THRESHOLD_SECONDS = 3.0

# IMPORTANT:
# Parked threshold is EXACTLY 5 seconds.
PARKED_TIME_THRESHOLD_SECONDS = 5.0

# No additional confirmation delay.
PARKED_CONFIRMATION_SECONDS = 0.0


# =====================================================================
# CLASS SMOOTHING
# =====================================================================

CLASS_HISTORY_LENGTH = 15


# =====================================================================
# DUPLICATE FILTERING
# =====================================================================

DUPLICATE_IOU_THRESHOLD = 0.60


# =====================================================================
# ROAD
# =====================================================================

ROAD_ID = "ROAD_001"


# =====================================================================
# ZONES
# =====================================================================

# Set these according to the actual video if needed.
#
# WAITING_ZONE:
#   Traffic signal / stop-line region.
#
# PARKING_ZONE:
#   Actual parking/loading area.
#
# If WAITING_ZONE is None:
#   stationary vehicles are not specifically identified
#   as signal waiting based on location.
#
# If PARKING_ZONE is None:
#   stationary vehicles can become parked after 5 seconds,
#   provided they are not inside WAITING_ZONE.
#
# Example:
#
# WAITING_ZONE = [300, 150, 650, 300]
# PARKING_ZONE = [700, 250, 950, 520]

WAITING_ZONE = None
PARKING_ZONE = None


# =====================================================================
# HELPER FUNCTIONS
# =====================================================================

def get_center(bbox):
    x1, y1, x2, y2 = bbox

    return (
        (x1 + x2) / 2.0,
        (y1 + y2) / 2.0
    )


def pixel_distance(point_a, point_b):
    return math.hypot(
        point_a[0] - point_b[0],
        point_a[1] - point_b[1]
    )


def bbox_height(bbox):
    x1, y1, x2, y2 = bbox

    return max(
        1.0,
        y2 - y1
    )


def normalized_movement(
    previous_position,
    current_position,
    bbox
):
    """
    Normalize movement using vehicle bounding-box height.
    """

    movement = pixel_distance(
        previous_position,
        current_position
    )

    return movement / bbox_height(bbox)


def point_inside_zone(point, zone):

    if zone is None:
        return False

    x, y = point

    x1, y1, x2, y2 = zone

    return (
        x1 <= x <= x2
        and
        y1 <= y <= y2
    )


def calculate_iou(box_a, box_b):

    xa1, ya1, xa2, ya2 = box_a
    xb1, yb1, xb2, yb2 = box_b

    inter_x1 = max(xa1, xb1)
    inter_y1 = max(ya1, yb1)

    inter_x2 = min(xa2, xb2)
    inter_y2 = min(ya2, yb2)

    inter_width = max(
        0.0,
        inter_x2 - inter_x1
    )

    inter_height = max(
        0.0,
        inter_y2 - inter_y1
    )

    intersection = (
        inter_width *
        inter_height
    )

    area_a = (
        max(0.0, xa2 - xa1) *
        max(0.0, ya2 - ya1)
    )

    area_b = (
        max(0.0, xb2 - xb1) *
        max(0.0, yb2 - yb1)
    )

    union = (
        area_a +
        area_b -
        intersection
    )

    if union <= 0:
        return 0.0

    return intersection / union


# =====================================================================
# TRACK STATE
# =====================================================================

class TrackState:

    def __init__(
        self,
        track_id,
        vehicle_type
    ):

        self.track_id = track_id

        self.vehicle_type = vehicle_type

        self.centers = deque(
            maxlen=60
        )

        self.timestamps = deque(
            maxlen=60
        )

        self.stationary_since = None

        self.last_seen_frame = -1

        self.class_history = deque(
            maxlen=CLASS_HISTORY_LENGTH
        )

        self.status = "moving"

        self.last_movement_ratio = None

        self.last_seen_timestamp = 0.0


    def update(
        self,
        center,
        timestamp,
        bbox
    ):

        self.centers.append(center)

        self.timestamps.append(timestamp)

        self.last_seen_timestamp = timestamp

        movement_ratio = None

        # -------------------------------------------------------------
        # Determine movement using short history
        # -------------------------------------------------------------

        if len(self.centers) >= 2:

            old_position = self.centers[0]

            old_timestamp = self.timestamps[0]

            time_difference = (
                timestamp -
                old_timestamp
            )

            if time_difference > 0.5:

                movement_ratio = normalized_movement(
                    old_position,
                    center,
                    bbox
                )

        self.last_movement_ratio = movement_ratio

        # IMPORTANT:
        # If movement_ratio is unavailable, vehicle is NOT considered
        # stationary.
        is_stationary = (
            movement_ratio is not None
            and
            movement_ratio < STOP_MOVEMENT_RATIO
        )

        if is_stationary:

            if self.stationary_since is None:

                self.stationary_since = timestamp

        else:

            self.stationary_since = None

            self.status = "moving"

        return self.stationary_duration(
            timestamp
        )


    def stationary_duration(
        self,
        timestamp
    ):

        if self.stationary_since is None:

            return 0.0

        return max(
            0.0,
            timestamp -
            self.stationary_since
        )


# =====================================================================
# VEHICLE DETECTOR / TRACKER
# =====================================================================

class VehicleDetectorTracker:

    def __init__(
        self,
        model_path,
        confidence
    ):

        print(
            f"[Person1] Loading model: {model_path}"
        )

        self.model = YOLO(
            model_path
        )

        self.confidence = confidence

        self.tracks = {}

        self.seen_ids = set()


    # -----------------------------------------------------------------
    # Duplicate removal
    # -----------------------------------------------------------------

    def deduplicate_boxes(
        self,
        boxes,
        confidences,
        class_ids,
        track_ids
    ):

        if len(boxes) <= 1:

            return (
                boxes,
                confidences,
                class_ids,
                track_ids
            )

        keep = [True] * len(boxes)

        order = sorted(
            range(len(boxes)),
            key=lambda i: confidences[i],
            reverse=True
        )

        for a in range(
            len(order)
        ):

            i = order[a]

            if not keep[i]:
                continue

            for b in range(
                a + 1,
                len(order)
            ):

                j = order[b]

                if not keep[j]:
                    continue

                overlap = calculate_iou(
                    boxes[i],
                    boxes[j]
                )

                if (
                    overlap >=
                    DUPLICATE_IOU_THRESHOLD
                ):

                    keep[j] = False

        return (
            [
                box
                for box, flag
                in zip(boxes, keep)
                if flag
            ],

            [
                c
                for c, flag
                in zip(confidences, keep)
                if flag
            ],

            [
                c
                for c, flag
                in zip(class_ids, keep)
                if flag
            ],

            [
                t
                for t, flag
                in zip(track_ids, keep)
                if flag
            ]
        )


    # -----------------------------------------------------------------
    # Process one frame
    # -----------------------------------------------------------------

    def process_frame(
        self,
        frame,
        frame_index,
        timestamp
    ):

        results = self.model.track(
            frame,
            persist=True,
            tracker="bytetrack.yaml",
            classes=list(
                VEHICLE_CLASS_IDS.keys()
            ),
            conf=self.confidence,
            iou=DEFAULT_IOU,
            imgsz=DEFAULT_IMAGE_SIZE,
            half=torch.cuda.is_available(),
            verbose=False
        )

        records = []

        if not results:
            return records

        result = results[0]

        if (
            result.boxes is None
            or
            result.boxes.id is None
        ):
            return records

        boxes = (
            result.boxes.xyxy
            .cpu()
            .numpy()
            .tolist()
        )

        confidences = (
            result.boxes.conf
            .cpu()
            .numpy()
            .tolist()
        )

        class_ids = (
            result.boxes.cls
            .cpu()
            .numpy()
            .astype(int)
            .tolist()
        )

        track_ids = (
            result.boxes.id
            .cpu()
            .numpy()
            .astype(int)
            .tolist()
        )

        (
            boxes,
            confidences,
            class_ids,
            track_ids
        ) = self.deduplicate_boxes(
            boxes,
            confidences,
            class_ids,
            track_ids
        )

        processed_ids = set()

        for (
            bbox,
            confidence,
            class_id,
            track_id
        ) in zip(
            boxes,
            confidences,
            class_ids,
            track_ids
        ):

            if (
                class_id
                not in VEHICLE_CLASS_IDS
            ):
                continue

            if track_id in processed_ids:
                continue

            processed_ids.add(track_id)

            x1, y1, x2, y2 = bbox

            center = get_center(
                bbox
            )

            vehicle_type = (
                VEHICLE_CLASS_IDS[
                    class_id
                ]
            )

            # ---------------------------------------------------------
            # Create track if new
            # ---------------------------------------------------------

            if track_id not in self.tracks:

                self.tracks[track_id] = (
                    TrackState(
                        track_id,
                        vehicle_type
                    )
                )

            track = self.tracks[
                track_id
            ]

            track.last_seen_frame = (
                frame_index
            )

            track.class_history.append(
                class_id
            )

            # ---------------------------------------------------------
            # Stable class voting
            # ---------------------------------------------------------

            stable_class_id = Counter(
                track.class_history
            ).most_common(1)[0][0]

            stable_vehicle_type = (
                VEHICLE_CLASS_IDS[
                    stable_class_id
                ]
            )

            track.vehicle_type = (
                stable_vehicle_type
            )

            # ---------------------------------------------------------
            # Movement
            # ---------------------------------------------------------

            stationary_duration = (
                track.update(
                    center,
                    timestamp,
                    bbox
                )
            )

            # ---------------------------------------------------------
            # Zones
            # ---------------------------------------------------------

            in_waiting_zone = (
                point_inside_zone(
                    center,
                    WAITING_ZONE
                )
            )

            in_parking_zone = (
                point_inside_zone(
                    center,
                    PARKING_ZONE
                )
            )

            # ---------------------------------------------------------
            # State classification
            # ---------------------------------------------------------

            if track.stationary_since is None:

                movement_state = "moving"

            else:

                # -----------------------------------------------------
                # Traffic signal / queue waiting gets first priority
                # -----------------------------------------------------

                if (
                    in_waiting_zone
                    and
                    stationary_duration
                    >=
                    WAITING_TIME_THRESHOLD_SECONDS
                ):

                    movement_state = (
                        "signal_waiting"
                    )

                # -----------------------------------------------------
                # Parked vehicle
                #
                # Exactly 5 seconds stationary.
                #
                # If a parking zone is configured, vehicle must be
                # inside it.
                #
                # If no parking zone is configured, stationary duration
                # alone is enough, as long as it isn't in waiting zone.
                # -----------------------------------------------------

                elif (
                    not in_waiting_zone
                    and
                    stationary_duration
                    >= (
                        PARKED_TIME_THRESHOLD_SECONDS
                        +
                        PARKED_CONFIRMATION_SECONDS
                    )
                    and
                    (
                        PARKING_ZONE is None
                        or
                        in_parking_zone
                    )
                ):

                    movement_state = "parked"

                # -----------------------------------------------------
                # Stationary but not yet parked
                # -----------------------------------------------------

                else:

                    movement_state = (
                        "signal_waiting"
                    )

            track.status = (
                movement_state
            )

            self.seen_ids.add(
                track_id
            )

            # ---------------------------------------------------------
            # Output record
            # ---------------------------------------------------------

            record = {

                "road_id": ROAD_ID,

                "frame_index": int(
                    frame_index
                ),

                "timestamp": round(
                    timestamp,
                    3
                ),

                "vehicle_id": int(
                    track_id
                ),

                "vehicle_type": (
                    stable_vehicle_type
                ),

                "bbox": [
                    round(
                        float(v),
                        1
                    )
                    for v in bbox
                ],

                "position": [
                    round(
                        float(center[0]),
                        1
                    ),
                    round(
                        float(center[1]),
                        1
                    )
                ],

                "confidence": round(
                    float(confidence),
                    3
                ),

                "movement_state": (
                    movement_state
                ),

                "stationary_duration": round(
                    stationary_duration,
                    1
                ),

                "in_waiting_zone": bool(
                    in_waiting_zone
                ),

                "in_parking_zone": bool(
                    in_parking_zone
                ),
            }

            records.append(
                record
            )

        return records


# =====================================================================
# INPUT
# =====================================================================

def open_source(source):

    try:

        source_value = int(
            source
        )

    except (
        TypeError,
        ValueError
    ):

        source_value = source

    capture = cv2.VideoCapture(
        source_value
    )

    if not capture.isOpened():

        raise RuntimeError(
            f"Could not open video source: {source}"
        )

    return capture


# =====================================================================
# VIDEO OVERLAY
# =====================================================================

def draw_overlay(
    frame,
    records
):

    colors = {

        "moving": (
            0,
            200,
            0
        ),

        "signal_waiting": (
            0,
            200,
            255
        ),

        "parked": (
            0,
            0,
            255
        ),
    }

    for record in records:

        x1, y1, x2, y2 = [
            int(v)
            for v in record["bbox"]
        ]

        state = record[
            "movement_state"
        ]

        color = colors.get(
            state,
            (
                255,
                255,
                255
            )
        )

        cv2.rectangle(
            frame,
            (x1, y1),
            (x2, y2),
            color,
            2
        )

        label = (
            f"ID {record['vehicle_id']} | "
            f"{record['vehicle_type']} | "
            f"{state}"
        )

        cv2.putText(
            frame,
            label,
            (
                x1,
                max(
                    20,
                    y1 - 8
                )
            ),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            color,
            2,
            cv2.LINE_AA
        )

    return frame


# =====================================================================
# OUTPUT
# =====================================================================

def write_outputs(
    records,
    json_path,
    csv_path
):

    json_path = Path(
        json_path
    )

    csv_path = Path(
        csv_path
    )

    json_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    csv_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    # ---------------------------------------------------------------
    # JSON
    # ---------------------------------------------------------------

    with open(
        json_path,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            records,
            file,
            indent=2
        )

    # ---------------------------------------------------------------
    # CSV
    # ---------------------------------------------------------------

    fieldnames = [

        "road_id",
        "frame_index",
        "timestamp",
        "vehicle_id",
        "vehicle_type",
        "bbox",
        "position",
        "confidence",
        "movement_state",
        "stationary_duration",
        "in_waiting_zone",
        "in_parking_zone",
    ]

    with open(
        csv_path,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames
        )

        writer.writeheader()

        for record in records:

            row = dict(
                record
            )

            row["bbox"] = json.dumps(
                row["bbox"]
            )

            row["position"] = json.dumps(
                row["position"]
            )

            writer.writerow(
                row
            )

    print(
        f"[Person1] JSON: {json_path}"
    )

    print(
        f"[Person1] CSV : {csv_path}"
    )


# =====================================================================
# MAIN
# =====================================================================

def main():

    parser = argparse.ArgumentParser(
        description=(
            "LaneLogic Person 1 - "
            "Vehicle Detection & Tracking"
        )
    )

    parser.add_argument(
        "--source",
        required=True,
        help=(
            "Prerecorded video path. "
            "Example: videos/traffic1.mp4"
        )
    )

    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help="YOLO model weights"
    )

    parser.add_argument(
        "--output",
        default="output/vehicle_data.json",
        help="JSON output path"
    )

    parser.add_argument(
        "--csv",
        default="output/vehicle_data.csv",
        help="CSV output path"
    )

    parser.add_argument(
        "--resize-width",
        type=int,
        default=960,
        help="Maximum frame width"
    )

    parser.add_argument(
        "--show",
        action="store_true",
        help="Show annotated video"
    )

    parser.add_argument(
        "--max-frames",
        type=int,
        default=0,
        help="Maximum frames; 0 = complete video"
    )

    args = parser.parse_args()

    # ---------------------------------------------------------------
    # Model
    # ---------------------------------------------------------------

    tracker = VehicleDetectorTracker(
        model_path=args.model,
        confidence=DEFAULT_CONFIDENCE
    )

    # ---------------------------------------------------------------
    # Video
    # ---------------------------------------------------------------

    capture = open_source(
        args.source
    )

    fps = capture.get(
        cv2.CAP_PROP_FPS
    )

    if not fps or fps <= 0:

        fps = 30.0

    total_frames = int(
        capture.get(
            cv2.CAP_PROP_FRAME_COUNT
        )
    )

    print()
    print("=" * 60)
    print("LaneLogic - PERSON 1")
    print("Vehicle Detection & Tracking")
    print("=" * 60)

    print(
        f"Source       : {args.source}"
    )

    print(
        f"Model        : {args.model}"
    )

    print(
        f"FPS          : {fps:.2f}"
    )

    print(
        f"Total frames : {total_frames}"
    )

    print(
        f"Road ID      : {ROAD_ID}"
    )

    print(
        "Parked after : 5.0 seconds"
    )

    print("=" * 60)
    print()

    all_records = []

    frame_index = 0

    processing_start = time.time()

    # ---------------------------------------------------------------
    # Process video
    # ---------------------------------------------------------------

    while True:

        ok, frame = capture.read()

        if not ok:
            break

        # -----------------------------------------------------------
        # Resize only if larger than target width
        # -----------------------------------------------------------

        if (
            args.resize_width
            and
            frame.shape[1]
            > args.resize_width
        ):

            scale = (
                args.resize_width /
                frame.shape[1]
            )

            frame = cv2.resize(
                frame,
                (
                    args.resize_width,
                    int(
                        frame.shape[0] *
                        scale
                    )
                )
            )

        # -----------------------------------------------------------
        # IMPORTANT:
        # Use VIDEO TIME, not processing time.
        # -----------------------------------------------------------

        timestamp = (
            frame_index /
            fps
        )

        records = tracker.process_frame(
            frame,
            frame_index,
            timestamp
        )

        all_records.extend(
            records
        )

        # -----------------------------------------------------------
        # Preview
        # -----------------------------------------------------------

        if args.show:

            annotated = draw_overlay(
                frame.copy(),
                records
            )

            cv2.imshow(
                "LaneLogic - Person 1",
                annotated
            )

            key = (
                cv2.waitKey(1)
                & 0xFF
            )

            if key == ord("q"):

                print(
                    "\n[Person1] "
                    "Stopped by user."
                )

                break

        frame_index += 1

        if (
            args.max_frames
            and
            frame_index
            >= args.max_frames
        ):

            break

    # ---------------------------------------------------------------
    # Cleanup
    # ---------------------------------------------------------------

    capture.release()

    if args.show:
        cv2.destroyAllWindows()

    # ---------------------------------------------------------------
    # Final duplicate safety
    #
    # One vehicle can appear only once per frame.
    # ---------------------------------------------------------------

    unique_records = []

    seen_frame_vehicle = set()

    for record in all_records:

        key = (
            record["frame_index"],
            record["vehicle_id"]
        )

        if key in seen_frame_vehicle:
            continue

        seen_frame_vehicle.add(
            key
        )

        unique_records.append(
            record
        )

    # ---------------------------------------------------------------
    # Write outputs
    # ---------------------------------------------------------------

    write_outputs(
        unique_records,
        args.output,
        args.csv
    )

    processing_time = (
        time.time()
        -
        processing_start
    )

    print()
    print("=" * 60)
    print("PROCESSING COMPLETE")
    print("=" * 60)

    print(
        f"Frames processed : {frame_index}"
    )

    print(
        f"Records exported : {len(unique_records)}"
    )

    print(
        f"Unique vehicles  : {len(tracker.seen_ids)}"
    )

    print(
        f"Processing time  : {processing_time:.1f}s"
    )

    print(
        f"JSON             : {args.output}"
    )

    print(
        f"CSV              : {args.csv}"
    )

    print("=" * 60)


if __name__ == "__main__":
    main()