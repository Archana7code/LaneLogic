# """
# LaneLogic - PERSON 4: Recurrence & Recommendation
# ====================================================
# Role in the pipeline: the "reasoning and recommendation" part.

# What this file does:
#   1. Pulls historical window observations for every road from Person 3's
#      backend API (GET /roads, GET /roads/{road_id}/history).
#   2. Applies a configurable, rule-based test to decide whether a road is a
#      "Chronic Problem Zone" (e.g. blocked in a large fraction of observed
#      windows, across enough total windows to be meaningful).
#   3. For each chronic road, looks up its dominant cause and maps it to one
#      or more candidate interventions using a fixed cause -> intervention
#      table (see CAUSE_INTERVENTION_MAP below).
#   4. Scores each candidate intervention with two simple, transparent
#      0-100 rule-based scores:
#        - expected_benefit_score : derived from how much road space is
#          typically recovered when that cause's blockage clears, and how
#          often the cause occurs.
#        - implementation_difficulty_score : a fixed per-intervention-type
#          estimate of how disruptive/costly the intervention typically is.
#      Recommendations are ranked by benefit-to-difficulty, NOT by any
#      claim of guaranteed real-world outcome.
#   5. Pushes chronic-zone flags and recommendations back to Person 3's
#      backend via POST /chronic-zones/bulk and POST /recommendations/bulk.

# IMPORTANT: every score here is an explainable heuristic for demo purposes.
# This module never claims a guaranteed real-world result.

# Run:
#   python main.py --api http://localhost:8000
# """

# import argparse
# from collections import defaultdict

# import requests

# # ---------------------------------------------------------------------------
# # Configurable rules for flagging a "Chronic Problem Zone"
# # ---------------------------------------------------------------------------

# MIN_WINDOWS_REQUIRED = 6          # need at least this many observed windows
# CHRONIC_BLOCKED_WINDOW_FRACTION = 0.4  # fraction of windows that must be "moderate"/"severe"
# CHRONIC_MIN_AVG_BLOCKED_PCT = 15.0


# CAUSE_INTERVENTION_MAP = {
#     "illegal_parking": [
#         {"intervention": "No-parking enforcement + signage", "difficulty": 20, "benefit_weight": 1.0},
#         {"intervention": "Designated parking bay relocation", "difficulty": 55, "benefit_weight": 1.1},
#     ],
#     "loading_unloading": [
#         {"intervention": "Designated loading bay with time restriction", "difficulty": 45, "benefit_weight": 1.0},
#         {"intervention": "Restrict loading to off-peak hours only", "difficulty": 25, "benefit_weight": 0.8},
#     ],
#     "traffic_signal_queue": [
#         {"intervention": "Signal timing / green-phase review", "difficulty": 60, "benefit_weight": 0.9},
#         {"intervention": "Additional turning lane at junction", "difficulty": 80, "benefit_weight": 1.2},
#     ],
#     "school_drop_off": [
#         {"intervention": "Dedicated pickup/drop-off zone", "difficulty": 50, "benefit_weight": 1.0},
#         {"intervention": "Staggered school timing coordination", "difficulty": 35, "benefit_weight": 0.7},
#     ],
#     "general_congestion": [
#         {"intervention": "Lane-usage review / informal auto-stand relocation", "difficulty": 50, "benefit_weight": 0.9},
#     ],
#     "unclassified": [
#         {"intervention": "Manual site survey recommended before intervention", "difficulty": 10, "benefit_weight": 0.4},
#     ],
# }


# def fetch_json(api_base, path):
#     resp = requests.get(f"{api_base}{path}", timeout=10)
#     resp.raise_for_status()
#     return resp.json()


# def post_json(api_base, path, payload):
#     resp = requests.post(f"{api_base}{path}", json=payload, timeout=10)
#     resp.raise_for_status()
#     return resp.json()


# def evaluate_road(history):
#     """
#     history: list of observation dicts (as returned by
#     GET /roads/{road_id}/history), each with occupancy_pct, blocked_pct, cause.

#     Returns (is_chronic, dominant_cause, occurrence_count, severity_score)
#     or (False, None, 0, 0.0) if not enough data / not chronic.
#     """
#     if len(history) < MIN_WINDOWS_REQUIRED:
#         return False, None, 0, 0.0

#     blocked_windows = [h for h in history if h["blocked_pct"] >= CHRONIC_MIN_AVG_BLOCKED_PCT]
#     fraction_blocked = len(blocked_windows) / len(history)

#     if fraction_blocked < CHRONIC_BLOCKED_WINDOW_FRACTION:
#         return False, None, 0, 0.0

#     cause_counts = defaultdict(int)
#     for h in blocked_windows:
#         cause_counts[h["cause"]] += 1
#     dominant_cause = max(cause_counts, key=cause_counts.get)

#     avg_blocked_pct = sum(h["blocked_pct"] for h in history) / len(history)
#     # Severity score: blends how often it's blocked with how badly.
#     severity_score = round(min(100.0, fraction_blocked * 60 + (avg_blocked_pct / 100.0) * 40 * 2), 1)

#     return True, dominant_cause, len(blocked_windows), severity_score


# def build_recommendations(road_id, dominant_cause, occurrence_count, severity_score):
#     candidates = CAUSE_INTERVENTION_MAP.get(dominant_cause, CAUSE_INTERVENTION_MAP["unclassified"])

#     scored = []
#     for c in candidates:
#         expected_benefit = round(
#             min(100.0, severity_score * c["benefit_weight"]), 1
#         )
#         scored.append(
#             {
#                 "road_id": road_id,
#                 "cause": dominant_cause,
#                 "intervention": c["intervention"],
#                 "expected_benefit_score": expected_benefit,
#                 "implementation_difficulty_score": float(c["difficulty"]),
#                 "rationale": (
#                     f"Cause '{dominant_cause}' observed as blocking in "
#                     f"{occurrence_count} historical window(s) with a severity "
#                     f"score of {severity_score}/100. Recommendation is a "
#                     f"rule-based suggestion, not a guaranteed outcome."
#                 ),
#             }
#         )

#     # Rank by benefit-to-difficulty ratio, descending. Highest-value,
#     # lowest-effort interventions get priority_rank = 1.
#     scored.sort(key=lambda r: r["expected_benefit_score"] / max(1.0, r["implementation_difficulty_score"]),
#                 reverse=True)
#     for i, r in enumerate(scored, start=1):
#         r["priority_rank"] = i

#     return scored


# def main():
#     parser = argparse.ArgumentParser(description="LaneLogic Person 4: Recurrence & Recommendation")
#     parser.add_argument("--api", default="http://localhost:8000",
#                          help="Base URL of Person 3's FastAPI backend")
#     args = parser.parse_args()

#     roads = fetch_json(args.api, "/roads")
#     print(f"[Person4] Evaluating {len(roads)} road(s) for chronic status...")

#     chronic_zones_payload = []
#     all_recommendations = []

#     for road in roads:
#         road_id = road["id"]
#         history = fetch_json(args.api, f"/roads/{road_id}/history")

#         is_chronic, dominant_cause, occurrence_count, severity_score = evaluate_road(history)
#         if not is_chronic:
#             print(f"  {road_id}: not chronic (insufficient/low blockage evidence)")
#             continue

#         print(f"  {road_id}: CHRONIC -> cause={dominant_cause} "
#               f"occurrences={occurrence_count} severity={severity_score}")

#         chronic_zones_payload.append(
#             {
#                 "road_id": road_id,
#                 "dominant_cause": dominant_cause,
#                 "occurrence_count": occurrence_count,
#                 "severity_score": severity_score,
#                 "notes": "Auto-flagged by Person 4 rule-based recurrence check.",
#             }
#         )

#         recs = build_recommendations(road_id, dominant_cause, occurrence_count, severity_score)
#         all_recommendations.extend(recs)

#     if chronic_zones_payload:
#         post_json(args.api, "/chronic-zones/bulk", chronic_zones_payload)
#         print(f"[Person4] Pushed {len(chronic_zones_payload)} chronic zone(s) to backend.")

#     if all_recommendations:
#         post_json(args.api, "/recommendations/bulk", all_recommendations)
#         print(f"[Person4] Pushed {len(all_recommendations)} recommendation(s) to backend.")

#     if not chronic_zones_payload:
#         print("[Person4] No chronic zones detected yet — need more historical windows per road.")


# if __name__ == "__main__":
#     main()














# """
# LaneLogic - PERSON 4: Recurrence & Recommendation
# ==================================================

# Role:
#     Historical recurrence + recommendation engine.

# Pipeline:
#     Person 3 Backend
#           ↓
#     Person 4
#           ↓
#     Chronic Zone Detection
#           ↓
#     Cause-based Recommendations
#           ↓
#     Person 3 Backend
#           ↓
#     Frontend Dashboard

# What this module does:
#     1. Gets all roads from Person 3.
#     2. Gets historical analysis windows for every road.
#     3. Uses PARKED SPACE as the main blockage signal.
#     4. Detects chronic/repeated problem roads.
#     5. Generates recommendations for roads that currently have
#        a meaningful problem, even if there is not enough history
#        to call them chronic.
#     6. Sends chronic zones and recommendations back to Person 3.

# Important:
#     Person 1's parked threshold remains 5 seconds.
#     Person 4 does NOT change vehicle detection or parked detection.

# Run:
#     python main.py

# Or:
#     python main.py --api http://localhost:8000
# """

# import argparse
# from collections import defaultdict

# import requests


# # ============================================================
# # CONFIGURATION
# # ============================================================

# # Minimum number of observations needed before calling
# # something a "chronic" problem.
# #
# # We use 3 instead of 6 because your current prerecorded
# # videos may not generate many analysis windows.
# MIN_WINDOWS_REQUIRED = 3

# # A road is considered chronic when at least this fraction
# # of its historical windows show meaningful parked blockage.
# CHRONIC_WINDOW_FRACTION = 0.40

# # Minimum parked-space percentage considered meaningful.
# #
# # Example:
# # 5% parked space = some blockage
# # 10%+ = meaningful recurring blockage
# CHRONIC_MIN_PARKED_SPACE_PCT = 5.0

# # If there is only one observation, we can still create a
# # recommendation when the current problem is meaningful.
# CURRENT_PROBLEM_THRESHOLD_PCT = 5.0


# # ============================================================
# # CAUSE -> INTERVENTION MAP
# # ============================================================

# CAUSE_INTERVENTION_MAP = {

#     "illegal_parking": [
#         {
#             "intervention": "No-parking enforcement + signage",
#             "difficulty": 20,
#             "benefit_weight": 1.0,
#         },
#         {
#             "intervention": "Designated parking bay relocation",
#             "difficulty": 55,
#             "benefit_weight": 1.1,
#         },
#     ],

#     "loading_unloading": [
#         {
#             "intervention": "Designated loading bay with time restriction",
#             "difficulty": 45,
#             "benefit_weight": 1.0,
#         },
#         {
#             "intervention": "Restrict loading to off-peak hours only",
#             "difficulty": 25,
#             "benefit_weight": 0.8,
#         },
#     ],

#     "traffic_signal_queue": [
#         {
#             "intervention": "Signal timing / green-phase review",
#             "difficulty": 60,
#             "benefit_weight": 0.9,
#         },
#         {
#             "intervention": "Additional turning lane at junction",
#             "difficulty": 80,
#             "benefit_weight": 1.2,
#         },
#     ],

#     "school_drop_off": [
#         {
#             "intervention": "Dedicated pickup/drop-off zone",
#             "difficulty": 50,
#             "benefit_weight": 1.0,
#         },
#         {
#             "intervention": "Staggered school timing coordination",
#             "difficulty": 35,
#             "benefit_weight": 0.7,
#         },
#     ],

#     "general_congestion": [
#         {
#             "intervention": "Lane-usage review / informal auto-stand relocation",
#             "difficulty": 50,
#             "benefit_weight": 0.9,
#         },
#     ],

#     "unclassified": [
#         {
#             "intervention": "Manual site survey recommended before intervention",
#             "difficulty": 10,
#             "benefit_weight": 0.4,
#         },
#     ],
# }


# # ============================================================
# # HTTP HELPERS
# # ============================================================

# def fetch_json(api_base, path):
#     """
#     GET JSON from Person 3 backend.
#     """

#     response = requests.get(
#         f"{api_base}{path}",
#         timeout=10
#     )

#     response.raise_for_status()

#     return response.json()


# def post_json(api_base, path, payload):
#     """
#     POST JSON to Person 3 backend.
#     """

#     response = requests.post(
#         f"{api_base}{path}",
#         json=payload,
#         timeout=10
#     )

#     response.raise_for_status()

#     return response.json()


# # ============================================================
# # PARKED SPACE HELPERS
# # ============================================================

# def get_parked_space_pct(observation):
#     """
#     Get parked-space percentage.

#     New Person 2:
#         parked_space_pct

#     Older compatibility:
#         blocked_pct

#     Parked-space percentage is preferred because the new
#     system specifically measures PARKED vehicles as the
#     parking blockage.
#     """

#     parked_pct = observation.get("parked_space_pct")

#     if parked_pct is not None:
#         try:
#             return float(parked_pct)
#         except (TypeError, ValueError):
#             pass

#     # Compatibility with older analysis data.
#     blocked_pct = observation.get("blocked_pct")

#     if blocked_pct is not None:
#         try:
#             return float(blocked_pct)
#         except (TypeError, ValueError):
#             pass

#     return 0.0


# def get_parked_vehicle_count(observation):
#     """
#     Extract parked vehicle count from movement_state_breakdown.
#     """

#     movement_breakdown = observation.get(
#         "movement_state_breakdown",
#         {}
#     )

#     if not isinstance(movement_breakdown, dict):
#         return 0

#     try:
#         return int(
#             movement_breakdown.get("parked", 0)
#         )
#     except (TypeError, ValueError):
#         return 0


# def get_cause(observation):
#     """
#     Safely get cause from an observation.
#     """

#     cause = observation.get("cause")

#     if cause:
#         return str(cause)

#     return "unclassified"


# # ============================================================
# # CHRONIC ROAD EVALUATION
# # ============================================================

# def evaluate_chronic_road(history):
#     """
#     Decide whether a road is a chronic problem.

#     Chronic condition:

#         1. At least MIN_WINDOWS_REQUIRED observations.
#         2. At least CHRONIC_WINDOW_FRACTION of those
#            observations show meaningful parked blockage.

#     Returns:

#         is_chronic
#         dominant_cause
#         occurrence_count
#         severity_score
#         average_parked_space_pct
#     """

#     if not history:
#         return (
#             False,
#             None,
#             0,
#             0.0,
#             0.0,
#         )

#     # --------------------------------------------------------
#     # Calculate parked-space values
#     # --------------------------------------------------------

#     parked_values = []

#     for observation in history:
#         parked_pct = get_parked_space_pct(observation)

#         parked_values.append(
#             max(0.0, parked_pct)
#         )

#     average_parked_space_pct = (
#         sum(parked_values) / len(parked_values)
#         if parked_values
#         else 0.0
#     )

#     # --------------------------------------------------------
#     # Need enough historical windows for chronic status
#     # --------------------------------------------------------

#     if len(history) < MIN_WINDOWS_REQUIRED:
#         return (
#             False,
#             None,
#             0,
#             0.0,
#             average_parked_space_pct,
#         )

#     # --------------------------------------------------------
#     # Find windows with meaningful parked blockage
#     # --------------------------------------------------------

#     blocked_windows = [
#         observation
#         for observation in history
#         if get_parked_space_pct(observation)
#         >= CHRONIC_MIN_PARKED_SPACE_PCT
#     ]

#     blocked_window_count = len(blocked_windows)

#     blocked_fraction = (
#         blocked_window_count / len(history)
#     )

#     # --------------------------------------------------------
#     # Check chronic threshold
#     # --------------------------------------------------------

#     if blocked_fraction < CHRONIC_WINDOW_FRACTION:
#         return (
#             False,
#             None,
#             blocked_window_count,
#             0.0,
#             average_parked_space_pct,
#         )

#     # --------------------------------------------------------
#     # Find dominant cause
#     # --------------------------------------------------------

#     cause_counts = defaultdict(int)

#     for observation in blocked_windows:
#         cause = get_cause(observation)

#         # Normal should not become a recommendation cause.
#         if cause == "normal":
#             cause = "unclassified"

#         cause_counts[cause] += 1

#     if cause_counts:
#         dominant_cause = max(
#             cause_counts,
#             key=cause_counts.get
#         )
#     else:
#         dominant_cause = "unclassified"

#     # --------------------------------------------------------
#     # Severity score
#     #
#     # Recurrence contributes 60 points.
#     # Average parked space contributes 40 points.
#     # --------------------------------------------------------

#     recurrence_score = blocked_fraction * 60.0

#     parked_space_score = min(
#         40.0,
#         (average_parked_space_pct / 100.0) * 40.0
#     )

#     severity_score = round(
#         min(
#             100.0,
#             recurrence_score + parked_space_score
#         ),
#         1
#     )

#     return (
#         True,
#         dominant_cause,
#         blocked_window_count,
#         severity_score,
#         average_parked_space_pct,
#     )


# # ============================================================
# # CURRENT PROBLEM DETECTION
# # ============================================================

# def get_current_problem(history):
#     """
#     Determine whether the road currently has a meaningful
#     parked-space problem.

#     We use the latest observation.

#     This allows recommendations to appear even when there
#     is not enough history to classify the road as chronic.
#     """

#     if not history:
#         return None

#     latest = history[-1]

#     parked_pct = get_parked_space_pct(latest)
#     parked_count = get_parked_vehicle_count(latest)
#     cause = get_cause(latest)

#     # No meaningful parked blockage.
#     if parked_pct < CURRENT_PROBLEM_THRESHOLD_PCT:
#         return None

#     # A "normal" cause should not generate an intervention.
#     if cause == "normal":
#         cause = "unclassified"

#     return {
#         "parked_space_pct": parked_pct,
#         "parked_vehicle_count": parked_count,
#         "cause": cause,
#     }


# # ============================================================
# # RECOMMENDATION SCORING
# # ============================================================

# def build_recommendations(
#     road_id,
#     dominant_cause,
#     occurrence_count,
#     severity_score,
#     parked_space_pct,
#     is_chronic,
# ):
#     """
#     Build ranked recommendations for a road.

#     Scores are explainable heuristics.

#     expected_benefit_score:
#         Based on severity and intervention benefit weight.

#     implementation_difficulty_score:
#         Fixed heuristic representing relative complexity.

#     priority:
#         Higher benefit with lower difficulty ranks higher.
#     """

#     candidates = CAUSE_INTERVENTION_MAP.get(
#         dominant_cause,
#         CAUSE_INTERVENTION_MAP["unclassified"]
#     )

#     recommendations = []

#     # --------------------------------------------------------
#     # Base severity
#     # --------------------------------------------------------

#     base_severity = max(
#         severity_score,
#         min(
#             100.0,
#             parked_space_pct
#         )
#     )

#     for candidate in candidates:

#         expected_benefit = round(
#             min(
#                 100.0,
#                 base_severity
#                 * candidate["benefit_weight"]
#             ),
#             1
#         )

#         difficulty = float(
#             candidate["difficulty"]
#         )

#         # Benefit-to-difficulty ratio.
#         ranking_score = round(
#             expected_benefit
#             / max(1.0, difficulty),
#             4
#         )

#         if is_chronic:
#             status_text = (
#                 "This road shows a recurring parked-space "
#                 "problem across historical observations."
#             )
#         else:
#             status_text = (
#                 "This recommendation is based on the "
#                 "current observed parked-space problem; "
#                 "more history is needed before calling the "
#                 "road chronic."
#             )

#         recommendation = {
#             "road_id": road_id,
#             "cause": dominant_cause,
#             "intervention": candidate["intervention"],

#             "expected_benefit_score": expected_benefit,

#             "implementation_difficulty_score": difficulty,

#             "rationale": (
#                 f"Cause '{dominant_cause}' observed with "
#                 f"{parked_space_pct:.2f}% parked-space blockage. "
#                 f"{occurrence_count} historical window(s) "
#                 f"showed meaningful blockage. "
#                 f"{status_text} "
#                 f"Recommendation is a rule-based suggestion, "
#                 f"not a guaranteed real-world outcome."
#             ),

#             # Extra metadata is useful to the frontend and
#             # does not break the existing backend schema if
#             # the backend ignores unknown fields.
#             "parked_space_pct": round(
#                 parked_space_pct,
#                 2
#             ),

#             "is_chronic": bool(is_chronic),

#             "_ranking_score": ranking_score,
#         }

#         recommendations.append(
#             recommendation
#         )

#     # --------------------------------------------------------
#     # Rank recommendations
#     # --------------------------------------------------------

#     recommendations.sort(
#         key=lambda item: item["_ranking_score"],
#         reverse=True
#     )

#     # --------------------------------------------------------
#     # Assign priority rank
#     # --------------------------------------------------------

#     for index, recommendation in enumerate(
#         recommendations,
#         start=1
#     ):
#         recommendation["priority_rank"] = index

#         # Internal field should not be sent to backend.
#         recommendation.pop(
#             "_ranking_score",
#             None
#         )

#     return recommendations


# # ============================================================
# # MAIN
# # ============================================================

# def main():

#     parser = argparse.ArgumentParser(
#         description=(
#             "LaneLogic Person 4: "
#             "Recurrence & Recommendation"
#         )
#     )

#     parser.add_argument(
#         "--api",
#         default="http://localhost:8000",
#         help="Person 3 FastAPI base URL"
#     )

#     args = parser.parse_args()

#     api_base = args.api.rstrip("/")

#     print()
#     print("=" * 60)
#     print("LANELOGIC - PERSON 4")
#     print("RECURRENCE & RECOMMENDATION")
#     print("=" * 60)
#     print()

#     # ========================================================
#     # GET ROADS
#     # ========================================================

#     try:
#         roads = fetch_json(
#             api_base,
#             "/roads"
#         )

#     except requests.RequestException as e:

#         print(
#             f"[ERROR] Could not connect to backend: {e}"
#         )

#         print()
#         print(
#             "Make sure Person 3 is running:"
#         )

#         print(
#             "uvicorn main:app --reload --port 8000"
#         )

#         return

#     print(
#         f"[Person4] Evaluating {len(roads)} road(s)..."
#     )

#     print()

#     chronic_zones_payload = []
#     all_recommendations = []

#     # ========================================================
#     # PROCESS EACH ROAD
#     # ========================================================

#     for road in roads:

#         road_id = road["id"]

#         road_name = road.get(
#             "name",
#             road_id
#         )

#         print(
#             f"--- {road_id} | {road_name} ---"
#         )

#         # ----------------------------------------------------
#         # Get history
#         # ----------------------------------------------------

#         try:
#             history = fetch_json(
#                 api_base,
#                 f"/roads/{road_id}/history"
#             )

#         except requests.RequestException as e:

#             print(
#                 f"  [ERROR] Could not get history: {e}"
#             )

#             print()

#             continue

#         if not history:

#             print(
#                 "  No historical observations."
#             )

#             print()

#             continue

#         print(
#             f"  Historical windows: {len(history)}"
#         )

#         # ----------------------------------------------------
#         # Calculate current problem
#         # ----------------------------------------------------

#         current_problem = get_current_problem(
#             history
#         )

#         # ----------------------------------------------------
#         # Evaluate chronic status
#         # ----------------------------------------------------

#         (
#             is_chronic,
#             chronic_cause,
#             occurrence_count,
#             severity_score,
#             average_parked_space_pct,
#         ) = evaluate_chronic_road(
#             history
#         )

#         # ----------------------------------------------------
#         # CHRONIC ROAD
#         # ----------------------------------------------------

#         if is_chronic:

#             print(
#                 f"  STATUS      : CHRONIC"
#             )

#             print(
#                 f"  Cause       : {chronic_cause}"
#             )

#             print(
#                 f"  Occurrences : {occurrence_count}"
#             )

#             print(
#                 f"  Avg parked  : "
#                 f"{average_parked_space_pct:.2f}%"
#             )

#             print(
#                 f"  Severity    : "
#                 f"{severity_score}/100"
#             )

#             chronic_zones_payload.append(
#                 {
#                     "road_id": road_id,
#                     "dominant_cause": chronic_cause,
#                     "occurrence_count": occurrence_count,
#                     "severity_score": severity_score,
#                     "notes": (
#                         "Auto-flagged by Person 4 "
#                         "rule-based recurrence analysis "
#                         "using parked-space blockage."
#                     ),
#                 }
#             )

#             # ------------------------------------------------
#             # Generate recommendations
#             # ------------------------------------------------

#             recommendations = build_recommendations(
#                 road_id=road_id,
#                 dominant_cause=chronic_cause,
#                 occurrence_count=occurrence_count,
#                 severity_score=severity_score,
#                 parked_space_pct=average_parked_space_pct,
#                 is_chronic=True,
#             )

#             all_recommendations.extend(
#                 recommendations
#             )

#             for recommendation in recommendations:

#                 print(
#                     "  Recommendation:"
#                 )

#                 print(
#                     f"    → "
#                     f"{recommendation['intervention']}"
#                 )

#                 print(
#                     f"      Benefit: "
#                     f"{recommendation['expected_benefit_score']}"
#                 )

#                 print(
#                     f"      Difficulty: "
#                     f"{recommendation['implementation_difficulty_score']}"
#                 )

#         # ----------------------------------------------------
#         # NOT CHRONIC BUT CURRENT PROBLEM EXISTS
#         # ----------------------------------------------------

#         elif current_problem is not None:

#             cause = current_problem["cause"]

#             parked_pct = current_problem[
#                 "parked_space_pct"
#             ]

#             parked_count = current_problem[
#                 "parked_vehicle_count"
#             ]

#             print(
#                 "  STATUS      : CURRENT PROBLEM"
#             )

#             print(
#                 f"  Cause       : {cause}"
#             )

#             print(
#                 f"  Parked      : "
#                 f"{parked_count} vehicle(s)"
#             )

#             print(
#                 f"  Parked space: "
#                 f"{parked_pct:.2f}%"
#             )

#             print(
#                 "  Chronic     : NO "
#                 "(more history required)"
#             )

#             # ------------------------------------------------
#             # Generate useful recommendation anyway.
#             # ------------------------------------------------

#             recommendations = build_recommendations(
#                 road_id=road_id,
#                 dominant_cause=cause,
#                 occurrence_count=1,
#                 severity_score=parked_pct,
#                 parked_space_pct=parked_pct,
#                 is_chronic=False,
#             )

#             all_recommendations.extend(
#                 recommendations
#             )

#             for recommendation in recommendations:

#                 print(
#                     "  Recommendation:"
#                 )

#                 print(
#                     f"    → "
#                     f"{recommendation['intervention']}"
#                 )

#                 print(
#                     f"      Benefit: "
#                     f"{recommendation['expected_benefit_score']}"
#                 )

#                 print(
#                     f"      Difficulty: "
#                     f"{recommendation['implementation_difficulty_score']}"
#                 )

#         # ----------------------------------------------------
#         # NORMAL ROAD
#         # ----------------------------------------------------

#         else:

#             print(
#                 "  STATUS      : NORMAL"
#             )

#             print(
#                 f"  Avg parked  : "
#                 f"{average_parked_space_pct:.2f}%"
#             )

#             print(
#                 "  No recommendation required."
#             )

#         print()

#     # ========================================================
#     # PUSH CHRONIC ZONES
#     # ========================================================

#     if chronic_zones_payload:

#         try:

#             post_json(
#                 api_base,
#                 "/chronic-zones/bulk",
#                 chronic_zones_payload
#             )

#             print(
#                 f"[Person4] ✓ Pushed "
#                 f"{len(chronic_zones_payload)} "
#                 f"chronic zone(s) to backend."
#             )

#         except requests.RequestException as e:

#             print(
#                 f"[Person4] ✗ Failed to push "
#                 f"chronic zones: {e}"
#             )

#     else:

#         print(
#             "[Person4] No chronic zones detected yet."
#         )

#     # ========================================================
#     # PUSH RECOMMENDATIONS
#     # ========================================================

#     if all_recommendations:

#         # ----------------------------------------------------
#         # Keep only fields expected by Person 3.
#         #
#         # This prevents extra Person4-only metadata from
#         # causing validation problems if the backend schema
#         # is strict.
#         # ----------------------------------------------------

#         backend_recommendations = []

#         for recommendation in all_recommendations:

#             backend_recommendations.append(
#                 {
#                     "road_id": recommendation["road_id"],
#                     "cause": recommendation["cause"],
#                     "intervention": recommendation[
#                         "intervention"
#                     ],
#                     "expected_benefit_score": recommendation[
#                         "expected_benefit_score"
#                     ],
#                     "implementation_difficulty_score":
#                         recommendation[
#                             "implementation_difficulty_score"
#                         ],
#                     "priority_rank": recommendation[
#                         "priority_rank"
#                     ],
#                     "rationale": recommendation[
#                         "rationale"
#                     ],
#                 }
#             )

#         try:

#             post_json(
#                 api_base,
#                 "/recommendations/bulk",
#                 backend_recommendations
#             )

#             print(
#                 f"[Person4] ✓ Pushed "
#                 f"{len(backend_recommendations)} "
#                 f"recommendation(s) to backend."
#             )

#         except requests.RequestException as e:

#             print(
#                 f"[Person4] ✗ Failed to push "
#                 f"recommendations: {e}"
#             )

#     else:

#         print(
#             "[Person4] No recommendations generated."
#         )

#     # ========================================================
#     # FINAL SUMMARY
#     # ========================================================

#     print()
#     print("=" * 60)
#     print("PERSON 4 COMPLETE")
#     print("=" * 60)

#     print(
#         f"Roads evaluated       : {len(roads)}"
#     )

#     print(
#         f"Chronic zones         : "
#         f"{len(chronic_zones_payload)}"
#     )

#     print(
#         f"Recommendations       : "
#         f"{len(all_recommendations)}"
#     )

#     print("=" * 60)
#     print()


# # ============================================================
# # ENTRY POINT
# # ============================================================

# if __name__ == "__main__":
#     main()













import requests
from collections import Counter

BACKEND_URL = "http://localhost:8000"

# ============================================================
# PERSON 4 - RECURRENCE + RECOMMENDATION
# ============================================================

# For short prerecorded videos:
# multiple analysis windows with parked vehicles = recurring evidence
MIN_WINDOWS_REQUIRED = 3

# A road becomes chronic when parked evidence appears
# in at least this fraction of its historical windows.
CHRONIC_WINDOW_FRACTION = 0.40

# IMPORTANT:
# Do NOT require a large parked-space percentage.
# Even a small parked vehicle can represent a recurring
# parking problem when it repeatedly appears.
MIN_PARKED_VEHICLES_FOR_RECURRENCE = 1

# Current problem threshold
CURRENT_PROBLEM_PARKED_VEHICLES = 1


CAUSE_RECOMMENDATIONS = {
    "illegal_parking": (
        "Install no-parking signage and increase parking enforcement "
        "during peak hours."
    ),

    "loading_unloading": (
        "Create a designated loading/unloading zone away from the "
        "main traffic lane."
    ),

    "signal_waiting": (
        "Review traffic-signal timing and provide a clearly defined "
        "waiting lane near the junction."
    ),

    "traffic_congestion": (
        "Review lane capacity and signal timing; consider traffic "
        "management during peak hours."
    ),

    "mixed_traffic": (
        "Improve lane discipline and provide clearer lane markings "
        "and vehicle guidance."
    ),

    "unclassified": (
        "Inspect the location for recurring roadside obstruction "
        "and consider appropriate parking or enforcement measures."
    ),

    "normal": (
        "No immediate intervention required."
    ),
}


def get_parked_vehicle_count(observation):
    """
    Get the number of parked vehicles from a Person 2 observation.

    Primary source:
        movement_state_breakdown["parked"]

    Fallback:
        parked_vehicle_count
    """

    breakdown = observation.get("movement_state_breakdown", {})

    if isinstance(breakdown, dict):
        try:
            return int(breakdown.get("parked", 0))
        except (TypeError, ValueError):
            pass

    try:
        return int(observation.get("parked_vehicle_count", 0))
    except (TypeError, ValueError):
        return 0


def get_parked_space_pct(observation):
    """
    Parked-space percentage from Person 2.
    """

    try:
        return float(observation.get("parked_space_pct", 0.0))
    except (TypeError, ValueError):
        return 0.0


def get_cause(observation):
    cause = observation.get("cause", "unclassified")

    if not cause:
        cause = "unclassified"

    return cause


def get_latest_observation(observations):
    if not observations:
        return None

    return max(
        observations,
        key=lambda x: (
            x.get("timestamp", 0),
            x.get("window_index", x.get("window", 0))
        )
    )


def analyse_road(road_id, observations):
    """
    Analyse one road's historical observations.
    """

    if not observations:
        return {
            "road_id": road_id,
            "chronic": False,
            "reason": "no historical observations",
            "parked_windows": 0,
            "total_windows": 0,
            "recurrence_fraction": 0.0,
        }

    total_windows = len(observations)

    parked_windows = 0
    total_parked_vehicle_observations = 0
    parked_space_values = []

    causes = []

    for observation in observations:

        parked_count = get_parked_vehicle_count(observation)
        parked_space = get_parked_space_pct(observation)

        total_parked_vehicle_observations += parked_count
        parked_space_values.append(parked_space)

        if parked_count >= MIN_PARKED_VEHICLES_FOR_RECURRENCE:
            parked_windows += 1

        cause = get_cause(observation)

        if cause != "normal":
            causes.append(cause)

    recurrence_fraction = parked_windows / total_windows

    chronic = (
        total_windows >= MIN_WINDOWS_REQUIRED
        and recurrence_fraction >= CHRONIC_WINDOW_FRACTION
    )

    # Most common non-normal cause
    if causes:
        dominant_cause = Counter(causes).most_common(1)[0][0]
    else:
        dominant_cause = "normal"

    average_parked_space = (
        sum(parked_space_values) / len(parked_space_values)
        if parked_space_values
        else 0.0
    )

    return {
        "road_id": road_id,
        "chronic": chronic,
        "total_windows": total_windows,
        "parked_windows": parked_windows,
        "recurrence_fraction": round(recurrence_fraction, 3),
        "total_parked_vehicle_observations": total_parked_vehicle_observations,
        "average_parked_space_pct": round(average_parked_space, 3),
        "dominant_cause": dominant_cause,
    }


def make_recommendation(road_id, analysis, latest_observation):
    """
    Generate recommendation for current/recurrent problem.
    """

    if latest_observation is None:
        return None

    parked_count = get_parked_vehicle_count(latest_observation)
    parked_space = get_parked_space_pct(latest_observation)

    cause = get_cause(latest_observation)

    # --------------------------------------------------------
    # Current problem
    # --------------------------------------------------------

    current_problem = parked_count >= CURRENT_PROBLEM_PARKED_VEHICLES

    # --------------------------------------------------------
    # Chronic problem
    # --------------------------------------------------------

    chronic = analysis["chronic"]

    if not current_problem and not chronic:
        return None

    # Prefer latest cause
    if cause == "normal":
        cause = analysis.get("dominant_cause", "unclassified")

    recommendation_text = CAUSE_RECOMMENDATIONS.get(
        cause,
        CAUSE_RECOMMENDATIONS["unclassified"]
    )

    if chronic:
        problem_type = "chronic"
        explanation = (
            f"Parked vehicles were observed in "
            f"{analysis['parked_windows']} of "
            f"{analysis['total_windows']} historical windows "
            f"({analysis['recurrence_fraction'] * 100:.1f}% recurrence)."
        )
    else:
        problem_type = "current"
        explanation = (
            f"{parked_count} parked vehicle(s) currently detected "
            f"with {parked_space:.2f}% parked-space occupancy."
        )

    return {
        "road_id": road_id,
        "problem_type": problem_type,
        "cause": cause,
        "recommendation": recommendation_text,
        "explanation": explanation,
        "parked_vehicle_count": parked_count,
        "parked_space_pct": round(parked_space, 3),
        "recurrence_fraction": analysis["recurrence_fraction"],
    }


def fetch_roads():
    try:
        response = requests.get(
            f"{BACKEND_URL}/roads",
            timeout=10
        )

        response.raise_for_status()

        return response.json()

    except Exception as e:
        print(f"[Person4] Could not fetch roads: {e}")
        return []


def fetch_history(road_id):
    try:
        response = requests.get(
            f"{BACKEND_URL}/roads/{road_id}/history",
            timeout=10
        )

        response.raise_for_status()

        return response.json()

    except Exception as e:
        print(
            f"[Person4] Could not fetch history for "
            f"{road_id}: {e}"
        )
        return []


def send_recommendation(recommendation):
    if not recommendation:
        return

    try:
        response = requests.post(
            f"{BACKEND_URL}/recommendations/bulk",
            json={
                "recommendations": [recommendation]
            },
            timeout=10
        )

        if response.ok:
            print(
                f"      ✓ Recommendation sent to backend"
            )
        else:
            print(
                f"      ⚠ Recommendation backend returned "
                f"{response.status_code}"
            )

    except Exception as e:
        print(
            f"      ⚠ Could not send recommendation: {e}"
        )


def send_chronic_zone(analysis):
    if not analysis.get("chronic"):
        return

    payload = {
        "road_id": analysis["road_id"],
        "recurrence_fraction": analysis["recurrence_fraction"],
        "parked_windows": analysis["parked_windows"],
        "total_windows": analysis["total_windows"],
        "average_parked_space_pct": analysis[
            "average_parked_space_pct"
        ],
        "dominant_cause": analysis["dominant_cause"],
    }

    try:
        response = requests.post(
            f"{BACKEND_URL}/chronic-zones/bulk",
            json={
                "zones": [payload]
            },
            timeout=10
        )

        if response.ok:
            print(
                f"      ✓ Chronic zone sent to backend"
            )
        else:
            print(
                f"      ⚠ Chronic-zone backend returned "
                f"{response.status_code}"
            )

    except Exception as e:
        print(
            f"      ⚠ Could not send chronic zone: {e}"
        )


def main():

    print()
    print("=" * 70)
    print("LANELOGIC - PERSON 4")
    print("RECURRENCE + RECOMMENDATION ANALYSIS")
    print("=" * 70)

    roads = fetch_roads()

    if not roads:
        print()
        print("No roads found in backend.")
        print("Make sure Person 3 backend is running.")
        return

    print(
        f"[Person4] Evaluating {len(roads)} road(s)..."
    )
    print()

    chronic_count = 0

    for road in roads:

        road_id = road.get("road_id")

        if not road_id:
            continue

        history = fetch_history(road_id)

        analysis = analyse_road(
            road_id,
            history
        )

        print(
            f"ROAD: {road_id}"
        )

        print(
            f"  Historical windows : "
            f"{analysis['total_windows']}"
        )

        print(
            f"  Parked windows     : "
            f"{analysis['parked_windows']}"
        )

        print(
            f"  Recurrence         : "
            f"{analysis['recurrence_fraction'] * 100:.1f}%"
        )

        print(
            f"  Avg parked space   : "
            f"{analysis['average_parked_space_pct']:.3f}%"
        )

        print(
            f"  Dominant cause     : "
            f"{analysis['dominant_cause']}"
        )

        if analysis["chronic"]:

            chronic_count += 1

            print(
                "  STATUS             : 🔴 CHRONIC ZONE"
            )

            print(
                "  Reason             : "
                "Recurring parked-vehicle problem"
            )

        else:

            print(
                "  STATUS             : Normal / not chronic"
            )

            if analysis["total_windows"] < MIN_WINDOWS_REQUIRED:
                print(
                    f"  Reason             : Need at least "
                    f"{MIN_WINDOWS_REQUIRED} historical windows"
                )
            else:
                print(
                    "  Reason             : Parked problem "
                    "not recurring enough"
                )

        latest = get_latest_observation(history)

        recommendation = make_recommendation(
            road_id,
            analysis,
            latest
        )

        if recommendation:

            print(
                f"  Recommendation     : "
                f"{recommendation['recommendation']}"
            )

            send_recommendation(
                recommendation
            )

        send_chronic_zone(
            analysis
        )

        print("-" * 70)

    print()
    print("=" * 70)
    print(
        f"CHRONIC ZONES DETECTED: {chronic_count}"
    )
    print("=" * 70)
    print()


if __name__ == "__main__":
    main()