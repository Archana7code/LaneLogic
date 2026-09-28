"""
LaneLogic - Intervention Knowledge Base & Recommendation Decision Engine
========================================================================
Maps diagnosed causes to applicable traffic management interventions.
Evaluates candidate actions using transparent multi-criteria scoring:
expected road-space recovery, feasibility, public disruption, and evidence strength.
"""

from typing import Dict, List, Optional, Any
from core.contracts import InterventionRecommendation


# ============================================================
# INTERVENTION KNOWLEDGE BASE CATALOG
# ============================================================

INTERVENTION_CATALOG: Dict[str, Dict[str, Any]] = {
    "INT_LOADING_BAY": {
        "title": "Create a designated recessed loading/unloading bay",
        "causes": ["loading_unloading"],
        "recovery_factor": 0.80,  # Recovers ~80% of lost curb lane space
        "feasibility": 55.0,     # Medium infrastructure effort
        "disruption": 35.0,      # Moderate construction disruption
        "description": "Construct a dedicated physical loading bay to pull commercial delivery vehicles out of through-traffic lanes.",
    },
    "INT_LOADING_TIME_WINDOW": {
        "title": "Enforce strict commercial loading time-window restrictions (off-peak only)",
        "causes": ["loading_unloading"],
        "recovery_factor": 0.70,
        "feasibility": 85.0,     # High feasibility (regulatory/signage)
        "disruption": 15.0,      # Low disruption
        "description": "Restrict freight delivery and loading activity to 22:00-07:00 and 13:00-15:00 off-peak windows via municipal ordinance.",
    },
    "INT_PARKING_ENFORCEMENT": {
        "title": "Deploy targeted smart parking enforcement & clear no-stopping signage",
        "causes": ["illegal_parking"],
        "recovery_factor": 0.75,
        "feasibility": 80.0,
        "disruption": 10.0,
        "description": "Install high-visibility regulatory signage backed by targeted camera/warden enforcement during peak obstruction hours.",
    },
    "INT_PARKING_BAY_CREATION": {
        "title": "Formalize off-street or demarcated parallel parking zone",
        "causes": ["illegal_parking"],
        "recovery_factor": 0.85,
        "feasibility": 50.0,
        "disruption": 40.0,
        "description": "Reconfigure roadside curb geometry to establish designated parking stalls without encroaching on active travel lanes.",
    },
    "INT_SCHOOL_STAGGER": {
        "title": "Stagger school start/dismissal bells & establish managed drop-off queue",
        "causes": ["school_dropoff", "school_drop_off"],
        "recovery_factor": 0.65,
        "feasibility": 75.0,
        "disruption": 20.0,
        "description": "Partner with local school administration to stagger class release times by 20 minutes to eliminate peak arrival congestion.",
    },
    "INT_SCHOOL_PUDO_ZONE": {
        "title": "Establish dedicated pick-up/drop-off (PUDO) loop with traffic marshal",
        "causes": ["school_dropoff", "school_drop_off"],
        "recovery_factor": 0.85,
        "feasibility": 60.0,
        "disruption": 25.0,
        "description": "Convert roadside shoulder into an organized kiss-and-ride lane with 60-second dwell time limits and school marshals.",
    },
    "INT_AUTO_STAND_FORMALIZATION": {
        "title": "Designate formal auto-rickshaw staging stand with queuing lane",
        "causes": ["informal_auto_stand"],
        "recovery_factor": 0.80,
        "feasibility": 65.0,
        "disruption": 25.0,
        "description": "Formalize 4-vehicle capacity auto stand 30m away from junction conflict point to prevent intersection blockage.",
    },
    "INT_SIGNAL_TIMING_OPTIMIZATION": {
        "title": "Adjust signal green-phase splits and offset timing for queue clearance",
        "causes": ["traffic_signal_queue"],
        "recovery_factor": 0.70,
        "feasibility": 90.0,
        "disruption": 5.0,
        "description": "Recalibrate traffic signal timing plan based on measured peak queue lengths to clear approach queues in single cycles.",
    },
    "INT_CONSTRUCTION_PERMIT_MANAGEMENT": {
        "title": "Enforce work-zone traffic management plan & material storage set-back",
        "causes": ["construction_obstruction"],
        "recovery_factor": 0.90,
        "feasibility": 70.0,
        "disruption": 30.0,
        "description": "Require construction contractors to relocate materials behind barricades and maintain minimum usable roadway width.",
    },
    "INT_CURB_MANAGEMENT_STUDY": {
        "title": "Conduct detailed curb-space allocation audit before structural changes",
        "causes": ["unclassified", "general_congestion", "temporary_stopping"],
        "recovery_factor": 0.40,
        "feasibility": 90.0,
        "disruption": 5.0,
        "description": "Gather multi-day granular curb utilization data to classify obstruction causes before deploying permanent capital works.",
    },
}


class RecommendationDecisionEngine:
    """
    Translates diagnosis into ranked, explainable, authority-facing recommendations.
    Every recommendation is traceable:
    Problem -> Evidence -> Cause -> Candidates -> Multi-Criteria Ranking -> Recommended Action.
    """

    def generate_recommendations(
        self,
        road_id: str,
        cause: str,
        cause_confidence: float,
        road_space_loss_pct: float,
        recurrence_score: float = 0.5,
        evidence_summary: str = "",
    ) -> List[InterventionRecommendation]:
        """
        Generate, evaluate, and rank candidate interventions for a detected problem.
        """
        # Match candidate interventions from knowledge base
        matched_interventions = []
        for int_id, int_meta in INTERVENTION_CATALOG.items():
            if cause in int_meta["causes"]:
                matched_interventions.append((int_id, int_meta))

        # Fallback to general curb study if cause has no direct match
        if not matched_interventions:
            matched_interventions.append(("INT_CURB_MANAGEMENT_STUDY", INTERVENTION_CATALOG["INT_CURB_MANAGEMENT_STUDY"]))

        evaluated: List[Dict[str, Any]] = []

        for int_id, meta in matched_interventions:
            rec_factor = meta["recovery_factor"]
            feasibility = meta["feasibility"]
            disruption = meta["disruption"]

            # Expected recovery: fraction of lost road space that this intervention can reclaim
            estimated_recovery_pct = round(min(100.0, road_space_loss_pct * rec_factor), 1)

            # Benefit score (0-100): combines expected recovery with cause confidence and recurrence
            raw_benefit = (estimated_recovery_pct / max(1.0, road_space_loss_pct)) * 100.0
            expected_benefit_score = round(min(100.0, raw_benefit * cause_confidence * (0.5 + 0.5 * recurrence_score)), 1)
            implementation_difficulty_score = round(100.0 - feasibility, 1)

            # Transparent ranking formula:
            # Score = 0.50 * Expected Benefit + 0.30 * Feasibility - 0.20 * Disruption
            composite_score = (
                0.50 * expected_benefit_score
                + 0.30 * feasibility
                - 0.20 * disruption
            )

            ranking_factors = {
                "expected_recovery_pct": estimated_recovery_pct,
                "expected_benefit_score": expected_benefit_score,
                "feasibility_score": feasibility,
                "disruption_score": disruption,
                "cause_confidence": cause_confidence,
                "composite_score": round(composite_score, 2),
            }

            rationale = (
                f"Diagnosed cause '{cause}' (confidence {cause_confidence * 100:.0f}%) is responsible for "
                f"{road_space_loss_pct:.1f}% usable road width loss. '{meta['title']}' offers an estimated "
                f"{estimated_recovery_pct:.1f}% recovery with {feasibility:.0f}/100 feasibility and "
                f"{disruption:.0f}/100 disruption score. {evidence_summary}"
            )

            evaluated.append({
                "road_id": road_id,
                "cause": cause,
                "intervention": meta["title"],
                "expected_benefit_score": expected_benefit_score,
                "implementation_difficulty_score": implementation_difficulty_score,
                "disruption_score": disruption,
                "ranking_factors": ranking_factors,
                "estimated_road_space_recovery_pct": estimated_recovery_pct,
                "rationale": rationale,
                "evidence_basis": evidence_summary or f"Observed {road_space_loss_pct:.1f}% road-space loss.",
                "is_estimated": True,
                "_composite_score": composite_score,
            })

        # Rank by composite score descending
        evaluated.sort(key=lambda item: item["_composite_score"], reverse=True)

        recommendations: List[InterventionRecommendation] = []
        for rank, item in enumerate(evaluated, start=1):
            item.pop("_composite_score", None)
            item["priority_rank"] = rank
            recommendations.append(InterventionRecommendation(**item))

        return recommendations
