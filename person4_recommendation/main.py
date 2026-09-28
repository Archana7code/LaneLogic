"""
LaneLogic - PERSON 4: Recurrence + Recommendation Analysis
============================================================

Role:
    Historical recurrence + recommendation engine.

Pipeline:
    Person 3 Backend (/roads, /roads/{road_id}/history)
          |
          v
    Person 4 (this file)
          |
          v
    Chronic Zone Detection  -> POST /chronic-zones/bulk
    Cause-based Recommendation -> POST /recommendations/bulk
          |
          v
    Person 3 Backend -> Frontend Dashboard

IMPORTANT SCHEMA NOTES (matched against the real Person 3 backend):
    - GET /roads returns roads with field "id", NOT "road_id".
    - POST /chronic-zones/bulk expects a BARE JSON LIST of objects with
      exactly: road_id, dominant_cause, occurrence_count, severity_score,
      notes (optional). No wrapping object.
    - POST /recommendations/bulk expects a BARE JSON LIST of objects with
      exactly: road_id, cause, intervention, expected_benefit_score,
      implementation_difficulty_score, priority_rank, rationale.
      No wrapping object, and no extra/renamed fields.
    - Person 2's real cause values are only ever one of:
      "traffic_signal_queue", "loading_unloading", "school_drop_off",
      "illegal_parking", "general_congestion", "normal", "unclassified".
    - "parked_space_pct" IS safe to read from /roads/{id}/history, because
      Person 3's /analysis/bulk endpoint backfills parked_space_pct from
      blocked_pct at storage time if Person 2 didn't send it directly.

Run:
    python main.py
    python main.py --api http://localhost:8000
"""

import argparse
from collections import Counter, defaultdict
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import requests

from core.interventions import RecommendationDecisionEngine
from core.recurrence import HistoricalRecurrenceEngine
from core.cause_classifier import ExplainableCauseClassifier, normalize_cause_name
from core.contracts import ObstructionEvent
from core.config import (
    MIN_EVENTS_FOR_CHRONIC,
    CHRONIC_RECURRENCE_THRESHOLD,
    CHRONIC_MIN_PARKED_SPACE_PCT,
    MIN_PARKED_VEHICLES_FOR_RECURRENCE,
)

rec_decision_engine = RecommendationDecisionEngine()
cause_classifier = ExplainableCauseClassifier()

# ============================================================
# CONFIGURATION
# Meaningful, configurable evidence-based thresholds
# ============================================================

BACKEND_URL_DEFAULT = "http://localhost:8000"

# Minimum number of historical observations/windows required before a road can qualify as chronic
MIN_WINDOWS_REQUIRED = MIN_EVENTS_FOR_CHRONIC

# Thresholds for flagging a "current problem" recommendation
CURRENT_PROBLEM_PARKED_VEHICLES = MIN_PARKED_VEHICLES_FOR_RECURRENCE
CURRENT_PROBLEM_MIN_PARKED_SPACE_PCT = CHRONIC_MIN_PARKED_SPACE_PCT

recurrence_engine = HistoricalRecurrenceEngine(
    min_events_for_chronic=MIN_WINDOWS_REQUIRED,
    chronic_recurrence_threshold=CHRONIC_RECURRENCE_THRESHOLD,
)


# ============================================================
# CAUSE -> INTERVENTION MAP
# Keys MUST match Person 2's real classify_cause() output exactly.
# (intervention text, implementation_difficulty 0-100, benefit_weight)
# ============================================================

CAUSE_INTERVENTION_MAP = {
    "illegal_parking": [
        ("Install no-parking signage and increase enforcement during peak hours.", 20, 1.0),
        ("Create a designated parking bay to absorb existing demand.", 55, 1.15),
    ],
    "loading_unloading": [
        ("Restrict loading to off-peak hours only.", 25, 0.85),
        ("Create a designated loading/unloading zone with a time-window restriction.", 45, 1.1),
    ],
    "traffic_signal_queue": [
        ("Review and adjust signal green-phase timing.", 40, 0.8),
        ("Add a clearly marked waiting lane near the junction.", 60, 1.0),
    ],
    "school_drop_off": [
        ("Stagger school opening/closing times to spread demand.", 30, 0.7),
        ("Create a dedicated pickup/drop-off zone.", 50, 1.1),
    ],
    "general_congestion": [
        ("Review lane capacity and signal timing during peak hours.", 50, 0.9),
    ],
    "unclassified": [
        ("Inspect the location for recurring roadside obstruction before intervening.", 10, 0.4),
    ],
}


# ============================================================
# HTTP HELPERS
# ============================================================

def fetch_json(api_base, path):
    response = requests.get(f"{api_base}{path}", timeout=10)
    response.raise_for_status()
    return response.json()


def post_json(api_base, path, payload):
    response = requests.post(f"{api_base}{path}", json=payload, timeout=10)
    response.raise_for_status()
    return response.json()


# ============================================================
# FIELD EXTRACTION HELPERS
# ============================================================

def get_parked_vehicle_count(observation):
    """
    Parked vehicle count, read from movement_state_breakdown, which is
    what Person 2 actually sends (state_breakdown() in their code).
    """
    breakdown = observation.get("movement_state_breakdown", {})
    if isinstance(breakdown, dict):
        try:
            return int(breakdown.get("parked", 0))
        except (TypeError, ValueError):
            pass
    return 0


def get_parked_space_pct(observation):
    """
    Parked-space percentage. Safe to read directly: Person 3's backend
    backfills this from blocked_pct at storage time if Person 2 didn't
    send it, so /roads/{id}/history always has a real value here.
    """
    try:
        return float(observation.get("parked_space_pct", 0.0))
    except (TypeError, ValueError):
        return 0.0


def get_cause(observation):
    cause = observation.get("cause") or "unclassified"
    return str(cause)


def get_latest_observation(observations):
    if not observations:
        return None
    # Person 2 does not send a "timestamp" per window; window_index is
    # the reliable ordering field for window-level observations.
    return max(observations, key=lambda x: x.get("window_index", 0))


# ============================================================
# CHRONIC ROAD EVALUATION VIA HISTORICAL RECURRENCE ENGINE
# ============================================================

def analyse_road(road_id, observations):
    """
    Analyse one road's historical observations using the authoritative
    HistoricalRecurrenceEngine to determine empirical recurrence, peak hours,
    evidence summary, and chronic zone qualification.
    """
    if not observations:
        return {
            "road_id": road_id,
            "chronic": False,
            "single_event_severity": False,
            "total_windows": 0,
            "parked_windows": 0,
            "recurrence_fraction": 0.0,
            "average_parked_space_pct": 0.0,
            "dominant_cause": "normal",
            "evidence_summary": "No historical observations available.",
            "peak_hours": [],
            "severity": "normal",
        }

    # Authoritative engine analysis
    pattern = recurrence_engine.analyze_windows(
        road_id=road_id,
        observations=observations,
        observation_period_days=1,
        min_parked_space_pct=CHRONIC_MIN_PARKED_SPACE_PCT,
    )

    return {
        "road_id": road_id,
        "chronic": pattern.is_chronic,
        "single_event_severity": pattern.single_event_severity,
        "total_windows": len(observations),
        "parked_windows": pattern.total_events,
        "recurrence_fraction": pattern.recurrence_score,
        "average_parked_space_pct": pattern.average_road_space_loss_pct,
        "dominant_cause": pattern.dominant_cause,
        "evidence_summary": pattern.evidence_summary,
        "peak_hours": pattern.peak_hours,
        "severity": pattern.severity,
        "pattern": pattern,
    }


def get_current_problem(latest_observation):
    """
    Decide whether the latest single window shows a meaningful, current
    problem, even if there isn't enough history to call it chronic.
    """
    if latest_observation is None:
        return None

    parked_count = get_parked_vehicle_count(latest_observation)
    parked_space = get_parked_space_pct(latest_observation)
    cause = get_cause(latest_observation)

    is_problem = (
        parked_count >= CURRENT_PROBLEM_PARKED_VEHICLES
        and parked_space >= CURRENT_PROBLEM_MIN_PARKED_SPACE_PCT
    )
    if not is_problem:
        return None

    if cause == "normal":
        cause = "unclassified"

    return {
        "parked_vehicle_count": parked_count,
        "parked_space_pct": parked_space,
        "cause": cause,
    }


# ============================================================
# RECOMMENDATION BUILDING (matches Person 3's RecommendationIn exactly)
# ============================================================

def build_recommendation_set(
    road_id,
    cause,
    severity_pct,
    rationale_detail,
    duration_sec=30.0,
    recurrence_score=0.5,
):
    """
    Build candidate interventions using the multi-criteria decision engine,
    matching Person 3's RecommendationIn schema exactly.
    Uses actual classifier confidence rather than hardcoded metrics.
    """
    norm_cause = normalize_cause_name(cause)
    pred = cause_classifier.classify(
        vehicle_type="car",
        duration_sec=duration_sec,
        road_space_loss_pct=severity_pct,
        recurrence_score=recurrence_score,
    )
    actual_confidence = pred.confidence

    recs = rec_decision_engine.generate_recommendations(
        road_id=road_id,
        cause=norm_cause,
        cause_confidence=actual_confidence,
        road_space_loss_pct=severity_pct,
        recurrence_score=recurrence_score,
        evidence_summary=rationale_detail,
    )
    return [
        {
            "road_id": r.road_id,
            "cause": r.cause,
            "intervention": r.intervention,
            "expected_benefit_score": r.expected_benefit_score,
            "implementation_difficulty_score": r.implementation_difficulty_score,
            "priority_rank": r.priority_rank,
            "rationale": r.rationale,
        }
        for r in recs
    ]


def build_chronic_zone_payload(analysis):
    """
    Build the payload matching schemas.ChronicZoneIn exactly: road_id,
    dominant_cause, occurrence_count, severity_score, notes.
    Notes are enriched with evidence traceability instead of placeholder strings.
    """
    severity_score = round(
        min(
            100.0,
            analysis["recurrence_fraction"] * 60.0
            + min(40.0, analysis["average_parked_space_pct"] / 100.0 * 40.0),
        ),
        1,
    )

    peak_str = ", ".join(f"{h:02d}:00" for h in analysis.get("peak_hours", [])) or "varied"
    evidence_text = analysis.get("evidence_summary") or "Evaluated via HistoricalRecurrenceEngine."
    notes = (
        f"{evidence_text} Dominant cause: {analysis['dominant_cause']}. "
        f"Recurrence score: {analysis['recurrence_fraction']:.2f}. "
        f"Peak hours: {peak_str}. Severity: {analysis.get('severity', 'moderate')}."
    )

    return {
        "road_id": analysis["road_id"],
        "dominant_cause": analysis["dominant_cause"],
        "occurrence_count": analysis["parked_windows"],
        "severity_score": severity_score,
        "notes": notes,
    }


# ============================================================
# SEND HELPERS (bare lists, matching FastAPI's List[...] parameters)
# ============================================================

def send_recommendations(api_base, recommendations):
    if not recommendations:
        return
    try:
        post_json(api_base, "/recommendations/bulk", recommendations)
        print(f"      [OK] {len(recommendations)} recommendation(s) sent to backend")
    except requests.RequestException as e:
        print(f"      [WARN] Could not send recommendation(s): {e}")


def send_chronic_zone(api_base, analysis):
    if not analysis.get("chronic"):
        return
    payload = build_chronic_zone_payload(analysis)
    try:
        post_json(api_base, "/chronic-zones/bulk", [payload])
        print("      [OK] Chronic zone sent to backend")
    except requests.RequestException as e:
        print(f"      [WARN] Could not send chronic zone: {e}")


# ============================================================
# MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="LaneLogic Person 4: Recurrence & Recommendation"
    )
    parser.add_argument(
        "--api", default=BACKEND_URL_DEFAULT, help="Person 3 FastAPI base URL"
    )
    args = parser.parse_args()
    api_base = args.api.rstrip("/")

    print()
    print("=" * 70)
    print("LANELOGIC - PERSON 4")
    print("RECURRENCE + RECOMMENDATION ANALYSIS")
    print("=" * 70)

    try:
        roads = fetch_json(api_base, "/roads")
    except requests.RequestException as e:
        print(f"[ERROR] Could not connect to backend: {e}")
        print("Make sure Person 3 is running: uvicorn main:app --reload --port 8000")
        return

    if not roads:
        print("No roads found in backend.")
        return

    print(f"[Person4] Evaluating {len(roads)} road(s)...")
    print()

    chronic_count = 0

    for road in roads:
        # IMPORTANT: Person 3 returns the road's identifier as "id",
        # not "road_id". Using the wrong key here silently skips every
        # road, so this line is the most important one in the file.
        road_id = road.get("id")
        if not road_id:
            continue

        try:
            history = fetch_json(api_base, f"/roads/{road_id}/history")
        except requests.RequestException as e:
            print(f"  [WARN] Skipping {road_id}, could not fetch history: {e}")
            continue

        if not history:
            print(f"ROAD: {road_id}")
            print("  No historical observations.")
            print("-" * 70)
            continue

        analysis = analyse_road(road_id, history)
        latest = get_latest_observation(history)

        print(f"ROAD: {road_id}")
        print(f"  Historical windows : {analysis['total_windows']}")
        print(f"  Parked windows     : {analysis['parked_windows']}")
        print(f"  Recurrence         : {analysis['recurrence_fraction'] * 100:.1f}%")
        print(f"  Avg parked space   : {analysis['average_parked_space_pct']:.2f}%")
        print(f"  Dominant cause     : {analysis['dominant_cause']}")

        recommendations = []

        if analysis["chronic"]:
            chronic_count += 1
            print("  STATUS             : [CRITICAL] CHRONIC ZONE")

            rationale_detail = (
                f"Parked vehicles observed across {analysis['parked_windows']} of {analysis['total_windows']} "
                f"historical windows with {analysis['recurrence_fraction']:.2f} recurrence score. {analysis['evidence_summary']}"
            )
            recommendations.extend(
                build_recommendation_set(
                    road_id=road_id,
                    cause=analysis["dominant_cause"],
                    severity_pct=analysis["average_parked_space_pct"],
                    rationale_detail=rationale_detail,
                    duration_sec=analysis.get("pattern").average_duration_sec if analysis.get("pattern") else 30.0,
                    recurrence_score=analysis["recurrence_fraction"],
                )
            )
            send_chronic_zone(api_base, analysis)

        elif analysis.get("single_event_severity"):
            print("  STATUS             : [WARNING] PROLONGED / SEVERE OBSTRUCTION (isolated, not yet chronic)")
            rationale_detail = (
                f"Single severe/prolonged obstruction detected ({analysis['average_parked_space_pct']:.1f}% space loss). "
                f"Requires operational monitoring; not yet qualified as recurring chronic problem."
            )
            recommendations.extend(
                build_recommendation_set(
                    road_id=road_id,
                    cause=analysis["dominant_cause"],
                    severity_pct=analysis["average_parked_space_pct"],
                    rationale_detail=rationale_detail,
                    duration_sec=60.0,
                    recurrence_score=0.20,
                )
            )

        else:
            current_problem = get_current_problem(latest)
            if current_problem:
                print("  STATUS             : CURRENT PROBLEM (not yet chronic)")
                rationale_detail = (
                    f"{current_problem['parked_vehicle_count']} parked vehicle(s) "
                    f"currently detected; more history is needed before calling "
                    f"this road chronic."
                )
                recommendations.extend(
                    build_recommendation_set(
                        road_id=road_id,
                        cause=current_problem["cause"],
                        severity_pct=current_problem["parked_space_pct"],
                        rationale_detail=rationale_detail,
                        duration_sec=15.0,
                        recurrence_score=0.10,
                    )
                )
            else:
                print("  STATUS             : Normal")
                print("  No recommendation required.")

        if recommendations:
            for rec in recommendations:
                print(f"  Recommendation     : {rec['intervention']}")
                print(f"    Expected benefit : {rec['expected_benefit_score']}")
                print(f"    Difficulty       : {rec['implementation_difficulty_score']}")
            send_recommendations(api_base, recommendations)

        print("-" * 70)

    print()
    print("=" * 70)
    print(f"CHRONIC ZONES DETECTED: {chronic_count}")
    print("=" * 70)
    print()


if __name__ == "__main__":
    main()