"""
LaneLogic - Explainable Cause Classification Engine
====================================================
Transparent, rule-backed and evidence-attributed cause classifier.
Computes cause probabilities, feature attributions, explicit confidence metrics,
and uncertainty status for road obstruction events.
"""

from typing import Dict, List, Optional, Any
from core.contracts import CausePrediction
from core.config import (
    CONFIDENCE_CONFIDENT_THRESHOLD,
    CONFIDENCE_MARGINAL_THRESHOLD,
    CONFIDENCE_DIFF_MARGIN,
)


class ExplainableCauseClassifier:
    """
    Evaluates obstruction event evidence against traffic engineering rules.
    Outputs the likely cause, confidence, triggered rules, and feature contributions.
    """

    VERSION = "rule_engine_v2.2"

    def __init__(self, school_hours: Optional[Dict[str, str]] = None):
        self.school_hours = school_hours or {"start": "07:30", "end": "09:00"}

    def classify(
        self,
        vehicle_type: str,
        duration_sec: float,
        road_space_loss_pct: float,
        timestamp: float = 0.0,
        in_waiting_zone: bool = False,
        cluster_count: int = 1,
        recurrence_score: float = 0.0,
        road_context: Optional[Dict[str, Any]] = None,
    ) -> CausePrediction:
        """
        Classifies the cause of an obstruction event using multi-criteria evidence scoring.
        """
        hour = int(timestamp // 3600) % 24 if timestamp > 0 else 14  # Default afternoon if 0

        # Score accumulator for candidate causes (Person 2 Canonical Taxonomy)
        scores: Dict[str, float] = {
            "loading_unloading": 0.0,
            "illegal_parking": 0.0,
            "school_dropoff": 0.0,
            "traffic_signal_queue": 0.0,
            "general_congestion": 0.0,
            "unclassified": 0.0,
        }

        triggered_rules: List[str] = []
        feature_contributions: Dict[str, float] = {}

        # ----------------------------------------------------
        # Rule 1: Signal Queue Zone
        # ----------------------------------------------------
        if in_waiting_zone:
            scores["traffic_signal_queue"] += 0.95
            triggered_rules.append("Vehicle located inside designated signal/waiting queue zone.")
            feature_contributions["location_in_queue_zone"] = 0.95
        else:
            # ----------------------------------------------------
            # Rule 2: Vehicle Type & Duration (Outside Queue Zone)
            # ----------------------------------------------------
            vtype = vehicle_type.lower()
            if vtype in ("truck", "bus"):
                if duration_sec >= 20.0:
                    scores["loading_unloading"] += 0.75
                    triggered_rules.append(f"Commercial vehicle ({vtype}) stationary for >=20s ({duration_sec:.1f}s).")
                    feature_contributions["vehicle_type_commercial"] = 0.45
                    feature_contributions["duration_loading_threshold"] = 0.30
                else:
                    scores["loading_unloading"] += 0.40
                    scores["unclassified"] += 0.30
                    triggered_rules.append(f"Commercial vehicle ({vtype}) stopped briefly ({duration_sec:.1f}s).")
            elif vtype in ("car", "motorcycle", "bicycle"):
                if duration_sec >= 45.0:
                    scores["illegal_parking"] += 0.80
                    triggered_rules.append(f"Private vehicle ({vtype}) parked for prolonged duration ({duration_sec:.1f}s).")
                    feature_contributions["duration_parked_threshold"] = 0.50
                    feature_contributions["vehicle_type_private"] = 0.30
                elif duration_sec >= 15.0:
                    scores["illegal_parking"] += 0.65
                    scores["unclassified"] += 0.20
                    triggered_rules.append(f"Vehicle ({vtype}) stationary outside queue zone ({duration_sec:.1f}s).")
                else:
                    scores["unclassified"] += 0.60
                    triggered_rules.append(f"Brief stop ({duration_sec:.1f}s) under parking threshold.")
                    feature_contributions["short_duration"] = 0.60
            elif "auto" in vtype or "rickshaw" in vtype:
                if cluster_count >= 2:
                    scores["illegal_parking"] += 0.75
                    triggered_rules.append(f"Clustering of {cluster_count} auto-rickshaws suggests informal staging.")
                    feature_contributions["auto_clustering"] = 0.75
                else:
                    scores["unclassified"] += 0.50

            # ----------------------------------------------------
            # Rule 3: Time-of-Day / School Hours
            # ----------------------------------------------------
            is_school_time = 7 <= hour <= 9 or 14 <= hour <= 16
            if is_school_time and vtype in ("car", "motorcycle") and duration_sec < 60.0:
                scores["school_dropoff"] += 0.55
                triggered_rules.append(f"Activity during peak drop-off/pickup window ({hour:02d}:00).")
                feature_contributions["school_hours_alignment"] = 0.55

        # ----------------------------------------------------
        # Rule 4: Road Space Loss & General Congestion Profile
        # ----------------------------------------------------
        if road_space_loss_pct >= 35.0 and duration_sec >= 300.0:
            scores["illegal_parking"] += 0.40
            triggered_rules.append(f"Large static footprint ({road_space_loss_pct:.1f}% width loss) for extended duration.")
            feature_contributions["severe_footprint_loss"] = 0.40
        elif road_space_loss_pct < 10.0 and duration_sec < 10.0:
            scores["unclassified"] += 0.30

        # ----------------------------------------------------
        # Rule 5: Recurrence Amplification
        # ----------------------------------------------------
        if recurrence_score >= 0.50:
            if scores["loading_unloading"] > 0.3:
                scores["loading_unloading"] += 0.15
            if scores["illegal_parking"] > 0.3:
                scores["illegal_parking"] += 0.15
            feature_contributions["historical_recurrence"] = 0.15

        # Normalize score ratio (heuristic evidence attribution weight)
        total_score = sum(scores.values())
        if total_score > 0:
            probs = {k: v / total_score for k, v in scores.items()}
        else:
            probs = {"unclassified": 1.0}
            scores["unclassified"] = 1.0

        sorted_candidates = sorted(probs.items(), key=lambda item: item[1], reverse=True)
        top_cause, top_prob = sorted_candidates[0]
        second_cause, second_prob = sorted_candidates[1] if len(sorted_candidates) > 1 else ("", 0.0)

        # Confidence is a transparent heuristic rule evidence attribution score (0.0-1.0), NOT a statistical ML probability
        confidence = round(min(0.95, top_prob), 2)
        if top_cause == "unclassified":
            confidence = 0.30

        # Scarcity of evidence check: minimal duration or negligible loss caps confidence score
        if duration_sec < 3.0 or road_space_loss_pct < 1.0:
            confidence = min(confidence, 0.40)

        # Explicit uncertainty communication
        if confidence >= CONFIDENCE_CONFIDENT_THRESHOLD and (top_prob - second_prob) >= CONFIDENCE_DIFF_MARGIN:
            uncertainty_status = "confident"
        elif confidence >= CONFIDENCE_MARGINAL_THRESHOLD:
            uncertainty_status = "marginal"
        else:
            uncertainty_status = "uncertain_continue_monitoring"

        explanation_parts = []
        if top_cause == "loading_unloading":
            explanation_parts.append(f"Truck/commercial activity with {road_space_loss_pct:.1f}% road loss suggests freight loading/unloading.")
        elif top_cause == "illegal_parking":
            explanation_parts.append(f"Stationary parked vehicle blocking usable road width outside designated bays.")
        elif top_cause == "school_dropoff":
            explanation_parts.append(f"Short-duration stops during school hours creating curb friction.")
        elif top_cause == "traffic_signal_queue":
            explanation_parts.append(f"Vehicles queued within intersection signal approach.")
        elif top_cause == "general_congestion":
            explanation_parts.append(f"Elevated road-space occupancy without localized stationary obstruction.")
        else:
            explanation_parts.append("Road occupancy is elevated but available vehicle states do not match a specific cause profile.")

        explanation = " ".join(explanation_parts)

        alternative_causes = [
            {"cause": c, "probability": round(p, 2)}
            for c, p in sorted_candidates[1:4]
            if p > 0.05
        ]

        return CausePrediction(
            cause=top_cause,
            confidence=confidence,
            explanation=explanation,
            triggered_rules=triggered_rules,
            feature_contributions=feature_contributions,
            uncertainty_status=uncertainty_status,
            model_type="rule_based",
            model_version=self.VERSION,
            alternative_causes=alternative_causes,
        )


def normalize_cause_name(cause: Optional[str]) -> str:
    """
    Normalizes cause strings across Person 2 vocabulary and legacy variations.
    Canonical Person 2 cause values:
      - traffic_signal_queue
      - loading_unloading
      - school_dropoff (or school_drop_off)
      - illegal_parking
      - general_congestion
      - normal
      - unclassified
    """
    if not cause:
        return "unclassified"
    c = str(cause).strip().lower()
    mapping = {
        "school_drop_off": "school_dropoff",
        "school_dropoff": "school_dropoff",
        "loading/unloading": "loading_unloading",
        "signal_queue": "traffic_signal_queue",
        "traffic_signal": "traffic_signal_queue",
        "temporary_stopping": "unclassified",
        "informal_auto_stand": "illegal_parking",
        "construction_obstruction": "illegal_parking",
    }
    return mapping.get(c, c)
