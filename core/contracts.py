"""
LaneLogic - Core Common Data Contracts
========================================
Canonical Pydantic models for the closed-loop system shared across detection,
analysis, backend, recurrence, recommendations, feedback, and simulation.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# ============================================================
# CANONICAL OBSTRUCTION EVENT
# ============================================================

class ObstructionEvent(BaseModel):
    """
    Canonical time-bounded obstruction event representing continuous,
    meaningful loss of usable road space rather than frame-level detections.
    """
    event_id: str = Field(description="Unique stable event identifier")
    road_id: str = Field(description="Identifier of the monitored road")
    camera_id: Optional[str] = Field(default="CAM_01", description="Identifier of the recording camera")
    vehicle_id: int = Field(description="Persistent tracker vehicle ID")
    vehicle_type: str = Field(description="Vehicle classification (car, truck, bus, etc.)")
    start_time: float = Field(description="Event start timestamp in video seconds or epoch")
    end_time: Optional[float] = Field(default=None, description="Event end timestamp (None if ongoing)")
    duration_sec: float = Field(default=0.0, description="Total continuous stationary duration in seconds")
    location: List[float] = Field(default_factory=list, description="Coordinates [x, y] in image or [lat, lng]")
    bbox: Optional[List[float]] = Field(default=None, description="Bounding box [x1, y1, x2, y2]")
    road_width_m: Optional[float] = Field(default=None, description="Configured usable road width in meters")
    occupied_width_m: Optional[float] = Field(default=None, description="Estimated occupied road width in meters")
    road_space_loss_pct: float = Field(default=0.0, description="Percentage of usable road space blocked (0-100)")
    recurrence_score: float = Field(default=0.0, description="Recurrence score (0.0 to 1.0)")
    cause: str = Field(default="unclassified", description="Likely cause classification")
    cause_confidence: float = Field(default=0.0, description="Confidence in cause classification (0.0 to 1.0)")
    cause_explanation: Optional[str] = Field(default=None, description="Human-readable explanation of the cause")
    severity: str = Field(default="normal", description="Severity classification (normal, low, moderate, high, critical)")
    status: str = Field(default="active", description="Event lifecycle state: active, ended, confirmed")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional context or evidence attributes")

    class Config:
        from_attributes = True


class ObstructionEventBulkIn(BaseModel):
    events: List[ObstructionEvent]


# ============================================================
# CAUSE & EXPLAINABILITY CONTRACTS
# ============================================================

class CausePrediction(BaseModel):
    """Explainable cause prediction with confidence and evidence breakdown."""
    model_config = {"protected_namespaces": ()}

    cause: str
    confidence: float = Field(ge=0.0, le=1.0)
    explanation: str
    triggered_rules: List[str] = Field(default_factory=list)
    feature_contributions: Dict[str, float] = Field(default_factory=dict)
    uncertainty_status: str = Field(default="confident")  # "confident", "marginal", "uncertain_continue_monitoring"
    model_type: str = Field(default="rule_based")  # "rule_based" or "supervised_ml" (never fabricated)
    model_version: str = Field(default="rule_engine_v2.2")
    alternative_causes: List[Dict[str, Any]] = Field(default_factory=list)


# ============================================================
# HISTORICAL PATTERN CONTRACTS
# ============================================================

class HistoricalPattern(BaseModel):
    """Aggregated historical obstruction pattern for a road segment."""
    road_id: str
    observation_period_days: int = 1
    total_events: int = 0
    total_duration_sec: float = 0.0
    average_duration_sec: float = 0.0
    average_road_space_loss_pct: float = 0.0
    frequency_per_day: float = 0.0
    peak_hours: List[int] = Field(default_factory=list)
    temporal_consistency: float = Field(default=0.0, ge=0.0, le=1.0)
    spatial_consistency: float = Field(default=0.0, ge=0.0, le=1.0)
    recurrence_score: float = Field(default=0.0, ge=0.0, le=1.0)
    is_chronic: bool = False
    single_event_severity: bool = False  # Explicit distinction between isolated severe stop vs chronic pattern
    dominant_cause: str = "normal"
    severity: str = "normal"
    evidence_summary: str = ""


# ============================================================
# INTERVENTION & RECOMMENDATION CONTRACTS
# ============================================================

class InterventionRecommendation(BaseModel):
    """Ranked and explainable intervention recommendation."""
    id: Optional[int] = None
    road_id: str
    cause: str
    intervention: str
    expected_benefit_score: float = Field(description="Estimated benefit score (0-100)")
    implementation_difficulty_score: float = Field(description="Difficulty/cost score (0-100)")
    disruption_score: float = Field(default=20.0, description="Public disruption during implementation (0-100)")
    priority_rank: int = 1
    rationale: str
    ranking_factors: Dict[str, float] = Field(default_factory=dict)
    estimated_road_space_recovery_pct: float = 0.0
    evidence_basis: str = ""
    is_estimated: bool = True

    class Config:
        from_attributes = True


# ============================================================
# HUMAN FEEDBACK CONTRACTS
# ============================================================

class HumanFeedbackIn(BaseModel):
    event_id: Optional[str] = None
    road_id: str
    feedback_type: str = Field(description="cause_confirmation, cause_correction, recommendation_acceptance, recommendation_rejection, general_note")
    original_value: Optional[str] = None
    corrected_value: Optional[str] = None
    accepted: Optional[bool] = None
    notes: Optional[str] = None
    authority_user: Optional[str] = "traffic_engineer"


class HumanFeedbackOut(HumanFeedbackIn):
    id: int
    created_at: Any

    class Config:
        from_attributes = True


# ============================================================
# INTERVENTION OUTCOME TRACKING CONTRACTS
# ============================================================

class InterventionOutcomeIn(BaseModel):
    road_id: str
    intervention_type: str
    implementation_date: str = Field(description="ISO Date or string timestamp of implementation")
    baseline_window_description: str = Field(description="e.g. 7 days pre-intervention")
    post_window_description: str = Field(description="e.g. 7 days post-intervention")
    baseline_metrics: Dict[str, float] = Field(description="Keys: avg_duration_sec, avg_loss_pct, daily_frequency, recurrence_score")
    post_metrics: Dict[str, float] = Field(description="Keys: avg_duration_sec, avg_loss_pct, daily_frequency, recurrence_score")
    notes: Optional[str] = None


class InterventionOutcomeOut(InterventionOutcomeIn):
    id: int
    observed_change: Dict[str, float] = Field(description="Absolute and percentage changes observed")
    is_causal_claim: bool = False  # Always explicitly marked as observed association, not proven causality
    recorded_at: Any

    class Config:
        from_attributes = True


# ============================================================
# INTERVENTION SIMULATION CONTRACTS
# ============================================================

class SimulationRequest(BaseModel):
    road_id: str
    intervention_type: str
    parameters: Dict[str, Any] = Field(default_factory=dict)


class SimulationResponse(BaseModel):
    road_id: str
    intervention_type: str
    simulated: bool = True  # Explicit flag that this is simulated/predicted
    data_source: str = "historical"  # "historical" or "demo_default"
    baseline_loss_pct: float
    simulated_loss_pct: float
    simulated_recovery_pct: float
    baseline_avg_duration_sec: float
    simulated_avg_duration_sec: float
    confidence_score: float
    feasibility_score: float
    disruption_score: float
    disclaimer: str = "Simulated scenario projection based on historical patterns and empirical knowledge base. Not a guaranteed outcome."


# ============================================================
# ALERT CONTRACTS
# ============================================================

class AlertOut(BaseModel):
    id: int
    alert_type: str
    severity: str
    road_id: str
    event_id: Optional[str] = None
    message: str
    status: str  # active, acknowledged, resolved
    created_at: Any
    acknowledged_at: Optional[Any] = None
    acknowledged_by: Optional[str] = None

    class Config:
        from_attributes = True
