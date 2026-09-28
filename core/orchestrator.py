"""
LaneLogic - End-to-End Closed-Loop Pipeline Orchestrator
=========================================================
Connects all layers into a single coherent, reproducible workflow:
P1 Detections -> ObstructionEventEngine -> Geometry -> P3 Ingestion ->
Historical Recurrence -> Cause Classifier -> Recommendation Decision Engine.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
import requests

from core.event_engine import ObstructionEventEngine
from core.geometry import calculate_road_space_metrics, PerspectiveCalibrator
from core.recurrence import HistoricalRecurrenceEngine
from core.cause_classifier import ExplainableCauseClassifier, normalize_cause_name
from core.interventions import RecommendationDecisionEngine
from core.contracts import ObstructionEvent, HistoricalPattern, InterventionRecommendation
from core.config import (
    DEFAULT_STATIONARY_THRESHOLD_SEC,
    DEFAULT_MAX_DISAPPEARANCE_GAP_SEC,
    MIN_EVENTS_FOR_CHRONIC,
    CHRONIC_RECURRENCE_THRESHOLD,
    CHRONIC_MIN_PARKED_SPACE_PCT,
)


class ClosedLoopOrchestrator:
    """
    Unified pipeline orchestrator executing the complete LaneLogic workflow.
    """

    def __init__(self, api_url: Optional[str] = None):
        self.api_url = api_url.rstrip("/") if api_url else None
        self.cause_classifier = ExplainableCauseClassifier()
        self.rec_engine = RecommendationDecisionEngine()
        self.recurrence_engine = HistoricalRecurrenceEngine(
            min_events_for_chronic=MIN_EVENTS_FOR_CHRONIC,
            chronic_recurrence_threshold=CHRONIC_RECURRENCE_THRESHOLD,
        )

    def run_pipeline(
        self,
        detections: List[Dict[str, Any]],
        roi_config: Dict[str, Any],
        road_id: str = "ROAD_001",
        observation_period_days: int = 1,
        push_to_backend: bool = True,
    ) -> Dict[str, Any]:
        """
        Executes the full pipeline for a set of vehicle detections.
        """
        road_width = float(roi_config.get("road_width_meters", 10.0))
        road_length = float(roi_config.get("road_length_meters", 120.0))
        road_poly = roi_config.get("road_polygon")
        queue_poly = (
            roi_config.get("signal_queue_zone", {}).get("polygon")
            if isinstance(roi_config.get("signal_queue_zone"), dict)
            else roi_config.get("signal_queue_zone")
        )

        # ----------------------------------------------------
        # Step 1: P1 Detection Tracks -> Event Engine
        # ----------------------------------------------------
        event_engine = ObstructionEventEngine(
            stationary_threshold_sec=DEFAULT_STATIONARY_THRESHOLD_SEC,
            max_disappearance_gap_sec=DEFAULT_MAX_DISAPPEARANCE_GAP_SEC,
            road_width_m=road_width,
            road_length_m=road_length,
            road_polygon=road_poly,
            queue_polygon=queue_poly,
        )
        events: List[ObstructionEvent] = event_engine.process_batch(detections)

        # ----------------------------------------------------
        # Step 2: Road-Space Measurement Verification
        # ----------------------------------------------------
        sample_bboxes = [e.bbox for e in events if e.bbox and len(e.bbox) >= 4]
        geometry_metrics = calculate_road_space_metrics(
            vehicle_bboxes=sample_bboxes[:10],
            road_polygon_pts=road_poly,
            road_length_meters=road_length,
            road_width_meters=road_width,
        )

        # ----------------------------------------------------
        # Step 3: Backend Ingestion (Optional)
        # ----------------------------------------------------
        ingestion_status = "skipped_no_api"
        if push_to_backend and self.api_url:
            try:
                payload = [e.model_dump() for e in events]
                resp = requests.post(f"{self.api_url}/events/bulk", json={"events": payload}, timeout=10)
                resp.raise_for_status()
                ingestion_status = f"pushed_{len(events)}_events"
            except Exception as e:
                ingestion_status = f"error_{e}"

        # ----------------------------------------------------
        # Step 4: Historical Recurrence Analysis
        # ----------------------------------------------------
        pattern: HistoricalPattern = self.recurrence_engine.analyze_events(
            road_id=road_id,
            events=events,
            observation_period_days=observation_period_days,
        )

        # ----------------------------------------------------
        # Step 5: Cause Classification & Explainability
        # ----------------------------------------------------
        sample_event = events[0] if events else None
        cause_pred = self.cause_classifier.classify(
            vehicle_type=sample_event.vehicle_type if sample_event else "car",
            duration_sec=pattern.average_duration_sec,
            road_space_loss_pct=pattern.average_road_space_loss_pct,
            recurrence_score=pattern.recurrence_score,
        )

        # ----------------------------------------------------
        # Step 6: Intervention Decision Engine
        # ----------------------------------------------------
        recommendations: List[InterventionRecommendation] = self.rec_engine.generate_recommendations(
            road_id=road_id,
            cause=pattern.dominant_cause if pattern.dominant_cause != "normal" else cause_pred.cause,
            cause_confidence=cause_pred.confidence,
            road_space_loss_pct=pattern.average_road_space_loss_pct,
            recurrence_score=pattern.recurrence_score,
            evidence_summary=pattern.evidence_summary,
        )

        return {
            "road_id": road_id,
            "total_detections_processed": len(detections),
            "canonical_events_count": len(events),
            "events": [e.model_dump() for e in events],
            "geometry_metrics": geometry_metrics,
            "backend_ingestion": ingestion_status,
            "recurrence_pattern": pattern.model_dump(),
            "cause_diagnosis": cause_pred.model_dump(),
            "recommendations": [r.model_dump() for r in recommendations],
        }
