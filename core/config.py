"""
LaneLogic - Central System Configuration & Thresholds
======================================================
Consolidates all operational constants, thresholds, and evidence weights
to ensure transparent, configurable behavior without magic numbers.
"""

# ============================================================
# EVENT ENGINE THRESHOLDS
# ============================================================

# Vehicle stationary dwell time required before an obstruction event starts (seconds)
DEFAULT_STATIONARY_THRESHOLD_SEC: float = 4.0

# Max tracker disappearance gap tolerated before closing an ongoing event (seconds)
DEFAULT_MAX_DISAPPEARANCE_GAP_SEC: float = 3.0

# Default physical dimensions if road ROI metadata is uncalibrated
DEFAULT_ROAD_WIDTH_M: float = 10.0
DEFAULT_ROAD_LENGTH_M: float = 120.0


# ============================================================
# RECURRENCE & CHRONIC ZONE THRESHOLDS
# ============================================================

# Minimum historical events / windows needed before a road can qualify as chronic
MIN_EVENTS_FOR_CHRONIC: int = 3

# Minimum recurrence score (0.0 - 1.0) required to flag a chronic zone
CHRONIC_RECURRENCE_THRESHOLD: float = 0.40

# Minimum parked-space loss percentage for a window/event to be considered problematic
CHRONIC_MIN_PARKED_SPACE_PCT: float = 5.0

# Number of parked vehicles required in a single window to flag as an obstruction
MIN_PARKED_VEHICLES_FOR_RECURRENCE: int = 1


# ============================================================
# ALERT THRESHOLDS
# ============================================================

# Road-space loss percentage triggering an immediate critical severity alert
ALERT_SEVERE_SPACE_LOSS_PCT: float = 40.0

# Continuous obstruction duration triggering a prolonged obstruction alert (seconds)
ALERT_PROLONGED_DURATION_SEC: float = 180.0

# Cooldown period in seconds to prevent alert flooding on the same road segment
ALERT_COOLDOWN_SECONDS: float = 300.0


# ============================================================
# CAUSE CLASSIFICATION & UNCERTAINTY THRESHOLDS
# ============================================================

# Minimum confidence required for a classification to be labeled "confident"
CONFIDENCE_CONFIDENT_THRESHOLD: float = 0.70

# Minimum confidence required for a classification to be labeled "marginal"
CONFIDENCE_MARGINAL_THRESHOLD: float = 0.45

# Minimum margin between top cause and second cause to be labeled "confident"
CONFIDENCE_DIFF_MARGIN: float = 0.20


# ============================================================
# SEVERITY CLASSIFICATION THRESHOLDS
# ============================================================

SEVERITY_LEVELS = {
    "critical": {"min_loss_pct": 40.0, "min_duration_sec": 120.0},
    "high": {"min_loss_pct": 25.0, "min_duration_sec": 45.0},
    "moderate": {"min_loss_pct": 10.0, "min_duration_sec": 15.0},
    "low": {"min_loss_pct": 3.0, "min_duration_sec": 5.0},
}
