#     # FINAL DUPLICATE SAFETY
#     # ===============================================================

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

#     # ===============================================================
#     # WRITE FINAL OUTPUTS
#     # ===============================================================

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

#     # ===============================================================
#     # SUMMARY
#     # ===============================================================

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

#     print(
#         f"Phase data       : {args.phase_output}"
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

import cv2
import torch
from ultralytics import YOLO


# ============================================================
# CONFIG
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

VEHICLE_CLASS_IDS = {
    1: "bicycle",
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck",
}

DEFAULT_MODEL = "yolov8s.pt"
DEFAULT_CONFIDENCE = 0.40
DEFAULT_IOU = 0.50
DEFAULT_IMAGE_SIZE = 640

TRACK_BUFFER = 120
TRACK_HIGH_THRESH = 0.60
TRACK_LOW_THRESH = 0.10
NEW_TRACK_THRESH = 0.70
MATCH_THRESH = 0.80

POSITION_HISTORY_SECONDS = 2.0
STOP_MOVEMENT_RATIO = 0.25

WAITING_TIME_THRESHOLD_SECONDS = 3.0
PARKED_TIME_THRESHOLD_SECONDS = 5.0
PARKED_CONFIRMATION_SECONDS = 0.0

CLASS_HISTORY_LENGTH = 15

DUPLICATE_IOU_THRESHOLD = 0.60

ROAD_ID = "ROAD_001"

WAITING_ZONE = None
PARKING_ZONE = None

# Phase configuration
DEFAULT_PHASE_SECONDS = 5.0
DEFAULT_PHASE_OUTPUT = "output/detection_stream.jsonl"


# ============================================================
# HELPERS
# ============================================================

def calculate_iou(box_a, box_b):

    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = box_b

    intersection_x1 = max(ax1, bx1)
    intersection_y1 = max(ay1, by1)
    intersection_x2 = min(ax2, bx2)
    intersection_y2 = min(ay2, by2)

    intersection_width = max(
        0,
        intersection_x2 - intersection_x1
    )

    intersection_height = max(
        0,
        intersection_y2 - intersection_y1
    )

    intersection_area = (
        intersection_width
        * intersection_height
    )

    area_a = max(
        0,
        ax2 - ax1
    ) * max(
        0,
        ay2 - ay1
    )

    area_b = max(
        0,
        bx2 - bx1
    ) * max(
        0,
        by2 - by1
    )

    union_area = (
        area_a
        + area_b
        - intersection_area
    )

    if union_area <= 0:
        return 0.0

    return intersection_area / union_area


def point_in_polygon(
    point,
    polygon
):

    if polygon is None:
        return False

    x, y = point

    return cv2.pointPolygonTest(
        polygon,
        (float(x), float(y)),
        False
    ) >= 0


# ============================================================
# TRACK STATE
# ============================================================

class TrackState:

    def __init__(
        self,
        track_id,
        vehicle_type,
        timestamp,
        center,
    ):

        self.track_id = track_id

        self.vehicle_type = (
            vehicle_type
        )

        self.centers = deque()

        self.centers.append(
            (
                timestamp,
                center
            )
        )

        self.stationary_since = None

        self.last_seen_frame = 0

        self.class_history = deque(
            maxlen=CLASS_HISTORY_LENGTH
        )

        self.class_history.append(
            vehicle_type
        )

        self.status = "moving"

        self.movement_ratio = 0.0

        self.last_timestamp = timestamp

    def update(
        self,
        vehicle_type,
        center,
        timestamp,
        frame_index,
        bbox_height,
    ):

        self.last_seen_frame = (
            frame_index
        )

        self.last_timestamp = (
            timestamp
        )

        self.class_history.append(
            vehicle_type
        )

        counts = Counter(
            self.class_history
        )

        self.vehicle_type = (
            counts.most_common(1)[0][0]
        )

        self.centers.append(
            (
                timestamp,
                center
            )
        )

        cutoff = (
            timestamp
            - POSITION_HISTORY_SECONDS
        )

        while (
            len(self.centers) > 1
            and self.centers[0][0]
            < cutoff
        ):
            self.centers.popleft()

        movement_ratio = None

        if (
            len(self.centers) >= 2
            and bbox_height > 0
        ):

            oldest_timestamp, oldest_center = (
                self.centers[0]
            )

            time_difference = (
                timestamp
                - oldest_timestamp
            )

            if time_difference > 0.5:

                dx = (
                    center[0]
                    - oldest_center[0]
                )

                dy = (
                    center[1]
                    - oldest_center[1]
                )

                distance = math.sqrt(
                    dx * dx
                    + dy * dy
                )

                movement_ratio = (
                    distance
                    / max(
                        bbox_height,
                        1.0
                    )
                )

        self.movement_ratio = (
            movement_ratio
            if movement_ratio is not None
            else 0.0
        )

        stationary = False

        if movement_ratio is not None:

            stationary = (
                movement_ratio
                < STOP_MOVEMENT_RATIO
            )

        if stationary:

            if (
                self.stationary_since
                is None
            ):
                self.stationary_since = (
                    timestamp
                )

        else:

            self.stationary_since = None

        if (
            self.stationary_since
            is None
        ):

            self.status = "moving"

        else:

            stationary_duration = (
                timestamp
                - self.stationary_since
            )

            if (
                stationary_duration
                >= PARKED_TIME_THRESHOLD_SECONDS
            ):

                self.status = "parked"

            elif (
                stationary_duration
                >= WAITING_TIME_THRESHOLD_SECONDS
            ):

                self.status = (
                    "signal_waiting"
                )

            else:

                self.status = (
                    "signal_waiting"
                )


# ============================================================
# VEHICLE DETECTOR + TRACKER
# ============================================================

class VehicleDetectorTracker:

    def __init__(
        self,
        model_path=DEFAULT_MODEL,
        confidence=DEFAULT_CONFIDENCE,
    ):

        self.model_path = model_path

        self.confidence = (
            confidence
        )

        print(
            f"[Person1] Loading model: "
            f"{model_path}"
        )

        self.model = YOLO(
            model_path
        )

        self.tracks = {}

    def process_frame(
        self,
        frame,
        frame_index,
        timestamp,
        road_id,
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
            verbose=False,
        )

        detections = []

        if not results:
            return detections

        result = results[0]

        if result.boxes is None:
            return detections

        boxes = result.boxes

        if boxes.xyxy is None:
            return detections

        xyxy = boxes.xyxy.cpu().numpy()

        confidences = (
            boxes.conf.cpu().numpy()
            if boxes.conf is not None
            else []
        )

        class_ids = (
            boxes.cls.cpu().numpy().astype(int)
            if boxes.cls is not None
            else []
        )

        track_ids = (
            boxes.id.cpu().numpy().astype(int)
            if boxes.id is not None
            else []
        )

        if len(track_ids) == 0:
            return detections

        candidate_detections = []

        for index, bbox in enumerate(xyxy):

            if index >= len(track_ids):
                continue

            class_id = int(
                class_ids[index]
            )

            if class_id not in VEHICLE_CLASS_IDS:
                continue

            confidence = float(
                confidences[index]
            )

            track_id = int(
                track_ids[index]
            )

            x1, y1, x2, y2 = (
                map(
                    float,
                    bbox
                )
            )

            center_x = (
                x1 + x2
            ) / 2

            center_y = (
                y1 + y2
            ) / 2

            candidate_detections.append(
                {
                    "bbox": [
                        x1,
                        y1,
                        x2,
                        y2,
                    ],
                    "confidence": confidence,
                    "class_id": class_id,
                    "track_id": track_id,
                    "center": [
                        center_x,
                        center_y,
                    ],
                }
            )

        # ----------------------------------------------------
        # Remove duplicate overlapping detections.
        # ----------------------------------------------------

        candidate_detections.sort(
            key=lambda item:
            item["confidence"],
            reverse=True
        )

        filtered_detections = []

        for candidate in candidate_detections:

            duplicate = False

            for existing in filtered_detections:

                iou = calculate_iou(
                    candidate["bbox"],
                    existing["bbox"]
                )

                if (
                    iou
                    >= DUPLICATE_IOU_THRESHOLD
                ):

                    duplicate = True
                    break

            if not duplicate:
                filtered_detections.append(
                    candidate
                )

        # ----------------------------------------------------
        # Build records.
        # ----------------------------------------------------

        for candidate in filtered_detections:

            bbox = candidate["bbox"]

            class_id = candidate[
                "class_id"
            ]

            vehicle_type = (
                VEHICLE_CLASS_IDS[
                    class_id
                ]
            )

            track_id = candidate[
                "track_id"
            ]

            center = candidate[
                "center"
            ]

            bbox_height = max(
                bbox[3] - bbox[1],
                1.0
            )

            if track_id not in self.tracks:

                self.tracks[
                    track_id
                ] = TrackState(
                    track_id,
                    vehicle_type,
                    timestamp,
                    center,
                )

            track = self.tracks[
                track_id
            ]

            track.update(
                vehicle_type,
                center,
                timestamp,
                frame_index,
                bbox_height,
            )

            stationary_duration = 0.0

            if (
                track.stationary_since
                is not None
            ):

                stationary_duration = (
                    timestamp
                    - track.stationary_since
                )

            in_waiting_zone = (
                point_in_polygon(
                    center,
                    WAITING_ZONE
                )
                if WAITING_ZONE is not None
                else False
            )

            in_parking_zone = (
                point_in_polygon(
                    center,
                    PARKING_ZONE
                )
                if PARKING_ZONE is not None
                else False
            )

            if (
                track.stationary_since
                is None
            ):

                movement_state = "moving"

            elif (
                in_waiting_zone
                and stationary_duration
                >= WAITING_TIME_THRESHOLD_SECONDS
            ):

                movement_state = (
                    "signal_waiting"
                )

            elif (
                not in_waiting_zone
                and stationary_duration
                >= PARKED_TIME_THRESHOLD_SECONDS
                and (
                    PARKING_ZONE is None
                    or in_parking_zone
                )
            ):

                movement_state = "parked"

            else:

                movement_state = (
                    "signal_waiting"
                )

            record = {
                "road_id": road_id,
                "frame_index": frame_index,
                "timestamp": round(
                    timestamp,
                    3
                ),
                "vehicle_id": track_id,
                "vehicle_type": (
                    track.vehicle_type
                ),
                "bbox": [
                    round(
                        value,
                        2
                    )
                    for value in bbox
                ],
                "position": [
                    round(
                        center[0],
                        2
                    ),
                    round(
                        center[1],
                        2
                    ),
                ],
                "confidence": round(
                    candidate[
                        "confidence"
                    ],
                    4
                ),
                "movement_state": (
                    movement_state
                ),
                "stationary_duration": round(
                    stationary_duration,
                    3
                ),
                "in_waiting_zone": (
                    in_waiting_zone
                ),
                "in_parking_zone": (
                    in_parking_zone
                ),
            }

            detections.append(
                record
            )

        return detections


# ============================================================
# OVERLAY
# ============================================================

def draw_overlay(
    frame,
    detections,
    phase_number=None,
    live=False,
):

    for detection in detections:

        bbox = detection[
            "bbox"
        ]

        x1, y1, x2, y2 = (
            map(
                int,
                bbox
            )
        )

        state = detection.get(
            "movement_state",
            "unknown"
        )

        if state == "moving":

            color = (
                0,
                200,
                0
            )

        elif state == "signal_waiting":

            color = (
                0,
                200,
                255
            )

        elif state == "parked":

            color = (
                0,
                0,
                255
            )

        else:

            color = (
                255,
                255,
                255
            )

        cv2.rectangle(
            frame,
            (x1, y1),
            (x2, y2),
            color,
            2,
        )

        label = (
            f'{detection["vehicle_type"]} '
            f'ID:{detection["vehicle_id"]} '
            f'{state}'
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
        )

    if live:

        cv2.putText(
            frame,
            "LIVE",
            (20, 35),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 0, 255),
            2,
        )

    if phase_number is not None:

        cv2.putText(
            frame,
            f"PHASE: {phase_number}",
            (20, 70),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 255, 255),
            2,
        )

    return frame


# ============================================================
# PHASE OUTPUT
# ============================================================

def send_phase_data(
    phase_output,
    phase_number,
    road_id,
    road_name,
    source_name,
    start_time,
    end_time,
    phase_records,
):

    payload = {
        "phase_id": (
            f"{road_id}_PHASE_"
            f"{phase_number}"
        ),
        "phase": phase_number,
        "road_id": road_id,
        "road_name": road_name,
        "source": source_name,
        "start_time": round(
            start_time,
            3
        ),
        "end_time": round(
            end_time,
            3
        ),
        "record_count": len(
            phase_records
        ),
        "observations": phase_records,
    }

    phase_output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(
        phase_output,
        "a",
        encoding="utf-8",
    ) as f:

        f.write(
            json.dumps(
                payload
            )
            + "\n"
        )

    print(
        f"[Person1] "
        f"Phase {phase_number} "
        f"written: "
        f"{len(phase_records)} "
        f"observations"
    )


# ============================================================
# OUTPUT WRITERS
# ============================================================

def write_outputs(
    detections,
    output_path,
    csv_path,
):

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(
        output_path,
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            detections,
            f,
            indent=2,
        )

    csv_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

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
        encoding="utf-8",
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        for detection in detections:

            row = dict(
                detection
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


# ============================================================
# VIDEO SOURCE
# ============================================================

def open_source(source):

    try:

        if isinstance(
            source,
            int
        ):

            capture = cv2.VideoCapture(
                source
            )

        else:

            source_path = str(
                source
            )

            if (
                source_path.isdigit()
                and len(source_path) <= 2
            ):

                capture = cv2.VideoCapture(
                    int(source_path)
                )

            else:

                capture = cv2.VideoCapture(
                    source_path
                )

        if not capture.isOpened():

            raise RuntimeError(
                f"Could not open video "
                f"source: {source}"
            )

        return capture

    except Exception:

        raise RuntimeError(
            f"Could not open video "
            f"source: {source}"
        )


# ============================================================
# MAIN
# ============================================================

def main():

    parser = argparse.ArgumentParser(
        description=(
            "LaneLogic Person 1 - "
            "YOLO + ByteTrack detection "
            "with phase-wise output"
        )
    )

    parser.add_argument(
        "--source",
        required=True,
    )

    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
    )

    parser.add_argument(
        "--confidence",
        type=float,
        default=DEFAULT_CONFIDENCE,
    )

    parser.add_argument(
        "--output",
        default="output/detections.json",
    )

    parser.add_argument(
        "--csv",
        default="output/vehicle_data.csv",
    )

    parser.add_argument(
        "--show",
        action="store_true",
    )

    parser.add_argument(
        "--max-frames",
        type=int,
        default=0,
    )

    parser.add_argument(
        "--live",
        action="store_true",
    )

    parser.add_argument(
        "--phase-seconds",
        type=float,
        default=DEFAULT_PHASE_SECONDS,
    )

    parser.add_argument(
        "--phase-output",
        default=DEFAULT_PHASE_OUTPUT,
    )

    parser.add_argument(
        "--road-id",
        default=ROAD_ID,
    )

    parser.add_argument(
        "--road-name",
        default="",
    )

    parser.add_argument(
        "--source-name",
        default="",
    )

    parser.add_argument(
        "--clear-phase-output",
        action="store_true",
    )

    args = parser.parse_args()

    # --------------------------------------------------------
    # Source
    # --------------------------------------------------------

    source = args.source

    if (
        isinstance(
            source,
            str
        )
        and source.isdigit()
    ):

        source = int(
            source
        )

    # --------------------------------------------------------
    # Phase output
    # --------------------------------------------------------

    phase_output = Path(
        args.phase_output
    )

    if args.clear_phase_output:

        if phase_output.exists():

            phase_output.unlink()

        done_file = (
            phase_output.with_suffix(
                ".done"
            )
        )

        if done_file.exists():

            done_file.unlink()

    # --------------------------------------------------------
    # Source name
    # --------------------------------------------------------

    source_name = (
        args.source_name
        if args.source_name
        else Path(
            str(args.source)
        ).name
    )

    # --------------------------------------------------------
    # Open source
    # --------------------------------------------------------

    capture = open_source(
        source
    )

    fps = capture.get(
        cv2.CAP_PROP_FPS
    )

    if not fps or fps <= 0:

        fps = 30.0

    resize_width = 960

    tracker = VehicleDetectorTracker(
        model_path=args.model,
        confidence=args.confidence,
    )

    all_detections = []

    phase_records = []

    phase_number = 1

    phase_start_time = 0.0

    processing_start = time.time()

    frame_index = 0

    print(
        "\n============================================================"
    )

    print(
        "LANELOGIC - PERSON 1"
    )

    print(
        f"Road ID: {args.road_id}"
    )

    print(
        f"Road Name: {args.road_name}"
    )

    print(
        f"Source: {source_name}"
    )

    print(
        f"Phase duration: "
        f"{args.phase_seconds} seconds"
    )

    print(
        f"Phase output: "
        f"{phase_output}"
    )

    print(
        "============================================================"
    )

    # --------------------------------------------------------
    # Processing loop
    # --------------------------------------------------------

    while True:

        ret, frame = capture.read()

        if not ret:

            if args.live:

                time.sleep(
                    0.05
                )

                continue

            break

        if args.live:

            timestamp = (
                time.time()
                - processing_start
            )

        else:

            timestamp = (
                frame_index
                / fps
            )

        # Resize
        if (
            resize_width
            and frame.shape[1]
            > resize_width
        ):

            scale = (
                resize_width
                / frame.shape[1]
            )

            frame = cv2.resize(
                frame,
                (
                    resize_width,
                    int(
                        frame.shape[0]
                        * scale
                    ),
                ),
            )

        detections = (
            tracker.process_frame(
                frame,
                frame_index,
                timestamp,
                args.road_id,
            )
        )

        all_detections.extend(
            detections
        )

        phase_records.extend(
            detections
        )

        # ----------------------------------------------------
        # Phase boundary
        # ----------------------------------------------------

        if (
            timestamp
            - phase_start_time
            >= args.phase_seconds
        ):

            send_phase_data(
                phase_output,
                phase_number,
                args.road_id,
                args.road_name,
                source_name,
                phase_start_time,
                timestamp,
                phase_records,
            )

            phase_records = []

            phase_number += 1

            phase_start_time = timestamp

        # ----------------------------------------------------
        # Display
        # ----------------------------------------------------

        if args.show:

            display_frame = (
                draw_overlay(
                    frame.copy(),
                    detections,
                    phase_number,
                    args.live,
                )
            )

            cv2.imshow(
                "LaneLogic - Person 1",
                display_frame,
            )

            key = (
                cv2.waitKey(1)
                & 0xFF
            )

            if key == ord("q"):

                print(
                    "\n[Person1] "
                    "Stopping current video..."
                )

                break

        frame_index += 1

        if (
            args.max_frames > 0
            and frame_index
            >= args.max_frames
        ):

            break

    # --------------------------------------------------------
    # Final partial phase
    # --------------------------------------------------------

    final_timestamp = (
        timestamp
        if frame_index > 0
        else 0.0
    )

    if phase_records:

        send_phase_data(
            phase_output,
            phase_number,
            args.road_id,
            args.road_name,
            source_name,
            phase_start_time,
            final_timestamp,
            phase_records,
        )

    # --------------------------------------------------------
    # Cleanup
    # --------------------------------------------------------

    capture.release()

    cv2.destroyAllWindows()

    # --------------------------------------------------------
    # Complete video output
    # --------------------------------------------------------

    write_outputs(
        all_detections,
        Path(args.output),
        Path(args.csv),
    )

    # --------------------------------------------------------
    # Done marker
    # --------------------------------------------------------

    done_file = (
        phase_output.with_suffix(
            ".done"
        )
    )

    done_file.touch()

    print(
        "\n============================================================"
    )

    print(
        "[Person1] VIDEO COMPLETED"
    )

    print(
        f"Road: {args.road_id}"
    )

    print(
        f"Total frames: {frame_index}"
    )

    print(
        f"Total detections: "
        f"{len(all_detections)}"
    )

    print(
        f"JSON: {args.output}"
    )

    print(
        f"CSV: {args.csv}"
    )

    print(
        f"Phase stream: "
        f"{phase_output}"
    )

    print(
        "============================================================"
    )


if __name__ == "__main__":
    main()