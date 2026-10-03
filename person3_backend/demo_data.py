"""
LaneLogic — Demo Data Seeder (person3_backend/demo_data.py)
============================================================

Populates the SQLite database with synthetic demo data on startup IF AND
ONLY IF the database is currently empty (no Road rows).

Usage (called automatically from main.py):
    from demo_data import run_demo_seed_if_empty
    run_demo_seed_if_empty()

Design decisions:
  • Uses SQLAlchemy Session / ORM models directly — NO HTTP requests,
    NO subprocess calls to demo_seed.py.
  • Idempotent: the emptiness check uses Road table count; if rows already
    exist the function exits immediately and logs a skip message.
  • Data values are copied verbatim from person6_frontend/demo_seed.py so
    the dashboard looks identical whether seeded manually or automatically.
  • Recommendations are generated through the existing
    RecommendationDecisionEngine (same path as /recommendations/generate)
    so they appear with the same fields and logic.
"""

import logging
from typing import Optional

from sqlalchemy.orm import Session

import models
from database import SessionLocal

logger = logging.getLogger("lanelogic.demo_seed")

# ---------------------------------------------------------------------------
# DEMO DATA — copied verbatim from person6_frontend/demo_seed.py
# ---------------------------------------------------------------------------

#: One profile per road, worst-first: critical, high, moderate, clear.
_PROFILES = [
    dict(pct=41.0, level="critical", score=4, cause="loading_unloading",
         occ=82.0, types={"truck": 5, "van": 3, "car": 6},
         dwell=2820, vt="truck", zone=(9, 92.0)),
    dict(pct=24.0, level="high",     score=3, cause="illegal_parking",
         occ=64.0, types={"car": 9, "auto": 3},
         dwell=1500, vt="car",   zone=(6, 74.0)),
    dict(pct=12.0, level="moderate", score=2, cause="school_dropoff",
         occ=48.0, types={"car": 7, "bus": 1},
         dwell=420,  vt="car",   zone=None),
    dict(pct=2.0,  level="normal",   score=0, cause="general_congestion",
         occ=25.0, types={"car": 5},
         dwell=60,   vt="car",   zone=None),
]

#: Fallback road definitions (id, name, lat, lon).
_FALLBACK_ROADS = [
    ("ROAD_001", "Noida",      28.5355, 77.3910),
    ("ROAD_002", "Delhi",      28.6139, 77.2090),
    ("ROAD_003", "Ghaziabad",  28.6692, 77.4538),
    ("ROAD_004", "Faridabad",  28.4089, 77.3178),
]

#: Shape multipliers for the 10 analysis windows (last value == profile value).
_SHAPE = [0.35, 0.55, 0.8, 1.0, 0.9, 0.7, 0.85, 0.95, 0.75, 1.0]

_WIDTH_M = 7.0   # road width used in demo calculations


# ---------------------------------------------------------------------------
# INTERNAL HELPERS
# ---------------------------------------------------------------------------

def _build_observations(road_id: str, p: dict) -> list[dict]:
    """Return 10 RoadWindowObservation dicts for one road/profile pair."""
    obs = []
    for i, k in enumerate(_SHAPE):
        pct = round(p["pct"] * k, 1)
        obs.append({
            "road_id":                 road_id,
            "window_index":            i,
            "window_start_seconds":    float(i * 60),
            "window_end_seconds":      float((i + 1) * 60),
            "vehicle_count":           sum(p["types"].values()),
            "vehicle_type_breakdown":  p["types"],
            "movement_state_breakdown": {
                "moving": 6,
                "parked": max(1, round(pct / 8)),
            },
            "road_length_meters":      60.0,
            "road_width_meters":       _WIDTH_M,
            "road_area_m2":            60.0 * _WIDTH_M,
            "occupancy_pct":           round(p["occ"] * (0.7 + 0.3 * k), 1),
            "parked_space_pct":        pct,
            "parked_width_meters":     round(pct / 100 * _WIDTH_M, 2),
            "parked_area_m2":          round(pct / 100 * 60.0 * _WIDTH_M, 2),
            "blocked_pct":             pct,
            "blocked_area_m2":         round(pct / 100 * 60.0 * _WIDTH_M, 2),
            "severity":                p["level"],
            "priority_score":          p["score"],
            "cause":                   p["cause"],
            "cause_explanation": (
                f"DEMO DATA: pattern consistent with "
                f"{p['cause'].replace('_', ' ')}."
            ),
        })
    return obs


def _build_events(road_id: str, p: dict) -> list[dict]:
    """Return obstruction event dicts for one road/profile pair."""
    n = 4 if p["score"] >= 3 else 2 if p["score"] == 2 else 1
    events = []
    for i in range(n):
        loss = round(p["pct"] * (1.0 - 0.18 * i), 1)
        dur  = max(30, int(p["dwell"] * (1.0 - 0.25 * i)))
        events.append({
            "event_id":             f"DEMO-{road_id}-{i + 1}",
            "road_id":              road_id,
            "camera_id":            "CAM_01",
            "vehicle_id":           100 + i,
            "vehicle_type":         p["vt"] if i % 2 == 0 else "car",
            "start_time":           float(i * 90),
            "end_time":             float(i * 90 + dur),
            "duration_sec":         float(dur),
            "location":             [480.0 + 40 * i, 300.0],
            "bbox":                 [420.0 + 40 * i, 250.0,
                                     540.0 + 40 * i, 350.0],
            "road_width_m":         _WIDTH_M,
            "occupied_width_m":     round(loss / 100 * _WIDTH_M, 2),
            "road_space_loss_pct":  loss,
            "recurrence_score":     p["zone"][1] if p["zone"] else 20.0,
            "cause":                p["cause"],
            "cause_confidence":     round(0.92 - 0.06 * i, 2),
            "cause_explanation":    "DEMO DATA: long dwell with high share of road width lost.",
            "severity":             p["level"],
            "status":               "active" if i < 2 else "resolved",
            "event_metadata":       {"demo": True},
        })
    return events


def _priority_from_parked_space(parked_space_pct: float):
    """Mirror the priority logic used in main.py."""
    if parked_space_pct >= 60:
        return "critical", 4
    if parked_space_pct >= 40:
        return "high", 3
    if parked_space_pct >= 20:
        return "moderate", 2
    if parked_space_pct >= 5:
        return "low", 1
    return "normal", 0


# ---------------------------------------------------------------------------
# PUBLIC ENTRY POINT
# ---------------------------------------------------------------------------

def run_demo_seed_if_empty() -> None:
    """
    Called once at backend startup (after create_all).

    • If the database already contains Road rows → logs a skip message and
      returns immediately.  No writes are performed.
    • If the database is empty → inserts all demo data and commits.

    Duplicate-seeding prevention:
      The function checks ``db.query(models.Road).count()`` before inserting
      anything.  Once the roads exist, the check will always find > 0 rows and
      skip.  Every subsequent restart is therefore a no-op.
    """
    db: Session = SessionLocal()
    try:
        road_count = db.query(models.Road).count()

        if road_count > 0:
            logger.info(
                "Demo database already populated (%d road(s)); skipping seed.",
                road_count,
            )
            return

        logger.info("Demo database empty; seeding demo data …")

        # ----------------------------------------------------------------
        # 1 / 6  Roads
        # ----------------------------------------------------------------
        roads_inserted = []
        for rid, name, lat, lon in _FALLBACK_ROADS:
            road = models.Road(
                id=rid,
                name=name,
                latitude=lat,
                longitude=lon,
            )
            db.add(road)
            roads_inserted.append(rid)

        db.flush()  # road PKs are needed by child inserts below
        logger.info("Seeded %d roads: %s", len(roads_inserted),
                    ", ".join(roads_inserted))

        # Pair each road with the matching profile (zip stops at shorter list).
        pairs = list(zip(roads_inserted, _PROFILES))

        # ----------------------------------------------------------------
        # 2 / 6  Analysis windows
        # ----------------------------------------------------------------
        obs_count = 0
        for rid, p in pairs:
            for obs_dict in _build_observations(rid, p):
                db.add(models.RoadWindowObservation(**obs_dict))
                obs_count += 1

            # Update road's denormalized current-status fields
            # (mirrors main.py's ingest_analysis logic).
            last_pct = p["pct"]  # _SHAPE[-1] == 1.0, so last window == pct
            priority_level, priority_score = _priority_from_parked_space(
                last_pct
            )
            road = db.get(models.Road, rid)
            if road:
                road.current_status            = priority_level
                road.current_occupancy_pct     = round(p["occ"], 1)
                road.current_parked_space_pct  = last_pct
                road.current_parked_width_meters = round(
                    last_pct / 100 * _WIDTH_M, 2
                )
                road.current_parked_area_m2    = round(
                    last_pct / 100 * 60.0 * _WIDTH_M, 2
                )
                road.current_dominant_cause    = p["cause"]
                road.current_priority_score    = priority_score
                road.current_priority_level    = priority_level

        logger.info("Seeded %d analysis windows.", obs_count)

        # ----------------------------------------------------------------
        # 3 / 6  Obstruction events
        # ----------------------------------------------------------------
        event_count = 0
        for rid, p in pairs:
            for ev in _build_events(rid, p):
                db.add(models.ObstructionEventModel(**ev))
                event_count += 1
        logger.info("Seeded %d obstruction events.", event_count)

        # ----------------------------------------------------------------
        # 4 / 6  Chronic zones
        # ----------------------------------------------------------------
        zone_count = 0
        for rid, p in pairs:
            if p["zone"] is None:
                continue
            occ_count, sev_score = p["zone"]
            db.add(models.ChronicZone(
                road_id=rid,
                dominant_cause=p["cause"],
                occurrence_count=occ_count,
                severity_score=sev_score,
                notes="DEMO DATA: same obstruction seen in many windows.",
            ))
            # Mark road as chronic.
            road = db.get(models.Road, rid)
            if road:
                road.is_chronic = 1
            zone_count += 1
        logger.info("Seeded %d chronic zone(s).", zone_count)

        # ----------------------------------------------------------------
        # 5 / 6  Recommendations (generated inline via RecommendationDecisionEngine)
        # ----------------------------------------------------------------
        try:
            from core.interventions import RecommendationDecisionEngine
            rec_engine = RecommendationDecisionEngine()
            rec_count = 0
            for rid, p in pairs:
                if p["score"] < 2:
                    continue  # same threshold as demo_seed.py
                road = db.get(models.Road, rid)
                recs = rec_engine.generate_recommendations(
                    road_id=rid,
                    cause=p["cause"],
                    cause_confidence=0.85,
                    road_space_loss_pct=p["pct"],
                    recurrence_score=0.6 if (road and road.is_chronic) else 0.3,
                    evidence_summary=(
                        f"Road {rid} observed with {p['pct']:.1f}% space loss."
                    ),
                )
                for r in recs:
                    db.add(models.Recommendation(
                        road_id=r.road_id,
                        cause=r.cause,
                        intervention=r.intervention,
                        expected_benefit_score=r.expected_benefit_score,
                        implementation_difficulty_score=r.implementation_difficulty_score,
                        priority_rank=r.priority_rank,
                        rationale=r.rationale,
                    ))
                    rec_count += 1
            logger.info("Seeded %d recommendation(s).", rec_count)
        except Exception as rec_err:
            logger.warning(
                "Could not generate recommendations during seed (continuing): %s",
                rec_err,
            )

        # ----------------------------------------------------------------
        # 6 / 6  One measured intervention outcome (closed-loop panel)
        # ----------------------------------------------------------------
        first_road_id = roads_inserted[0]
        baseline_loss   = 18.2
        post_loss       = 7.1
        loss_delta      = round(post_loss - baseline_loss, 2)
        loss_pct_delta  = round(loss_delta / baseline_loss * 100, 1) if baseline_loss else 0.0

        db.add(models.InterventionOutcomeModel(
            road_id=first_road_id,
            intervention_type="Designated loading zone with time-window restriction",
            implementation_date="2026-09-20",
            baseline_window_description="14 days before",
            post_window_description="14 days after",
            baseline_metrics={
                "road_space_loss_pct": baseline_loss,
                "avg_dwell_min": 49.0,
            },
            post_metrics={
                "road_space_loss_pct": post_loss,
                "avg_dwell_min": 12.0,
            },
            observed_change={
                "loss_pct_absolute_delta": loss_delta,
                "loss_pct_relative_delta": loss_pct_delta,
                "avg_dwell_min_delta": round(12.0 - 49.0, 1),
            },
            is_causal_claim=0,
            notes="DEMO DATA: illustrative figures, not a real measurement.",
        ))
        logger.info("Seeded intervention outcome for %s.", first_road_id)

        # ----------------------------------------------------------------
        # Commit all inserts atomically
        # ----------------------------------------------------------------
        db.commit()
        logger.info(
            "Demo data seeding complete: %d roads, %d windows, "
            "%d events, %d chronic zones seeded.",
            len(roads_inserted), obs_count, event_count, zone_count,
        )

    except Exception:
        db.rollback()
        logger.exception("Demo data seeding failed; rolled back.")
        raise
    finally:
        db.close()
