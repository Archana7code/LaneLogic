"""
LaneLogic - Continuous Model Improvement Architecture
======================================================
Collects authority feedback, corrected ground truth labels, and hard ambiguous events
into versioned training sets.
Tracks model versions, validation benchmarks, class distribution, and drift indicators.
Follows the engineering rule: never automatically retrain on every feedback item without
quality checks and fixed validation set evaluation.
"""

from typing import Dict, List, Optional, Any
import json
import time


class ContinuousLearningRegistry:
    """
    Manages versioned model artifacts and training dataset snapshots.
    """

    DEFAULT_VERSIONS = [
        {
            "version": "rule_engine_v1.0",
            "type": "transparent_rules",
            "model_type": "rule_based",
            "release_date": "2026-09-01",
            "accuracy": "not_evaluated",
            "f1_score": "not_evaluated",
            "is_measured": False,
            "status": "deprecated",
            "description": "Initial baseline rules",
        },
        {
            "version": "rule_engine_v2.2",
            "type": "explainable_rules_multi_criteria",
            "model_type": "rule_based",
            "release_date": "2026-09-28",
            "accuracy": "not_evaluated",
            "f1_score": "not_evaluated",
            "is_measured": False,
            "status": "deployed",
            "description": "Multi-criteria cause classifier with uncertainty detection and feature attribution (no synthetic metrics)",
        },
    ]

    def __init__(self):
        self.versions = list(self.DEFAULT_VERSIONS)
        self.dataset_snapshots: List[Dict[str, Any]] = []

    def get_deployed_version(self) -> Dict[str, Any]:
        for v in self.versions:
            if v.get("status") == "deployed":
                return v
        return self.versions[-1]

    def create_dataset_snapshot(
        self,
        feedback_records: List[Dict[str, Any]],
        snapshot_id: str,
        dataset_version: str = "v1.0",
        min_samples_for_validation: int = 50,
    ) -> Dict[str, Any]:
        """
        Snapshots human feedback corrections as a candidate labeled training partition.
        Includes sample count, class distribution, source feedback IDs, and validation readiness.
        """
        labeled_samples = []
        source_feedback_ids = []
        class_distribution: Dict[str, int] = {}

        for fb in feedback_records:
            if fb.get("corrected_value"):
                corr_cause = fb.get("corrected_value")
                fb_id = fb.get("id") or fb.get("event_id")
                if fb_id:
                    source_feedback_ids.append(fb_id)

                class_distribution[corr_cause] = class_distribution.get(corr_cause, 0) + 1

                labeled_samples.append({
                    "event_id": fb.get("event_id"),
                    "road_id": fb.get("road_id"),
                    "ground_truth_cause": corr_cause,
                    "feedback_type": fb.get("feedback_type"),
                    "timestamp": fb.get("created_at") or time.time(),
                })

        # Validation readiness is explicitly checked against configurable class balance and threshold
        validation_ready = (
            len(labeled_samples) >= min_samples_for_validation
            and len(class_distribution) >= 3  # Requires diversity of causes
        )

        snapshot = {
            "snapshot_id": snapshot_id,
            "dataset_version": dataset_version,
            "created_at": time.time(),
            "sample_count": len(labeled_samples),
            "class_distribution": class_distribution,
            "source_feedback_ids": source_feedback_ids,
            "validation_ready": validation_ready,
            "min_samples_required": min_samples_for_validation,
            "samples": labeled_samples,
        }
        self.dataset_snapshots.append(snapshot)
        return snapshot
