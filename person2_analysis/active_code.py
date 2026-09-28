


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