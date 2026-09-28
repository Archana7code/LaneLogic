"""
LaneLogic - Closed-Loop End-to-End Test Suite
=============================================
Comprehensive unit, API, integration, and regression tests.
Validates:
1. Unit Tests (Event Engine, Geometry, Recurrence, Cause, Recommendation, Feedback, Outcomes, Simulation, Alerts)
2. Edge Cases (Zero vehicles, Disappearance, Prolonged stops, Low confidence, Unknown roads)
3. API Tests (All new closed-loop endpoints + backward-compatible existing endpoints)
4. Integration Test (P1 Detection -> P2 Analysis -> P3 Backend -> P4 Recurrence & Recommendation)
"""

import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

BACKEND_DIR = ROOT_DIR / "person3_backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from core.contracts import ObstructionEvent, HistoricalPattern, InterventionOutcomeIn, SimulationRequest
from core.event_engine import ObstructionEventEngine
from core.geometry import calculate_road_space_metrics
from core.recurrence import HistoricalRecurrenceEngine
from core.cause_classifier import ExplainableCauseClassifier
from core.interventions import RecommendationDecisionEngine
from core.outcomes import InterventionOutcomeService
from core.simulation import InterventionSimulationEngine
from core.alerts import AlertEngine
from core.continuous_learning import ContinuousLearningRegistry

import main as backend_app
from database import Base, engine, get_db


@pytest.fixture(scope="module")
def client():
    """FastAPI TestClient fixture."""
    Base.metadata.create_all(bind=engine)
    with TestClient(backend_app.app) as c:
        yield c


# ============================================================
# 1. UNIT TESTS
# ============================================================

def test_event_creation_start_and_continuation():
    """Test that event engine starts, continues, and ends events properly."""
    engine = ObstructionEventEngine(
        stationary_threshold_sec=3.0,
        max_disappearance_gap_sec=2.0,
        road_width_m=10.0,
        road_length_m=100.0,
        road_polygon=[[0, 0], [100, 0], [100, 100], [0, 100]],
    )

    # Frame 1: vehicle moving (should not create event)
    events = engine.feed_observation({
        "vehicle_id": 99,
        "vehicle_type": "car",
        "timestamp": 1.0,
        "movement_state": "moving",
        "stationary_duration": 0.0,
        "bbox": [10, 10, 30, 30],
        "position": [20, 20],
    })
    assert len(events) == 0
    assert 99 not in engine.active_events

    # Frame 2: vehicle parked for 3.5s (should open event)
    events = engine.feed_observation({
        "vehicle_id": 99,
        "vehicle_type": "car",
        "timestamp": 4.5,
        "movement_state": "parked",
        "stationary_duration": 3.5,
        "bbox": [10, 10, 30, 30],
        "position": [20, 20],
    })
    assert len(events) == 0
    assert 99 in engine.active_events
    active_ev = engine.active_events[99]
    assert active_ev["vehicle_id"] == 99
    assert active_ev["duration_sec"] == 3.5

    # Frame 3: vehicle still parked at 6.0s (should update ongoing event)
    events = engine.feed_observation({
        "vehicle_id": 99,
        "vehicle_type": "car",
        "timestamp": 6.0,
        "movement_state": "parked",
        "stationary_duration": 5.0,
        "bbox": [10, 10, 30, 30],
        "position": [20, 20],
    })
    assert len(events) == 0
    assert engine.active_events[99]["duration_sec"] == 5.0

    # Frame 4: vehicle moves again (should close and return finalized event)
    events = engine.feed_observation({
        "vehicle_id": 99,
        "vehicle_type": "car",
        "timestamp": 7.0,
        "movement_state": "moving",
        "stationary_duration": 0.0,
        "bbox": [10, 10, 30, 30],
        "position": [20, 20],
    })
    assert len(events) == 1
    closed_ev = events[0]
    assert closed_ev.vehicle_id == 99
    assert closed_ev.duration_sec >= 5.0
    assert closed_ev.status == "ended"


def test_temporary_disappearance_gap_tolerance():
    """Verify that a brief occlusion does not split an obstruction into two events."""
    engine = ObstructionEventEngine(
        stationary_threshold_sec=2.0,
        max_disappearance_gap_sec=3.0,
    )
    # Start event at t=2.0s
    engine.feed_observation({
        "vehicle_id": 10,
        "vehicle_type": "truck",
        "timestamp": 2.0,
        "movement_state": "parked",
        "stationary_duration": 2.0,
        "bbox": [10, 10, 50, 50],
    })
    assert 10 in engine.active_events

    # Next observation at t=4.0s (2s gap < 3s max gap)
    engine.feed_observation({
        "vehicle_id": 10,
        "vehicle_type": "truck",
        "timestamp": 4.0,
        "movement_state": "parked",
        "stationary_duration": 4.0,
        "bbox": [10, 10, 50, 50],
    })
    # Must still be one active event
    assert 10 in engine.active_events
    assert engine.active_events[10]["duration_sec"] == 4.0


def test_geometry_unit_consistency():
    """Verify that image pixel intersection is normalized against road polygon pixels."""
    road_polygon = [[0, 0], [1000, 0], [1000, 500], [0, 500]]  # 500,000 px^2
    vehicle_bboxes = [[100, 100, 200, 200]]  # 100x100 = 10,000 px^2 (2% of road)

    res = calculate_road_space_metrics(
        vehicle_bboxes=vehicle_bboxes,
        road_polygon_pts=road_polygon,
        road_length_meters=100.0,
        road_width_meters=10.0,
    )
    assert res["occupancy_pct"] == 2.0
    assert res["occupied_area_m2"] == 20.0  # 2% of 1000 m^2
    assert res["occupied_width_meters"] == 0.2  # 20 m^2 / 100m
    assert res["is_calibrated_homography"] is False
    assert res["measurement_method"] == "geometric_polygon_ratio"


def test_geometry_saturation_tests_a_b_c_d():
    """
    Direct verification of Sections 6 & 7:
    Test A: One vehicle occupying ~1.26m of 7m usable road produces ~18%, NOT 100%.
    Test B: Vehicle entirely outside ROI produces 0%.
    Test C: Vehicle partially inside ROI produces 0% < loss < full loss.
    Test D: Multiple vehicles with overlap do not double count.
    """
    from core.geometry import PerspectiveCalibrator

    # Road polygon: 1000 length x 700 width px (ratio corresponds to 100m length x 7m width)
    road_polygon = [[0, 0], [1000, 0], [1000, 700], [0, 700]]  # 700,000 px^2

    # --- Test A: Vehicle occupying 1.26m of 7.0m road width (18.0% of road area)
    # Box spans length from 0 to 1000, height 0 to 126 (126 / 700 = 18.0%)
    res_a = calculate_road_space_metrics(
        vehicle_bboxes=[[0, 0, 1000, 126]],
        road_polygon_pts=road_polygon,
        road_length_meters=100.0,
        road_width_meters=7.0,
    )
    assert res_a["occupancy_pct"] == 18.0, "Must be approximately 18%, not 100%"
    assert res_a["occupied_width_meters"] == 1.26, "Must equal approximately 1.26m"

    # Also test calibrated homography hierarchy
    calibrator = PerspectiveCalibrator(
        src_points=[[0, 0], [1000, 0], [1000, 700], [0, 700]],
        dst_width_m=7.0,
        dst_length_m=100.0,
    )
    res_cal = calculate_road_space_metrics(
        vehicle_bboxes=[[0, 0, 1000, 126]],
        road_polygon_pts=road_polygon,
        road_length_meters=100.0,
        road_width_meters=7.0,
        calibrator=calibrator,
    )
    assert res_cal["is_calibrated_homography"] is True
    assert res_cal["measurement_method"] == "homography_calibrated"
    assert 17.5 <= res_cal["occupancy_pct"] <= 18.5

    # --- Test B: Vehicle entirely outside ROI -> 0%
    res_b = calculate_road_space_metrics(
        vehicle_bboxes=[[2000, 2000, 2100, 2100]],
        road_polygon_pts=road_polygon,
        road_length_meters=100.0,
        road_width_meters=7.0,
    )
    assert res_b["occupancy_pct"] == 0.0
    assert res_b["occupied_area_m2"] == 0.0

    # --- Test C: Vehicle partially inside ROI -> 0% < loss < full
    res_c = calculate_road_space_metrics(
        vehicle_bboxes=[[-100, 0, 100, 700]],  # Half inside: 100x700 = 70,000 px^2 = 10%
        road_polygon_pts=road_polygon,
        road_length_meters=100.0,
        road_width_meters=7.0,
    )
    assert 0.0 < res_c["occupancy_pct"] < 100.0
    assert res_c["occupancy_pct"] == 10.0

    # --- Test D: Multiple overlapping vehicles -> union aware, no double-counting
    box1 = [100, 100, 200, 200]  # 10,000 px^2
    box2 = [100, 100, 200, 200]  # Exact duplicate overlay
    box3 = [150, 150, 250, 250]  # Partially overlapping box
    res_single = calculate_road_space_metrics([box1], road_polygon, 100.0, 7.0)
    res_dup = calculate_road_space_metrics([box1, box2], road_polygon, 100.0, 7.0)
    assert res_single["occupancy_pct"] == res_dup["occupancy_pct"], "Duplicate overlapping boxes must not double count"


def test_historical_recurrence_scoring():
    """Verify recurrence score, peak hours, and chronic zone identification."""
    engine = HistoricalRecurrenceEngine(min_events_for_chronic=3, chronic_recurrence_threshold=0.40)
    events = [
        ObstructionEvent(
            event_id=f"EVT_{i}",
            road_id="TEST_ROAD",
            vehicle_id=i,
            vehicle_type="truck",
            start_time=13.0 * 3600 + i * 60,  # 13:00 - 13:05
            duration_sec=35.0,
            location=[100.0, 100.0 + i],
            road_space_loss_pct=15.0,
            cause="loading_unloading",
        )
        for i in range(5)
    ]
    pattern = engine.analyze_events("TEST_ROAD", events, observation_period_days=1)
    assert pattern.total_events == 5
    assert pattern.is_chronic is True
    assert 13 in pattern.peak_hours
    assert pattern.recurrence_score >= 0.40
    assert pattern.dominant_cause == "loading_unloading"


def test_explainable_cause_classifier():
    """Test cause classification rules and uncertainty handling."""
    classifier = ExplainableCauseClassifier()

    # Case 1: Commercial truck parked for 40s during afternoon
    pred1 = classifier.classify(
        vehicle_type="truck",
        duration_sec=40.0,
        road_space_loss_pct=18.0,
        timestamp=14.0 * 3600,
    )
    assert pred1.cause == "loading_unloading"
    assert pred1.confidence >= 0.65
    assert len(pred1.triggered_rules) > 0
    assert "vehicle_type_commercial" in pred1.feature_contributions
    assert pred1.uncertainty_status in ("confident", "marginal")

    # Case 2: Signal queue zone location
    pred2 = classifier.classify(
        vehicle_type="car",
        duration_sec=10.0,
        road_space_loss_pct=5.0,
        in_waiting_zone=True,
    )
    assert pred2.cause == "traffic_signal_queue"
    assert pred2.confidence >= 0.70

    # Case 3: Borderline ambiguous evidence
    pred3 = classifier.classify(
        vehicle_type="bicycle",
        duration_sec=1.0,
        road_space_loss_pct=0.5,
    )
    assert pred3.uncertainty_status in ("marginal", "uncertain_continue_monitoring")


def test_recommendation_decision_engine():
    """Test candidate intervention ranking trade-offs (recovery vs difficulty vs disruption)."""
    rec_engine = RecommendationDecisionEngine()
    recs = rec_engine.generate_recommendations(
        road_id="ROAD_TEST",
        cause="loading_unloading",
        cause_confidence=0.85,
        road_space_loss_pct=18.0,
        recurrence_score=0.70,
    )
    assert len(recs) >= 2
    # Verify priority ranks 1, 2...
    assert recs[0].priority_rank == 1
    assert recs[1].priority_rank == 2
    # Highest ranked must have positive expected benefit
    assert recs[0].expected_benefit_score > 0
    assert recs[0].estimated_road_space_recovery_pct > 0
    assert "ranking_factors" in recs[0].model_dump()


def test_intervention_outcomes_delta():
    """Verify before-and-after outcome tracking without causal claims."""
    outcome_in = InterventionOutcomeIn(
        road_id="ROAD_001",
        intervention_type="Designated Loading Bay",
        implementation_date="2026-09-15",
        baseline_window_description="14 days prior",
        post_window_description="14 days after",
        baseline_metrics={"avg_duration_sec": 45.0, "avg_loss_pct": 18.0, "daily_frequency": 6.0, "recurrence_score": 0.75},
        post_metrics={"avg_duration_sec": 15.0, "avg_loss_pct": 6.0, "daily_frequency": 2.0, "recurrence_score": 0.25},
    )
    out = InterventionOutcomeService.evaluate_outcome(outcome_in)
    assert out.observed_change["loss_pct_absolute_delta"] == -12.0
    assert out.observed_change["duration_sec_delta"] == -30.0
    assert out.is_causal_claim is False


def test_alert_deduplication_and_cooldown():
    """Verify alerting engine triggers and deduplication cooldown."""
    alert_eng = AlertEngine(cooldown_seconds=10.0)

    # First trigger: severe loss -> returns alert
    a1 = alert_eng.check_obstruction_alert(
        road_id="ALERT_ROAD",
        event_id="EVT_01",
        duration_sec=200.0,
        road_space_loss_pct=45.0,
        severity="critical",
        current_time=100.0,
    )
    assert a1 is not None
    assert a1["alert_type"] == "SEVERE_SPACE_LOSS"

    # Second trigger within cooldown (t=105s, 5s < 10s cooldown) -> suppressed
    a2 = alert_eng.check_obstruction_alert(
        road_id="ALERT_ROAD",
        event_id="EVT_02",
        duration_sec=205.0,
        road_space_loss_pct=46.0,
        severity="critical",
        current_time=105.0,
    )
    assert a2 is None

    # Third trigger after cooldown (t=115s > 10s cooldown) -> allowed
    a3 = alert_eng.check_obstruction_alert(
        road_id="ALERT_ROAD",
        event_id="EVT_03",
        duration_sec=210.0,
        road_space_loss_pct=46.0,
        severity="critical",
        current_time=115.0,
    )
    assert a3 is not None


def test_intervention_simulation():
    """Test scenario simulation engine output."""
    sim_engine = InterventionSimulationEngine()
    req = SimulationRequest(
        road_id="ROAD_001",
        intervention_type="Enforce strict commercial loading time-window restrictions",
        parameters={"compliance_rate": 0.85},
    )
    res = sim_engine.simulate(req, baseline_loss_pct=20.0, baseline_avg_duration_sec=50.0)
    assert res.simulated is True
    assert res.simulated_recovery_pct > 0
    assert res.simulated_loss_pct < res.baseline_loss_pct
    assert res.disclaimer is not None


# ============================================================
# 2. EDGE CASE TESTS
# ============================================================

def test_edge_case_zero_detections():
    """Event engine and recurrence with empty input."""
    engine = ObstructionEventEngine()
    events = engine.process_batch([])
    assert events == []

    rec_engine = HistoricalRecurrenceEngine()
    pattern = rec_engine.analyze_events("EMPTY_ROAD", [])
    assert pattern.total_events == 0
    assert pattern.is_chronic is False


def test_edge_case_single_detection_below_threshold():
    """Single frame detection that does not meet duration threshold is not an obstruction."""
    engine = ObstructionEventEngine(stationary_threshold_sec=5.0)
    events = engine.process_batch([{
        "vehicle_id": 1,
        "vehicle_type": "car",
        "timestamp": 1.0,
        "movement_state": "signal_waiting",
        "stationary_duration": 1.0,
        "bbox": [10, 10, 50, 50],
    }])
    assert len(events) == 0


def test_edge_case_vehicle_disappears_mid_stream():
    """Vehicle that disappears from tracking without moving is closed via timeout."""
    engine = ObstructionEventEngine(
        stationary_threshold_sec=2.0,
        max_disappearance_gap_sec=2.0,
    )
    # t=1.0: vehicle starts parked
    engine.feed_observation({
        "vehicle_id": 7,
        "vehicle_type": "truck",
        "timestamp": 1.0,
        "movement_state": "parked",
        "stationary_duration": 2.5,
        "bbox": [10, 10, 50, 50],
    })
    # t=5.0: observation for a different vehicle, vehicle 7 has disappeared (>2s gap)
    closed = engine.feed_observation({
        "vehicle_id": 8,
        "vehicle_type": "car",
        "timestamp": 5.0,
        "movement_state": "moving",
        "stationary_duration": 0.0,
        "bbox": [20, 20, 40, 40],
    })
    assert any(e.vehicle_id == 7 for e in closed)


def test_event_engine_streaming_vs_batch_equivalence():
    """Section 5: Proves batch processing and streaming produce logically equivalent events."""
    obs_sequence = [
        {"vehicle_id": 1, "vehicle_type": "car", "timestamp": 1.0, "movement_state": "moving", "stationary_duration": 0.0, "bbox": [10, 10, 40, 40]},
        {"vehicle_id": 1, "vehicle_type": "car", "timestamp": 2.0, "movement_state": "parked", "stationary_duration": 1.0, "bbox": [10, 10, 40, 40]},
        {"vehicle_id": 1, "vehicle_type": "car", "timestamp": 5.0, "movement_state": "parked", "stationary_duration": 4.0, "bbox": [10, 10, 40, 40]},
        {"vehicle_id": 1, "vehicle_type": "car", "timestamp": 8.0, "movement_state": "parked", "stationary_duration": 7.0, "bbox": [10, 10, 40, 40]},
        {"vehicle_id": 1, "vehicle_type": "car", "timestamp": 10.0, "movement_state": "moving", "stationary_duration": 0.0, "bbox": [10, 10, 40, 40]},
        {"vehicle_id": 2, "vehicle_type": "truck", "timestamp": 11.0, "movement_state": "parked", "stationary_duration": 5.0, "bbox": [50, 50, 90, 90]},
        {"vehicle_id": 2, "vehicle_type": "truck", "timestamp": 15.0, "movement_state": "parked", "stationary_duration": 9.0, "bbox": [50, 50, 90, 90]},
    ]

    # Streaming mode
    engine_stream = ObstructionEventEngine(stationary_threshold_sec=3.0, max_disappearance_gap_sec=2.0)
    stream_events = []
    for obs in obs_sequence:
        closed = engine_stream.feed_observation(obs)
        stream_events.extend(closed)
    stream_events.extend(engine_stream.flush())

    # Batch mode
    engine_batch = ObstructionEventEngine(stationary_threshold_sec=3.0, max_disappearance_gap_sec=2.0)
    batch_events = engine_batch.process_batch(obs_sequence)

    assert len(stream_events) == len(batch_events) == 2
    for s_ev, b_ev in zip(stream_events, batch_events):
        assert s_ev.vehicle_id == b_ev.vehicle_id
        assert s_ev.start_time == b_ev.start_time
        assert s_ev.duration_sec == b_ev.duration_sec
        assert s_ev.cause == b_ev.cause
        assert s_ev.severity == b_ev.severity


def test_event_engine_malformed_and_unsorted_observations():
    """Section 5: Proves event engine handles missing fields, zero bboxes, strings for IDs, unsorted timestamps without crashing."""
    engine = ObstructionEventEngine(stationary_threshold_sec=2.0)
    malformed_list = [
        {},  # empty
        {"vehicle_id": None},  # missing ID
        {"vehicle_id": "abc"},  # non-integer string ID
        {"vehicle_id": 42},  # missing timestamp, bbox, movement_state
        {"vehicle_id": 42, "timestamp": "invalid_ts"},  # invalid timestamp
        {"vehicle_id": "42", "timestamp": 10.0, "movement_state": "parked", "stationary_duration": 4.0},  # string ID '42'
        {"vehicle_id": 42, "timestamp": 5.0, "movement_state": "parked", "stationary_duration": 2.0},  # unsorted older timestamp
        {"vehicle_id": 42, "timestamp": 10.0, "movement_state": "parked", "stationary_duration": 4.0},  # duplicate observation
    ]
    events = engine.process_batch(malformed_list)
    assert isinstance(events, list)


def test_single_event_severity_distinction():
    """Section 13: Proves an isolated severe stop is labeled with single_event_severity=True, NOT is_chronic=True."""
    engine = HistoricalRecurrenceEngine(min_events_for_chronic=3, chronic_recurrence_threshold=0.40)
    isolated_severe_event = [
        ObstructionEvent(
            event_id="EVT_ISOLATED_LONG",
            road_id="ROAD_ISOLATED",
            vehicle_id=55,
            vehicle_type="truck",
            start_time=12.0 * 3600,
            duration_sec=120.0,  # 2 minute stop
            road_space_loss_pct=35.0,  # 35% loss
            cause="loading_unloading",
        )
    ]
    pattern = engine.analyze_events("ROAD_ISOLATED", isolated_severe_event, observation_period_days=1)
    assert pattern.total_events == 1
    assert pattern.is_chronic is False, "A single isolated event must NOT be classified as chronic"
    assert pattern.single_event_severity is True, "Must be explicitly classified as single_event_severity"
    assert pattern.severity == "critical"


def test_no_fabricated_metrics_rule():
    """Section 14, 15, 16, 46: Verify that the system does not fabricate ML accuracy, precision, recall, or F1."""
    registry = ContinuousLearningRegistry()
    deployed = registry.get_deployed_version()
    assert deployed["model_type"] == "rule_based"
    assert deployed["accuracy"] == "not_evaluated"
    assert deployed["f1_score"] == "not_evaluated"
    assert deployed["is_measured"] is False


# ============================================================
# 3. FASTAPI API TESTS
# ============================================================

def test_api_health_check(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_api_obstruction_events_ingest_and_list(client):
    payload = {
        "event_id": "TEST_EVT_API_01",
        "road_id": "ROAD_TEST_API",
        "vehicle_id": 101,
        "vehicle_type": "truck",
        "start_time": 10.0,
        "end_time": 25.0,
        "duration_sec": 15.0,
        "location": [150.0, 200.0],
        "road_space_loss_pct": 14.5,
        "cause": "loading_unloading",
        "cause_confidence": 0.85,
        "severity": "moderate",
    }
    # Ingest single
    res = client.post("/events", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["event_id"] == "TEST_EVT_API_01"
    assert data["road_id"] == "ROAD_TEST_API"

    # List events
    res_list = client.get("/events?road_id=ROAD_TEST_API")
    assert res_list.status_code == 200
    events = res_list.json()
    assert len(events) >= 1
    assert any(e["event_id"] == "TEST_EVT_API_01" for e in events)


def test_api_cause_prediction(client):
    req = {
        "road_id": "ROAD_001",
        "vehicle_type": "truck",
        "duration_sec": 45.0,
        "road_space_loss_pct": 22.0,
        "timestamp": 13.5 * 3600,
    }
    res = client.post("/causes/predict", json=req)
    assert res.status_code == 200
    data = res.json()
    assert data["cause"] == "loading_unloading"
    assert data["confidence"] > 0.5
    assert len(data["triggered_rules"]) > 0


def test_api_recommendation_generate(client):
    # Ensure road exists first
    client.post("/roads", json={"id": "ROAD_REC_API", "name": "Rec Test Road", "latitude": 0.0, "longitude": 0.0})

    req = {
        "road_id": "ROAD_REC_API",
        "cause": "illegal_parking",
        "cause_confidence": 0.85,
        "road_space_loss_pct": 20.0,
    }
    res = client.post("/recommendations/generate", json=req)
    assert res.status_code == 200
    data = res.json()
    assert data["road_id"] == "ROAD_REC_API"
    assert len(data["recommendations"]) >= 1


def test_api_human_feedback(client):
    client.post("/roads", json={"id": "ROAD_FB_API", "name": "FB Test Road", "latitude": 0.0, "longitude": 0.0})
    fb_payload = {
        "event_id": "TEST_EVT_API_01",
        "road_id": "ROAD_FB_API",
        "feedback_type": "cause_correction",
        "original_value": "loading_unloading",
        "corrected_value": "illegal_parking",
        "accepted": False,
        "notes": "Driver was parked eating lunch, not loading goods.",
        "authority_user": "warden_42",
    }
    res = client.post("/feedback", json=fb_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["corrected_value"] == "illegal_parking"
    assert data["authority_user"] == "warden_42"

    # Verify retrieval
    res_list = client.get("/feedback?road_id=ROAD_FB_API")
    assert res_list.status_code == 200
    assert len(res_list.json()) >= 1


def test_api_intervention_outcome(client):
    client.post("/roads", json={"id": "ROAD_OUTCOME_API", "name": "Outcome Road", "latitude": 0.0, "longitude": 0.0})
    outcome_payload = {
        "road_id": "ROAD_OUTCOME_API",
        "intervention_type": "Targeted Parking Enforcement",
        "implementation_date": "2026-09-20",
        "baseline_window_description": "7 days pre",
        "post_window_description": "7 days post",
        "baseline_metrics": {"avg_loss_pct": 22.0, "avg_duration_sec": 40.0, "daily_frequency": 5.0, "recurrence_score": 0.70},
        "post_metrics": {"avg_loss_pct": 8.0, "avg_duration_sec": 12.0, "daily_frequency": 1.5, "recurrence_score": 0.20},
    }
    res = client.post("/interventions/outcome", json=outcome_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["observed_change"]["loss_pct_absolute_delta"] == -14.0
    assert data["is_causal_claim"] is False

    # Get list
    res_list = client.get("/interventions/outcomes?road_id=ROAD_OUTCOME_API")
    assert res_list.status_code == 200
    assert len(res_list.json()) >= 1


def test_api_simulations(client):
    client.post("/roads", json={"id": "ROAD_SIM_API", "name": "Sim Road", "latitude": 0.0, "longitude": 0.0})
    sim_req = {
        "road_id": "ROAD_SIM_API",
        "intervention_type": "Recessed Loading Bay",
        "parameters": {"compliance_rate": 0.90},
    }
    res = client.post("/simulations/intervention", json=sim_req)
    assert res.status_code == 200
    data = res.json()
    assert data["simulated"] is True
    assert data["simulated_recovery_pct"] > 0


def test_api_alerts_and_acknowledgement(client):
    client.post("/roads", json={"id": "ROAD_ALERT_API", "name": "Alert Road", "latitude": 0.0, "longitude": 0.0})
    # Ingest severe event to trigger alert
    ev_payload = {
        "event_id": "EVT_TRIGGER_ALERT_99",
        "road_id": "ROAD_ALERT_API",
        "vehicle_id": 999,
        "vehicle_type": "truck",
        "start_time": 10.0,
        "duration_sec": 300.0,
        "road_space_loss_pct": 45.0,
        "severity": "critical",
    }
    client.post("/events", json=ev_payload)

    # Check alert was created
    alerts_res = client.get("/alerts?road_id=ROAD_ALERT_API")
    assert alerts_res.status_code == 200
    alerts = alerts_res.json()
    assert len(alerts) >= 1
    alert_id = alerts[0]["id"]
    assert alerts[0]["status"] == "active"

    # Acknowledge alert
    ack_res = client.post(f"/alerts/{alert_id}/acknowledge", json={"acknowledged_by": "operator_jane"})
    assert ack_res.status_code == 200
    assert ack_res.json()["status"] == "acknowledged"
    assert ack_res.json()["acknowledged_by"] == "operator_jane"


def test_api_models_versions(client):
    res = client.get("/models/versions")
    assert res.status_code == 200
    data = res.json()
    assert "versions" in data
    assert "deployed_version" in data


def test_api_duplicate_event_ingestion_idempotency(client):
    """Section 25 & 48: POST same event twice results in single upserted record, no duplication."""
    client.post("/roads", json={"id": "ROAD_IDEMP", "name": "Idemp Road", "latitude": 0.0, "longitude": 0.0})
    payload = {
        "event_id": "EVT_IDEMP_TEST_01",
        "road_id": "ROAD_IDEMP",
        "vehicle_id": 501,
        "vehicle_type": "car",
        "start_time": 100.0,
        "duration_sec": 45.0,
        "road_space_loss_pct": 12.0,
        "cause": "illegal_parking",
    }
    # Ingest first time
    res1 = client.post("/events", json=payload)
    assert res1.status_code == 200
    # Ingest second time
    res2 = client.post("/events", json=payload)
    assert res2.status_code == 200

    # Query events for road
    list_res = client.get("/events?road_id=ROAD_IDEMP")
    assert list_res.status_code == 200
    events = [e for e in list_res.json() if e["event_id"] == "EVT_IDEMP_TEST_01"]
    assert len(events) == 1, "Duplicate event_id ingestion must be idempotent"


def test_api_duplicate_window_ingestion_idempotency(client):
    """Section 8 & 48: POST same analytical window twice performs upsert, no duplication."""
    client.post("/roads", json={"id": "ROAD_WINDOW_IDEMP", "name": "Window Idemp Road", "latitude": 0.0, "longitude": 0.0})
    window_payload = {
        "observations": [
            {
                "road_id": "ROAD_WINDOW_IDEMP",
                "road_name": "Window Idemp Road",
                "window_index": 1,
                "window_start": 0.0,
                "window_end": 10.0,
                "window_start_seconds": 0.0,
                "window_end_seconds": 10.0,
                "vehicle_count": 3,
                "occupancy_pct": 15.0,
                "blocked_pct": 10.0,
                "cause": "illegal_parking",
                "cause_explanation": "Parked cars observed",
            }
        ]
    }
    # Send twice
    r1 = client.post("/analysis/bulk", json=window_payload)
    r2 = client.post("/analysis/bulk", json=window_payload)
    assert r1.status_code == 200
    assert r2.status_code == 200

    hist_res = client.get("/roads/ROAD_WINDOW_IDEMP/history")
    assert hist_res.status_code == 200
    windows = [w for w in hist_res.json() if w["window_index"] == 1]
    assert len(windows) == 1, "Duplicate window index must be upserted idempotently"


# ============================================================
# 4. REGRESSION TESTS (PRESERVING EXISTING FUNCTIONALITY)
# ============================================================

def test_regression_existing_endpoints(client):
    """Verify that existing Person 3 routes for Person 5 GIS and Person 6 Frontend are unbroken."""
    # /roads list
    res_roads = client.get("/roads")
    assert res_roads.status_code == 200

    # /chronic-zones list
    res_cz = client.get("/chronic-zones")
    assert res_cz.status_code == 200

    # /recommendations list
    res_recs = client.get("/recommendations")
    assert res_recs.status_code == 200


# ============================================================
# 5. INTEGRATION TEST: P1 -> P2 -> P3 -> P4
# ============================================================

def test_full_pipeline_integration(client):
    """
    End-to-End closed loop trace:
    P1 Detections -> ObstructionEvent -> P2 Analysis -> P3 Backend -> P4 Recurrence & Recommendation -> Feedback -> Outcome
    """
    import json
    dets_path = ROOT_DIR / "person1_detection" / "output" / "detections.json"
    roi_path = ROOT_DIR / "person2_analysis" / "roi_config.json"
    assert dets_path.exists(), "detections.json must exist"
    assert roi_path.exists(), "roi_config.json must exist"

    with open(dets_path) as f:
        dets = json.load(f)
    with open(roi_path) as f:
        roi = json.load(f)

    # 1. P1 Tracks -> Obstruction Events
    event_engine = ObstructionEventEngine(
        stationary_threshold_sec=4.0,
        max_disappearance_gap_sec=3.0,
        road_width_m=roi["road_width_meters"],
        road_length_m=roi["road_length_meters"],
        road_polygon=roi["road_polygon"],
    )
    events = event_engine.process_batch(dets[:4000])
    assert len(events) > 0, "Must create obstruction events from sample detections"

    # 2. Ingest Events into P3 Backend
    events_payload = [e.model_dump() for e in events]
    bulk_res = client.post("/events/bulk", json={"events": events_payload})
    assert bulk_res.status_code == 200

    # 3. P4 Recurrence Analysis
    rec_engine = HistoricalRecurrenceEngine()
    pattern = rec_engine.analyze_events("ROAD_001", events, observation_period_days=1)
    assert pattern.total_events == len(events)

    # 4. Cause Diagnosis & Recommendations Generation (Actual Confidence, No Fabrication)
    cause_diag = ExplainableCauseClassifier().classify(
        vehicle_type=events[0].vehicle_type,
        duration_sec=pattern.average_duration_sec,
        road_space_loss_pct=pattern.average_road_space_loss_pct,
        recurrence_score=pattern.recurrence_score,
    )
    rec_res = client.post("/recommendations/generate", json={
        "road_id": "ROAD_001",
        "cause": pattern.dominant_cause,
        "cause_confidence": cause_diag.confidence,
        "road_space_loss_pct": pattern.average_road_space_loss_pct,
    })
    assert rec_res.status_code == 200
    assert len(rec_res.json()["recommendations"]) > 0

    # 5. Authority Feedback
    fb_res = client.post("/feedback", json={
        "event_id": events[0].event_id,
        "road_id": "ROAD_001",
        "feedback_type": "cause_confirmation",
        "accepted": True,
        "notes": "Verified by traffic engineer",
    })
    assert fb_res.status_code == 200

    # 6. Authority Simulation (Separated from real outcomes)
    sim_res = client.post("/simulations/intervention", json={
        "road_id": "ROAD_001",
        "intervention_type": "Designated recessed loading bay",
    })
    assert sim_res.status_code == 200
    assert sim_res.json()["simulated"] is True
    assert sim_res.json()["data_source"] == "historical"

    # 7. Authority Outcome Tracking (Synthetic Test Fixture for Math Verification)
    outcome_res = client.post("/interventions/outcome", json={
        "road_id": "ROAD_001",
        "intervention_type": "Designated Loading Bay",
        "implementation_date": "2026-09-28",
        "baseline_window_description": "Initial video baseline (synthetic fixture)",
        "post_window_description": "Post-intervention validation window (synthetic fixture)",
        "baseline_metrics": {
            "avg_loss_pct": pattern.average_road_space_loss_pct,
            "avg_duration_sec": pattern.average_duration_sec,
            "daily_frequency": float(len(events)),
            "recurrence_score": pattern.recurrence_score,
        },
        "post_metrics": {
            "avg_loss_pct": round(pattern.average_road_space_loss_pct * 0.4, 2),
            "avg_duration_sec": round(pattern.average_duration_sec * 0.5, 1),
            "daily_frequency": 1.0,
            "recurrence_score": 0.15,
        },
        "notes": "SYNTHETIC_TEST_DATA: Controlled test fixture for delta calculation verification only",
    })
    assert outcome_res.status_code == 200
    out_data = outcome_res.json()
    assert out_data["is_causal_claim"] is False
    assert out_data["observed_change"]["loss_pct_absolute_delta"] < 0
