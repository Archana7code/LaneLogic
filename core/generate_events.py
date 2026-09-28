"""
LaneLogic - Event Generation Utility
====================================
Transforms frame-level detections (detections.json or detection streams)
into canonical time-bounded ObstructionEvent records.
Can run standalone or push events to the Person 3 backend.

Usage:
    python core/generate_events.py --input person1_detection/output/detections.json --output person1_detection/output/obstruction_events.json
    python core/generate_events.py --input person1_detection/output/detections.json --api http://localhost:8000
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import requests

from core.event_engine import ObstructionEventEngine


def generate_events_from_file(
    detections_path: Path,
    roi_config_path: Path,
    output_path: Optional[Path] = None,
    api_url: Optional[str] = None,
):
    with open(detections_path, "r", encoding="utf-8") as f:
        detections = json.load(f)

    roi_cfg = {}
    if roi_config_path.exists():
        with open(roi_config_path, "r", encoding="utf-8") as f:
            roi_cfg = json.load(f)

    engine = ObstructionEventEngine(
        stationary_threshold_sec=4.0,
        max_disappearance_gap_sec=3.0,
        road_width_m=float(roi_cfg.get("road_width_meters", 10.0)),
        road_length_m=float(roi_cfg.get("road_length_meters", 120.0)),
        road_polygon=roi_cfg.get("road_polygon"),
        queue_polygon=roi_cfg.get("signal_queue_zone", {}).get("polygon")
        if isinstance(roi_cfg.get("signal_queue_zone"), dict)
        else roi_cfg.get("signal_queue_zone"),
    )

    events = engine.process_batch(detections)
    print(f"[EventEngine] Processed {len(detections)} frame detections -> {len(events)} time-bounded obstruction events.")

    events_data = [e.model_dump() for e in events]

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(events_data, f, indent=2)
        print(f"[EventEngine] Saved obstruction events to: {output_path}")

    if api_url:
        try:
            resp = requests.post(f"{api_url.rstrip('/')}/events/bulk", json={"events": events_data}, timeout=10)
            resp.raise_for_status()
            print(f"[EventEngine] Successfully pushed {len(events)} events to backend API at {api_url}.")
        except Exception as e:
            print(f"[EventEngine] Warning: Could not push events to {api_url}: {e}")

    return events


def main():
    parser = argparse.ArgumentParser(description="Generate canonical ObstructionEvents from detections.")
    parser.add_argument("--input", default="person1_detection/output/detections.json", help="Path to detections.json")
    parser.add_argument("--roi", default="person2_analysis/roi_config.json", help="Path to roi_config.json")
    parser.add_argument("--output", default="person1_detection/output/obstruction_events.json", help="Path to save obstruction_events.json")
    parser.add_argument("--api", default=None, help="Optional Person 3 API base URL (e.g. http://localhost:8000)")
    args = parser.parse_args()

    generate_events_from_file(
        detections_path=Path(args.input),
        roi_config_path=Path(args.roi),
        output_path=Path(args.output) if args.output else None,
        api_url=args.api,
    )


if __name__ == "__main__":
    main()
