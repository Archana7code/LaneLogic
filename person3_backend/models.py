# """
# LaneLogic - PERSON 3: Backend/API
# ====================================
# models.py - SQLAlchemy ORM table definitions.

# Tables:
#   - VehicleDetection : raw per-frame detections from Person 1
#   - RoadWindowObservation : per-time-window occupancy/cause from Person 2
#   - Road : one row per monitored road (static metadata + latest live status)
#   - ChronicZone : roads flagged as recurring problem zones by Person 4
#   - Recommendation : intervention suggestions from Person 4
# """

# from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON
# from sqlalchemy.orm import relationship
# from sqlalchemy.sql import func

# from database import Base


# class Road(Base):
#     __tablename__ = "roads"

#     id = Column(String, primary_key=True)          # e.g. "ROAD_001"
#     name = Column(String, nullable=False)
#     latitude = Column(Float, nullable=False)
#     longitude = Column(Float, nullable=False)
#     polygon_geojson = Column(JSON, nullable=True)   # optional road-shape polygon for the map

#     # Denormalized "current status" fields, refreshed as new analysis comes in,
#     # so the dashboard/map can read a single row instead of aggregating live.
#     current_status = Column(String, default="normal")     # normal | moderate | severe
#     current_occupancy_pct = Column(Float, default=0.0)
#     current_dominant_cause = Column(String, nullable=True)
#     is_chronic = Column(Integer, default=0)  # 0/1 boolean flag, kept in sync with ChronicZone

#     detections = relationship("VehicleDetection", back_populates="road")
#     observations = relationship("RoadWindowObservation", back_populates="road")


# class VehicleDetection(Base):
#     __tablename__ = "vehicle_detections"

#     id = Column(Integer, primary_key=True, autoincrement=True)
#     road_id = Column(String, ForeignKey("roads.id"), index=True)
#     frame_index = Column(Integer)
#     timestamp = Column(Float)
#     vehicle_id = Column(Integer, index=True)
#     vehicle_type = Column(String)
#     bbox = Column(JSON)
#     position = Column(JSON)
#     confidence = Column(Float)
#     movement_state = Column(String)
#     created_at = Column(DateTime, server_default=func.now())

#     road = relationship("Road", back_populates="detections")


# class RoadWindowObservation(Base):
#     __tablename__ = "road_window_observations"

#     id = Column(Integer, primary_key=True, autoincrement=True)
#     road_id = Column(String, ForeignKey("roads.id"), index=True)
#     window_index = Column(Integer)
#     window_start_seconds = Column(Float)
#     window_end_seconds = Column(Float)
#     vehicle_count = Column(Integer)
#     occupancy_pct = Column(Float)
#     blocked_pct = Column(Float)
#     cause = Column(String)
#     cause_explanation = Column(String)
#     vehicle_type_breakdown = Column(JSON)
#     observed_at = Column(DateTime, server_default=func.now())

#     road = relationship("Road", back_populates="observations")


# class ChronicZone(Base):
#     __tablename__ = "chronic_zones"

#     id = Column(Integer, primary_key=True, autoincrement=True)
#     road_id = Column(String, ForeignKey("roads.id"), index=True)
#     dominant_cause = Column(String)
#     occurrence_count = Column(Integer)
#     severity_score = Column(Float)     # 0-100, rule-based, see Person 4
#     first_flagged_at = Column(DateTime, server_default=func.now())
#     last_updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
#     notes = Column(String, nullable=True)


# class Recommendation(Base):
#     __tablename__ = "recommendations"

#     id = Column(Integer, primary_key=True, autoincrement=True)
#     road_id = Column(String, ForeignKey("roads.id"), index=True)
#     cause = Column(String)
#     intervention = Column(String)
#     expected_benefit_score = Column(Float)      # 0-100, rule-based estimate
#     implementation_difficulty_score = Column(Float)  # 0-100, higher = harder
#     priority_rank = Column(Integer)
#     rationale = Column(String)
#     created_at = Column(DateTime, server_default=func.now())






"""
LaneLogic - PERSON 3: Backend/API
====================================
models.py - SQLAlchemy ORM table definitions.

Tables:
    Road
    VehicleDetection
    RoadWindowObservation
    ChronicZone
    Recommendation
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    ForeignKey,
    JSON
)

from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database import Base


# ============================================================
# ROAD
# ============================================================

class Road(Base):
    __tablename__ = "roads"

    id = Column(
        String,
        primary_key=True
    )

    name = Column(
        String,
        nullable=False
    )

    latitude = Column(
        Float,
        nullable=False,
        default=0.0
    )

    longitude = Column(
        Float,
        nullable=False,
        default=0.0
    )

    polygon_geojson = Column(
        JSON,
        nullable=True
    )

    # --------------------------------------------------------
    # Current road status
    # --------------------------------------------------------

    current_status = Column(
        String,
        default="normal"
    )

    current_occupancy_pct = Column(
        Float,
        default=0.0
    )

    # IMPORTANT:
    # This is parked-vehicle space, not traffic-light queue.
    current_parked_space_pct = Column(
        Float,
        default=0.0
    )

    current_parked_width_meters = Column(
        Float,
        default=0.0
    )

    current_parked_area_m2 = Column(
        Float,
        default=0.0
    )

    current_dominant_cause = Column(
        String,
        nullable=True
    )

    current_priority_score = Column(
        Integer,
        default=0
    )

    current_priority_level = Column(
        String,
        default="normal"
    )

    is_chronic = Column(
        Integer,
        default=0
    )

    # --------------------------------------------------------
    # Relationships
    # --------------------------------------------------------

    detections = relationship(
        "VehicleDetection",
        back_populates="road"
    )

    observations = relationship(
        "RoadWindowObservation",
        back_populates="road"
    )


# ============================================================
# PERSON 1 RAW VEHICLE DETECTIONS
# ============================================================

class VehicleDetection(Base):
    __tablename__ = "vehicle_detections"

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    road_id = Column(
        String,
        ForeignKey("roads.id"),
        index=True
    )

    frame_index = Column(Integer)

    timestamp = Column(Float)

    vehicle_id = Column(
        Integer,
        index=True
    )

    vehicle_type = Column(String)

    bbox = Column(JSON)

    position = Column(JSON)

    confidence = Column(Float)

    movement_state = Column(String)

    created_at = Column(
        DateTime,
        server_default=func.now()
    )

    road = relationship(
        "Road",
        back_populates="detections"
    )


# ============================================================
# PERSON 2 ANALYSIS
# ============================================================

class RoadWindowObservation(Base):
    __tablename__ = "road_window_observations"

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    road_id = Column(
        String,
        ForeignKey("roads.id"),
        index=True
    )

    window_index = Column(Integer)

    window_start_seconds = Column(Float)

    window_end_seconds = Column(Float)

    # --------------------------------------------------------
    # Vehicle information
    # --------------------------------------------------------

    vehicle_count = Column(Integer)

    vehicle_type_breakdown = Column(
        JSON
    )

    movement_state_breakdown = Column(
        JSON,
        nullable=True
    )

    # --------------------------------------------------------
    # Road-space information
    # --------------------------------------------------------

    road_length_meters = Column(
        Float,
        nullable=True
    )

    road_width_meters = Column(
        Float,
        nullable=True
    )

    road_area_m2 = Column(
        Float,
        nullable=True
    )

    occupancy_pct = Column(
        Float,
        default=0.0
    )

    # IMPORTANT:
    # For LaneLogic this represents PARKED vehicle space.
    parked_space_pct = Column(
        Float,
        default=0.0
    )

    parked_area_m2 = Column(
        Float,
        default=0.0
    )

    parked_width_meters = Column(
        Float,
        default=0.0
    )

    # Kept for compatibility with Person 2.
    blocked_pct = Column(
        Float,
        default=0.0
    )

    blocked_area_m2 = Column(
        Float,
        default=0.0
    )

    equivalent_occupied_width_meters = Column(
        Float,
        nullable=True
    )

    equivalent_blocked_width_meters = Column(
        Float,
        nullable=True
    )

    # --------------------------------------------------------
    # Priority
    # --------------------------------------------------------

    severity = Column(
        String,
        default="normal"
    )

    priority_score = Column(
        Integer,
        default=0
    )

    # --------------------------------------------------------
    # Cause
    # --------------------------------------------------------

    cause = Column(String)

    cause_explanation = Column(String)

    observed_at = Column(
        DateTime,
        server_default=func.now()
    )

    road = relationship(
        "Road",
        back_populates="observations"
    )


# ============================================================
# PERSON 4 CHRONIC ZONE
# ============================================================

class ChronicZone(Base):
    __tablename__ = "chronic_zones"

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    road_id = Column(
        String,
        ForeignKey("roads.id"),
        index=True
    )

    dominant_cause = Column(String)

    occurrence_count = Column(Integer)

    severity_score = Column(Float)

    first_flagged_at = Column(
        DateTime,
        server_default=func.now()
    )

    last_updated_at = Column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now()
    )

    notes = Column(
        String,
        nullable=True
    )


# ============================================================
# PERSON 4 RECOMMENDATIONS
# ============================================================

class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    road_id = Column(
        String,
        ForeignKey("roads.id"),
        index=True
    )

    cause = Column(String)

    intervention = Column(String)

    expected_benefit_score = Column(
        Float
    )

    implementation_difficulty_score = Column(
        Float
    )

    priority_rank = Column(Integer)

    rationale = Column(String)

    created_at = Column(
        DateTime,
        server_default=func.now()
    )