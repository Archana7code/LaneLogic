# """
# LaneLogic - PERSON 3: Backend/API
# ====================================
# schemas.py - Pydantic models used for request bodies and API responses.
# """

# from typing import Optional, List, Dict, Any
# from pydantic import BaseModel


# class RoadCreate(BaseModel):
#     id: str
#     name: str
#     latitude: float
#     longitude: float
#     polygon_geojson: Optional[Dict[str, Any]] = None


# class RoadOut(BaseModel):
#     id: str
#     name: str
#     latitude: float
#     longitude: float
#     polygon_geojson: Optional[Dict[str, Any]] = None
#     current_status: str
#     current_occupancy_pct: float
#     current_dominant_cause: Optional[str] = None
#     is_chronic: bool

#     class Config:
#         from_attributes = True


# class DetectionIn(BaseModel):
#     road_id: str
#     frame_index: int
#     timestamp: float
#     vehicle_id: int
#     vehicle_type: str
#     bbox: List[float]
#     position: List[float]
#     confidence: float
#     movement_state: str


# class DetectionsBulkIn(BaseModel):
#     detections: List[DetectionIn]


# class ObservationIn(BaseModel):
#     road_id: str
#     window_index: int
#     window_start_seconds: float
#     window_end_seconds: float
#     vehicle_count: int
#     occupancy_pct: float
#     blocked_pct: float
#     cause: str
#     cause_explanation: str
#     vehicle_type_breakdown: Dict[str, int]


# class ObservationsBulkIn(BaseModel):
#     observations: List[ObservationIn]


# class ObservationOut(ObservationIn):
#     id: int

#     class Config:
#         from_attributes = True


# class ChronicZoneIn(BaseModel):
#     road_id: str
#     dominant_cause: str
#     occurrence_count: int
#     severity_score: float
#     notes: Optional[str] = None


# class ChronicZoneOut(ChronicZoneIn):
#     id: int

#     class Config:
#         from_attributes = True


# class RecommendationIn(BaseModel):
#     road_id: str
#     cause: str
#     intervention: str
#     expected_benefit_score: float
#     implementation_difficulty_score: float
#     priority_rank: int
#     rationale: str


# class RecommendationOut(RecommendationIn):
#     id: int

#     class Config:
#         from_attributes = True


# class RoadDetailOut(BaseModel):
#     road: RoadOut
#     recent_observations: List[ObservationOut]
#     chronic_zone: Optional[ChronicZoneOut] = None
#     recommendations: List[RecommendationOut]












"""
LaneLogic - PERSON 3: Backend/API
====================================
schemas.py - Pydantic request/response models.
"""

from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field


# ============================================================
# ROAD
# ============================================================

class RoadCreate(BaseModel):

    id: str

    name: str

    # Can remain 0 if actual GPS location is unknown.
    latitude: float = 0.0

    longitude: float = 0.0

    polygon_geojson: Optional[
        Dict[str, Any]
    ] = None


class RoadOut(BaseModel):

    id: str

    name: str

    latitude: float

    longitude: float

    polygon_geojson: Optional[
        Dict[str, Any]
    ] = None

    current_status: str

    current_occupancy_pct: float

    current_parked_space_pct: float

    current_parked_width_meters: float

    current_parked_area_m2: float

    current_dominant_cause: Optional[str] = None

    current_priority_score: int

    current_priority_level: str

    is_chronic: bool

    class Config:
        from_attributes = True


# ============================================================
# PERSON 1 DETECTION
# ============================================================

class DetectionIn(BaseModel):

    road_id: str

    frame_index: int

    timestamp: float

    vehicle_id: int

    vehicle_type: str

    bbox: List[float]

    position: List[float]

    confidence: float

    movement_state: str


class DetectionsBulkIn(BaseModel):

    detections: List[DetectionIn]


# ============================================================
# PERSON 2 OBSERVATION
# ============================================================

class ObservationIn(BaseModel):

    road_id: str

    window_index: int

    window_start_seconds: float

    window_end_seconds: float

    vehicle_count: int

    vehicle_type_breakdown: Dict[str, int] = Field(
        default_factory=dict
    )

    movement_state_breakdown: Dict[str, int] = Field(
        default_factory=dict
    )

    road_length_meters: Optional[float] = None

    road_width_meters: Optional[float] = None

    road_area_m2: Optional[float] = None

    occupancy_pct: float = 0.0

    # Main metric for parking problem.
    parked_space_pct: float = 0.0

    parked_area_m2: float = 0.0

    parked_width_meters: float = 0.0

    # Compatibility with current Person 2.
    blocked_pct: float = 0.0

    blocked_area_m2: float = 0.0

    equivalent_occupied_width_meters: Optional[
        float
    ] = None

    equivalent_blocked_width_meters: Optional[
        float
    ] = None

    severity: str = "normal"

    priority_score: int = 0

    cause: str

    cause_explanation: str


class ObservationsBulkIn(BaseModel):

    observations: List[ObservationIn]


class ObservationOut(ObservationIn):

    id: int

    class Config:
        from_attributes = True


# ============================================================
# PERSON 4 CHRONIC ZONE
# ============================================================

class ChronicZoneIn(BaseModel):

    road_id: str

    dominant_cause: str

    occurrence_count: int

    severity_score: float

    notes: Optional[str] = None


class ChronicZoneOut(ChronicZoneIn):

    id: int

    class Config:
        from_attributes = True


# ============================================================
# PERSON 4 RECOMMENDATION
# ============================================================

class RecommendationIn(BaseModel):

    road_id: str

    cause: str

    intervention: str

    expected_benefit_score: float

    implementation_difficulty_score: float

    priority_rank: int

    rationale: str


class RecommendationOut(
    RecommendationIn
):

    id: int

    class Config:
        from_attributes = True


# ============================================================
# ROAD DETAIL
# ============================================================

class RoadDetailOut(BaseModel):

    road: RoadOut

    recent_observations: List[
        ObservationOut
    ]

    chronic_zone: Optional[
        ChronicZoneOut
    ] = None

    recommendations: List[
        RecommendationOut
    ]


# ============================================================
# CLOSED-LOOP ENHANCEMENT SCHEMAS
# ============================================================

class ObstructionEventIn(BaseModel):
    event_id: str
    road_id: str
    camera_id: Optional[str] = "CAM_01"
    vehicle_id: int
    vehicle_type: str
    start_time: float
    end_time: Optional[float] = None
    duration_sec: float = 0.0
    location: List[float] = Field(default_factory=list)
    bbox: Optional[List[float]] = None
    road_width_m: Optional[float] = None
    occupied_width_m: Optional[float] = None
    road_space_loss_pct: float = 0.0
    recurrence_score: float = 0.0
    cause: str = "unclassified"
    cause_confidence: float = 0.0
    cause_explanation: Optional[str] = None
    severity: str = "normal"
    status: str = "active"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ObstructionEventOut(ObstructionEventIn):
    id: int
    created_at: Any

    class Config:
        from_attributes = True


class ObstructionEventsBulkIn(BaseModel):
    events: List[ObstructionEventIn]


class CausePredictIn(BaseModel):
    road_id: str
    vehicle_type: str
    duration_sec: float
    road_space_loss_pct: float
    timestamp: float = 0.0
    in_waiting_zone: bool = False
    cluster_count: int = 1
    recurrence_score: float = 0.0


class CausePredictOut(BaseModel):
    model_config = {"protected_namespaces": ()}
    cause: str
    confidence: float
    explanation: str
    triggered_rules: List[str]
    feature_contributions: Dict[str, float]
    uncertainty_status: str
    model_type: str = "rule_based"
    model_version: str
    alternative_causes: List[Dict[str, Any]]


class RecommendationGenerateIn(BaseModel):
    road_id: str
    cause: Optional[str] = None
    cause_confidence: Optional[float] = None
    road_space_loss_pct: Optional[float] = None


class RecommendationGenerateOut(BaseModel):
    road_id: str
    recommendations: List[Dict[str, Any]]


class HumanFeedbackIn(BaseModel):
    event_id: Optional[str] = None
    road_id: str
    feedback_type: str
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


class InterventionOutcomeIn(BaseModel):
    road_id: str
    intervention_type: str
    implementation_date: str
    baseline_window_description: str
    post_window_description: str
    baseline_metrics: Dict[str, float]
    post_metrics: Dict[str, float]
    notes: Optional[str] = None


class InterventionOutcomeOut(InterventionOutcomeIn):
    id: int
    observed_change: Dict[str, float]
    is_causal_claim: bool = False
    recorded_at: Any

    class Config:
        from_attributes = True


class SimulationRequest(BaseModel):
    road_id: str
    intervention_type: str
    parameters: Dict[str, Any] = Field(default_factory=dict)


class SimulationResponse(BaseModel):
    road_id: str
    intervention_type: str
    simulated: bool = True
    data_source: str = "historical"
    baseline_loss_pct: float
    simulated_loss_pct: float
    simulated_recovery_pct: float
    baseline_avg_duration_sec: float
    simulated_avg_duration_sec: float
    confidence_score: float
    feasibility_score: float
    disruption_score: float
    disclaimer: str


class AlertOut(BaseModel):
    id: int
    alert_type: str
    severity: str
    road_id: str
    event_id: Optional[str] = None
    message: str
    status: str
    created_at: Any
    acknowledged_at: Optional[Any] = None
    acknowledged_by: Optional[str] = None

    class Config:
        from_attributes = True


class AlertAcknowledgeIn(BaseModel):
    acknowledged_by: str = "traffic_operator"