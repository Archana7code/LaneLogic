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

    vehicle_type_breakdown: Dict[str, int]

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