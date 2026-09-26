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

import requests


# ============================================================
# CONFIGURATION
# ============================================================

BACKEND_URL_DEFAULT = "http://localhost:8000"

# Minimum number of historical windows needed before a road can be
# called "chronic" at all.
MIN_WINDOWS_REQUIRED = 1 # change, org : 3

# A road is chronic when at least this fraction of its historical
# windows show a meaningful parked-vehicle problem.
CHRONIC_WINDOW_FRACTION = 0.00 # change , org : 0.40

# A window counts as "meaningful blockage" only if BOTH the vehicle
# count and the parked-space percentage clear these bars. Requiring
# both prevents a single briefly-parked car from counting the same
# as a genuine, space-consuming blockage.
MIN_PARKED_VEHICLES_FOR_RECURRENCE = 1
CHRONIC_MIN_PARKED_SPACE_PCT = 0.0 # change , org : 5.0

# Threshold for flagging a "current problem" recommendation even when
# there isn't yet enough history to call the road chronic.
CURRENT_PROBLEM_PARKED_VEHICLES = 1
CURRENT_PROBLEM_MIN_PARKED_SPACE_PCT = 0.0 # change, org : 3.0


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
# CHRONIC ROAD EVALUATION
# ============================================================

def analyse_road(road_id, observations):
    """
    Analyse one road's historical observations and decide whether it is
    a Chronic Problem Zone.
    """
    if not observations:
        return {
            "road_id": road_id,
            "chronic": False,
            "total_windows": 0,
            "parked_windows": 0,
            "recurrence_fraction": 0.0,
            "average_parked_space_pct": 0.0,
            "dominant_cause": "normal",
        }

    total_windows = len(observations)
    parked_windows = 0
    parked_space_values = []
    causes = []

    for observation in observations:
        parked_count = get_parked_vehicle_count(observation)
        parked_space = get_parked_space_pct(observation)
        parked_space_values.append(parked_space)

        # A window only counts toward recurrence if BOTH the vehicle
        # count AND the parked-space percentage clear their thresholds.
        if (
            parked_count >= MIN_PARKED_VEHICLES_FOR_RECURRENCE
            and parked_space >= CHRONIC_MIN_PARKED_SPACE_PCT
        ):
            parked_windows += 1

        cause = get_cause(observation)
        if cause != "normal":
            causes.append(cause)

    recurrence_fraction = parked_windows / total_windows
    average_parked_space = (
        sum(parked_space_values) / len(parked_space_values)
        if parked_space_values
        else 0.0
    )

    # chronic = (
    #     total_windows >= MIN_WINDOWS_REQUIRED
    #     and recurrence_fraction >= CHRONIC_WINDOW_FRACTION
    # )

    chronic = parked_windows >= 1

    dominant_cause = (
        Counter(causes).most_common(1)[0][0] if causes else "normal"
    )

    return {
        "road_id": road_id,
        "chronic": chronic,
        "total_windows": total_windows,
        "parked_windows": parked_windows,
        "recurrence_fraction": round(recurrence_fraction, 3),
        "average_parked_space_pct": round(average_parked_space, 3),
        "dominant_cause": dominant_cause,
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

def build_recommendation_set(road_id, cause, severity_pct, rationale_detail):
    """
    Build ALL candidate interventions for a cause, ranked by
    benefit-to-difficulty ratio, highest value first.
    """
    candidates = CAUSE_INTERVENTION_MAP.get(cause, CAUSE_INTERVENTION_MAP["unclassified"])

    scored = []
    for intervention, difficulty, benefit_weight in candidates:
        expected_benefit = round(min(100.0, severity_pct * benefit_weight), 1)
        ranking_score = expected_benefit / max(1.0, difficulty)
        scored.append({
            "road_id": road_id,
            "cause": cause,
            "intervention": intervention,
            "expected_benefit_score": expected_benefit,
            "implementation_difficulty_score": float(difficulty),
            "rationale": (
                f"Cause '{cause}' observed with {severity_pct:.2f}% parked-space "
                f"blockage. {rationale_detail} Recommendation is a rule-based "
                f"suggestion, not a guaranteed real-world outcome."
            ),
            "_ranking_score": ranking_score,
        })

    scored.sort(key=lambda r: r["_ranking_score"], reverse=True)
    for i, r in enumerate(scored, start=1):
        r["priority_rank"] = i
        r.pop("_ranking_score")

    return scored



def build_chronic_zone_payload(analysis):
    """
    Build the payload matching schemas.ChronicZoneIn exactly: road_id,
    dominant_cause, occurrence_count, severity_score, notes.
    """
    severity_score = round(
        min(
            100.0,
            analysis["recurrence_fraction"] * 60.0
            + min(40.0, analysis["average_parked_space_pct"] / 100.0 * 40.0),
        ),
        1,
    )

    return {
        "road_id": analysis["road_id"],
        "dominant_cause": analysis["dominant_cause"],
        "occurrence_count": analysis["parked_windows"],
        "severity_score": severity_score,
        "notes": "Auto-flagged by Person 4 rule-based recurrence analysis.",
    }


# ============================================================
# SEND HELPERS (bare lists, matching FastAPI's List[...] parameters)
# ============================================================

def send_recommendations(api_base, recommendations):
    if not recommendations:
        return
    try:
        post_json(api_base, "/recommendations/bulk", recommendations)
        print(f"      \u2713 {len(recommendations)} recommendation(s) sent to backend")
    except requests.RequestException as e:
        print(f"      \u26a0 Could not send recommendation(s): {e}")


def send_chronic_zone(api_base, analysis):
    if not analysis.get("chronic"):
        return
    payload = build_chronic_zone_payload(analysis)
    try:
        post_json(api_base, "/chronic-zones/bulk", [payload])
        print("      \u2713 Chronic zone sent to backend")
    except requests.RequestException as e:
        print(f"      \u26a0 Could not send chronic zone: {e}")


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
            print("  STATUS             : \U0001F534 CHRONIC ZONE")

            rationale_detail = (
                f"Parked vehicles were observed in {analysis['parked_windows']} "
                f"of {analysis['total_windows']} historical windows."
            )
            recommendations.append(
                build_recommendation_set(
                    road_id,
                    analysis["dominant_cause"],
                    analysis["average_parked_space_pct"],
                    rationale_detail,
                )
            )
            send_chronic_zone(api_base, analysis)

        else:
            current_problem = get_current_problem(latest)
            if current_problem:
                print("  STATUS             : CURRENT PROBLEM (not yet chronic)")
                rationale_detail = (
                    f"{current_problem['parked_vehicle_count']} parked vehicle(s) "
                    f"currently detected; more history is needed before calling "
                    f"this road chronic."
                )
                recommendations.append(
                    build_recommendation(
                        road_id,
                        current_problem["cause"],
                        current_problem["parked_space_pct"],
                        rationale_detail,
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