"""
LaneLogic - Intervention Outcome Tracking Service
==================================================
Measures whether observed obstruction metrics changed after an authority
implemented an intervention on a road.
Explicitly distinguishes observed before/after associations from causal claims.
"""

from typing import Dict, Any
from core.contracts import InterventionOutcomeIn, InterventionOutcomeOut


class InterventionOutcomeService:
    """
    Computes before-and-after metric deltas (duration, road space loss,
    daily frequency, recurrence score) for an implemented intervention.
    """

    @staticmethod
    def evaluate_outcome(outcome_in: InterventionOutcomeIn, outcome_id: int = 1, recorded_at: Any = None) -> InterventionOutcomeOut:
        b = outcome_in.baseline_metrics
        p = outcome_in.post_metrics

        observed_change: Dict[str, float] = {}

        # 1. Road-space loss change
        b_loss = float(b.get("avg_loss_pct", 0.0))
        p_loss = float(p.get("avg_loss_pct", 0.0))
        observed_change["loss_pct_absolute_delta"] = round(p_loss - b_loss, 2)
        observed_change["loss_pct_relative_change"] = (
            round(((p_loss - b_loss) / max(0.01, b_loss)) * 100.0, 1) if b_loss > 0 else 0.0
        )

        # 2. Duration change
        b_dur = float(b.get("avg_duration_sec", 0.0))
        p_dur = float(p.get("avg_duration_sec", 0.0))
        observed_change["duration_sec_delta"] = round(p_dur - b_dur, 1)
        observed_change["duration_relative_change"] = (
            round(((p_dur - b_dur) / max(0.01, b_dur)) * 100.0, 1) if b_dur > 0 else 0.0
        )

        # 3. Daily frequency change
        b_freq = float(b.get("daily_frequency", 0.0))
        p_freq = float(p.get("daily_frequency", 0.0))
        observed_change["frequency_delta"] = round(p_freq - b_freq, 2)

        # 4. Recurrence score change
        b_rec = float(b.get("recurrence_score", 0.0))
        p_rec = float(p.get("recurrence_score", 0.0))
        observed_change["recurrence_score_delta"] = round(p_rec - b_rec, 2)

        return InterventionOutcomeOut(
            id=outcome_id,
            road_id=outcome_in.road_id,
            intervention_type=outcome_in.intervention_type,
            implementation_date=outcome_in.implementation_date,
            baseline_window_description=outcome_in.baseline_window_description,
            post_window_description=outcome_in.post_window_description,
            baseline_metrics=b,
            post_metrics=p,
            observed_change=observed_change,
            is_causal_claim=False,
            notes=outcome_in.notes,
            recorded_at=recorded_at,
        )
