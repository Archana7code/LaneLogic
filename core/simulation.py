"""
LaneLogic - Intervention Scenario Simulation Engine
====================================================
Simulates expected impact of hypothetical interventions (e.g. loading zone,
parking restrictions, signal optimization) using historical pattern baselines
and empirical intervention knowledge factors.
Clearly labels projections as simulated/predicted.
"""

from typing import Dict, Any, Optional
from core.contracts import SimulationRequest, SimulationResponse
from core.interventions import INTERVENTION_CATALOG


class InterventionSimulationEngine:
    """
    Evaluates what-if policy scenarios for road authorities.
    """

    def simulate(
        self,
        request: SimulationRequest,
        baseline_loss_pct: float = 18.0,
        baseline_avg_duration_sec: float = 47.0,
        historical_recurrence: float = 0.65,
    ) -> SimulationResponse:
        int_type = request.intervention_type

        # Look up intervention catalog metadata or match substring
        matched_meta = None
        for key, meta in INTERVENTION_CATALOG.items():
            if key.lower() in int_type.lower() or meta["title"].lower() in int_type.lower():
                matched_meta = meta
                break

        if not matched_meta:
            matched_meta = INTERVENTION_CATALOG.get("INT_CURB_MANAGEMENT_STUDY")

        rec_factor = matched_meta.get("recovery_factor", 0.50)
        feasibility = matched_meta.get("feasibility", 70.0)
        disruption = matched_meta.get("disruption", 20.0)

        # Apply parameters override if specified in request
        if "compliance_rate" in request.parameters:
            compliance = float(request.parameters["compliance_rate"])  # e.g. 0.8
            rec_factor = rec_factor * compliance

        # Compute simulated recovery
        simulated_recovery_pct = round(baseline_loss_pct * rec_factor, 1)
        simulated_loss_pct = round(max(0.0, baseline_loss_pct - simulated_recovery_pct), 1)

        # Simulated duration reduction
        duration_factor = min(0.9, rec_factor * 1.1)
        simulated_duration = round(max(5.0, baseline_avg_duration_sec * (1.0 - duration_factor)), 1)

        # Confidence in simulation is higher when historical recurrence and evidence exist
        confidence_score = round(min(0.90, 0.40 + 0.40 * historical_recurrence), 2)

        return SimulationResponse(
            road_id=request.road_id,
            intervention_type=matched_meta["title"],
            simulated=True,
            baseline_loss_pct=baseline_loss_pct,
            simulated_loss_pct=simulated_loss_pct,
            simulated_recovery_pct=simulated_recovery_pct,
            baseline_avg_duration_sec=baseline_avg_duration_sec,
            simulated_avg_duration_sec=simulated_duration,
            confidence_score=confidence_score,
            feasibility_score=feasibility,
            disruption_score=disruption,
            disclaimer=(
                "SIMULATED SCENARIO: Projection based on empirical intervention knowledge base "
                "and baseline road metrics. Realized outcome may vary depending on local compliance and enforcement."
            ),
        )
