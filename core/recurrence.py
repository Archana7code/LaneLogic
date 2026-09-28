"""
LaneLogic - Historical Recurrence Engine
=========================================
Aggregates time-bounded obstruction events and window observations to compute
temporal consistency, spatial clustering, frequency, and transparent recurrence scores.
Flags Chronic Problem Zones with full evidence traceability.
"""

from typing import List, Dict, Any, Optional
from collections import Counter, defaultdict
import math

from core.contracts import ObstructionEvent, HistoricalPattern
from core.config import (
    MIN_EVENTS_FOR_CHRONIC,
    CHRONIC_RECURRENCE_THRESHOLD,
    CHRONIC_MIN_PARKED_SPACE_PCT,
)


class HistoricalRecurrenceEngine:
    """
    Transparent statistical recurrence analysis engine.
    Avoids arbitrary black-box scoring by relying on documented frequency,
    temporal concentration (hour clustering), and spatial consistency.
    """

    def __init__(
        self,
        min_events_for_chronic: int = MIN_EVENTS_FOR_CHRONIC,
        chronic_recurrence_threshold: float = CHRONIC_RECURRENCE_THRESHOLD,
    ):
        self.min_events_for_chronic = min_events_for_chronic
        self.chronic_recurrence_threshold = chronic_recurrence_threshold

    def analyze_events(
        self,
        road_id: str,
        events: List[ObstructionEvent],
        observation_period_days: int = 1,
    ) -> HistoricalPattern:
        """
        Analyze a collection of obstruction events for a given road.
        """
        if not events:
            return HistoricalPattern(
                road_id=road_id,
                observation_period_days=observation_period_days,
                total_events=0,
                evidence_summary="Insufficient historical observations to evaluate recurrence.",
                is_chronic=False,
                severity="normal",
            )

        total_events = len(events)
        durations = [e.duration_sec for e in events]
        losses = [e.road_space_loss_pct for e in events]
        causes = [e.cause for e in events if e.cause not in ("normal", "unclassified")]

        total_duration = sum(durations)
        avg_duration = total_duration / total_events
        avg_loss = sum(losses) / total_events if losses else 0.0

        frequency_per_day = total_events / max(1, observation_period_days)

        # ----------------------------------------------------
        # Temporal consistency: concentration into peak hours
        # ----------------------------------------------------
        # Extract hour from start_time (assuming epoch or seconds of day)
        hours = []
        for e in events:
            h = int(e.start_time // 3600) % 24
            hours.append(h)

        hour_counts = Counter(hours)
        peak_hours = [h for h, _ in hour_counts.most_common(3)]

        # Peak concentration ratio (fraction of events occurring in top 2 peak hours)
        top2_count = sum(c for _, c in hour_counts.most_common(2))
        temporal_consistency = round(top2_count / total_events, 2) if total_events > 0 else 0.0

        # ----------------------------------------------------
        # Spatial consistency: clustering of obstruction locations
        # ----------------------------------------------------
        locations = [e.location for e in events if e.location and len(e.location) >= 2]
        if len(locations) >= 2:
            xs = [loc[0] for loc in locations]
            ys = [loc[1] for loc in locations]
            std_x = math.sqrt(sum((x - sum(xs) / len(xs)) ** 2 for x in xs) / len(xs))
            std_y = math.sqrt(sum((y - sum(ys) / len(ys)) ** 2 for y in ys) / len(ys))
            spread = math.sqrt(std_x ** 2 + std_y ** 2)
            # Tighter spread = higher spatial consistency (normalized over typical 500px spread)
            spatial_consistency = round(max(0.0, min(1.0, 1.0 - (spread / 500.0))), 2)
        else:
            spatial_consistency = 0.50 if locations else 0.0

        # ----------------------------------------------------
        # Recurrence Score (0.0 to 1.0):
        # 45% event frequency, 35% temporal consistency, 20% spatial consistency
        # ----------------------------------------------------
        freq_factor = min(1.0, frequency_per_day / 4.0)
        recurrence_score = round(
            0.45 * freq_factor + 0.35 * temporal_consistency + 0.20 * spatial_consistency,
            2
        )

        # Explicit separation: single long event severity vs recurring chronic pattern
        single_event_severity = (
            total_events < self.min_events_for_chronic
            and (avg_duration >= 60.0 or avg_loss >= 30.0)
        )

        # True chronic pattern requires empirical recurrence evidence
        is_chronic = (
            total_events >= self.min_events_for_chronic
            and recurrence_score >= self.chronic_recurrence_threshold
        )

        dominant_cause = Counter(causes).most_common(1)[0][0] if causes else "illegal_parking"

        # Severity classification incorporates both chronic recurrence and single-event severity
        if (is_chronic or single_event_severity) and (avg_loss >= 25.0 or avg_duration >= 60.0):
            severity = "critical"
        elif is_chronic or single_event_severity or avg_loss >= 15.0:
            severity = "high"
        elif avg_loss >= 5.0 or total_events >= 2:
            severity = "moderate"
        else:
            severity = "low"

        peak_str = ", ".join(f"{h:02d}:00" for h in peak_hours) if peak_hours else "varied"
        if single_event_severity:
            evidence_summary = (
                f"Isolated severe obstruction detected on {road_id} ({total_events} event, duration: {avg_duration:.1f}s, "
                f"loss: {avg_loss:.1f}%). Classified as severe/prolonged stop; insufficient history for chronic recurrence."
            )
        else:
            evidence_summary = (
                f"Observed {total_events} obstruction event(s) across {observation_period_days} day(s). "
                f"Average duration: {avg_duration:.1f}s, average road-space loss: {avg_loss:.1f}%. "
                f"Peak concentration during {peak_str} with {temporal_consistency * 100:.0f}% temporal consistency."
            )

        return HistoricalPattern(
            road_id=road_id,
            observation_period_days=observation_period_days,
            total_events=total_events,
            total_duration_sec=round(total_duration, 1),
            average_duration_sec=round(avg_duration, 1),
            average_road_space_loss_pct=round(avg_loss, 2),
            frequency_per_day=round(frequency_per_day, 2),
            peak_hours=peak_hours,
            temporal_consistency=temporal_consistency,
            spatial_consistency=spatial_consistency,
            recurrence_score=recurrence_score,
            is_chronic=is_chronic,
            single_event_severity=single_event_severity,
            dominant_cause=dominant_cause,
            severity=severity,
            evidence_summary=evidence_summary,
        )

    def analyze_windows(
        self,
        road_id: str,
        observations: List[Dict[str, Any]],
        observation_period_days: int = 1,
        min_parked_space_pct: float = CHRONIC_MIN_PARKED_SPACE_PCT,
    ) -> HistoricalPattern:
        """
        Analyze a series of window observations (e.g. from /roads/{id}/history)
        using the authoritative recurrence engine. Deduplicates repeated window indices
        to ensure accurate recurrence fraction calculation.
        """
        if not observations:
            return HistoricalPattern(
                road_id=road_id,
                observation_period_days=observation_period_days,
                total_events=0,
                evidence_summary="Insufficient historical observations to evaluate recurrence.",
                is_chronic=False,
                single_event_severity=False,
                severity="normal",
            )

        # Deduplicate observations by window_index to prevent repeated phases/runs from inflating counts
        dedup_dict = {}
        for obs in observations:
            w_idx = obs.get("window_index")
            if w_idx is None:
                w_idx = obs.get("window_start_seconds", 0.0)
            dedup_dict[w_idx] = obs
        dedup_observations = list(dedup_dict.values())

        total_windows = len(dedup_observations)
        parked_windows = []
        causes = []

        for obs in dedup_observations:
            # Extract parked space and count
            p_space = float(obs.get("parked_space_pct") or obs.get("blocked_pct") or 0.0)
            breakdown = obs.get("movement_state_breakdown") or {}
            parked_count = int(breakdown.get("parked", 0)) if isinstance(breakdown, dict) else 0

            cause = str(obs.get("cause") or "normal")
            if cause not in ("normal", "unclassified"):
                causes.append(cause)

            if p_space >= min_parked_space_pct or parked_count >= 1:
                parked_windows.append(obs)

        parked_count_total = len(parked_windows)
        recurrence_fraction = parked_count_total / total_windows if total_windows > 0 else 0.0

        # Hours extraction from window start
        hours = []
        losses = []
        for w in parked_windows:
            start_sec = float(w.get("window_start_seconds") or w.get("timestamp") or 0.0)
            h = int(start_sec // 3600) % 24
            hours.append(h)
            losses.append(float(w.get("parked_space_pct") or w.get("blocked_pct") or 0.0))

        hour_counts = Counter(hours)
        peak_hours = [h for h, _ in hour_counts.most_common(3)]
        top2_count = sum(c for _, c in hour_counts.most_common(2))
        temporal_consistency = round(top2_count / parked_count_total, 2) if parked_count_total > 0 else 0.0

        avg_loss = sum(losses) / parked_count_total if parked_count_total > 0 else 0.0
        frequency_per_day = parked_count_total / max(1, observation_period_days)

        freq_factor = min(1.0, frequency_per_day / 4.0)
        recurrence_score = round(
            0.50 * recurrence_fraction + 0.30 * temporal_consistency + 0.20 * freq_factor,
            2,
        )

        single_event_severity = (
            total_windows <= 2 and parked_count_total >= 1 and avg_loss >= 35.0
        )

        # Enforce minimum total historical observation threshold (min_events_for_chronic)
        is_chronic = (
            total_windows >= self.min_events_for_chronic
            and parked_count_total >= self.min_events_for_chronic
            and recurrence_score >= self.chronic_recurrence_threshold
        )

        dominant_cause = Counter(causes).most_common(1)[0][0] if causes else "illegal_parking"

        if (is_chronic or single_event_severity) and avg_loss >= 25.0:
            severity = "critical"
        elif is_chronic or single_event_severity or avg_loss >= 15.0:
            severity = "high"
        elif avg_loss >= 5.0 or parked_count_total >= 2:
            severity = "moderate"
        else:
            severity = "low"

        peak_str = ", ".join(f"{h:02d}:00" for h in peak_hours) if peak_hours else "varied"
        evidence_summary = (
            f"Observed {parked_count_total} problematic window(s) across {total_windows} total windows "
            f"({recurrence_fraction * 100:.1f}% recurrence fraction). "
            f"Avg road-space loss: {avg_loss:.1f}%. Peak hours: {peak_str}."
        )

        return HistoricalPattern(
            road_id=road_id,
            observation_period_days=observation_period_days,
            total_events=parked_count_total,
            total_duration_sec=round(parked_count_total * 10.0, 1),
            average_duration_sec=round(avg_loss * 2.0, 1),
            average_road_space_loss_pct=round(avg_loss, 2),
            frequency_per_day=round(frequency_per_day, 2),
            peak_hours=peak_hours,
            temporal_consistency=temporal_consistency,
            spatial_consistency=0.5,
            recurrence_score=recurrence_score,
            is_chronic=is_chronic,
            single_event_severity=single_event_severity,
            dominant_cause=dominant_cause,
            severity=severity,
            evidence_summary=evidence_summary,
        )
