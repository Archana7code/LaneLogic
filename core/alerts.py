"""
LaneLogic - Alerting Engine
============================
Generates operational alerts for severe obstructions, prolonged stops,
and chronic problem zone triggers. Implements deduplication and cooldown
mechanisms to prevent alert flooding.
"""

from typing import Dict, List, Optional, Any
import time

from core.config import (
    ALERT_SEVERE_SPACE_LOSS_PCT,
    ALERT_PROLONGED_DURATION_SEC,
    ALERT_COOLDOWN_SECONDS,
)


class AlertEngine:
    """
    Manages operational alert evaluation with deduplication and cooldown per road/event.
    Thresholds are fully configurable to avoid hardcoded magic numbers.
    """

    DEFAULT_SEVERE_SPACE_LOSS_PCT: float = ALERT_SEVERE_SPACE_LOSS_PCT
    DEFAULT_PROLONGED_DURATION_SEC: float = ALERT_PROLONGED_DURATION_SEC
    DEFAULT_COOLDOWN_SECONDS: float = ALERT_COOLDOWN_SECONDS

    def __init__(
        self,
        cooldown_seconds: float = DEFAULT_COOLDOWN_SECONDS,
        severe_space_loss_pct: float = DEFAULT_SEVERE_SPACE_LOSS_PCT,
        prolonged_duration_sec: float = DEFAULT_PROLONGED_DURATION_SEC,
    ):
        self.cooldown_seconds = cooldown_seconds
        self.severe_space_loss_pct = severe_space_loss_pct
        self.prolonged_duration_sec = prolonged_duration_sec
        # key: (road_id, alert_type) -> last_alert_time
        self.recent_alerts: Dict[str, float] = {}

    def should_alert(self, road_id: str, alert_type: str, current_time: float) -> bool:
        key = f"{road_id}:{alert_type}"
        last_time = self.recent_alerts.get(key)
        if last_time is not None and (current_time - last_time) < self.cooldown_seconds:
            return False
        self.recent_alerts[key] = current_time
        return True

    def check_obstruction_alert(
        self,
        road_id: str,
        event_id: str,
        duration_sec: float,
        road_space_loss_pct: float,
        severity: str,
        current_time: Optional[float] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Evaluates an obstruction event against configurable alert conditions.
        """
        now = current_time if current_time is not None else time.time()

        # Select single highest-priority alert condition for the event
        if road_space_loss_pct >= self.severe_space_loss_pct:
            alert_type = "SEVERE_SPACE_LOSS"
            severity_val = "critical"
            msg = f"Critical road-space loss of {road_space_loss_pct:.1f}% detected on {road_id}."
        elif duration_sec >= self.prolonged_duration_sec:
            alert_type = "PROLONGED_OBSTRUCTION"
            severity_val = "high"
            msg = f"Vehicle stationary for {duration_sec / 60:.1f} minutes on {road_id}."
        elif severity in ("high", "critical"):
            alert_type = "HIGH_SEVERITY_OBSTRUCTION"
            severity_val = severity
            msg = f"{severity.upper()} severity obstruction active on {road_id}."
        else:
            return None

        if self.should_alert(road_id, alert_type, now):
            return {
                "alert_type": alert_type,
                "severity": severity_val,
                "road_id": road_id,
                "event_id": event_id,
                "message": msg,
                "status": "active",
            }

        return None
