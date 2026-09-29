#!/usr/bin/env python3
"""
LaneLogic - PERSON 6: demo data so every dashboard page has something to show.

Uses ONLY the public API of Person 3's backend (no other file is touched). Standard library only.
All data is SYNTHETIC and tagged as demo (event ids start with DEMO-, notes say DEMO DATA).
Use it to preview the UI before the real video pipeline has produced results.

    python person6_frontend/demo_seed.py
    python person6_frontend/demo_seed.py --api http://localhost:8000 --dry-run
"""
import argparse
import json
import sys
import urllib.error
import urllib.request

# One profile per road, worst first: critical, high, moderate, clear.
PROFILES = [
    dict(pct=41.0, level="critical", score=4, cause="loading_unloading", occ=82.0, types={"truck": 5, "van": 3, "car": 6}, dwell=2820, vt="truck", zone=(9, 92.0)),
    dict(pct=24.0, level="high", score=3, cause="illegal_parking", occ=64.0, types={"car": 9, "auto": 3}, dwell=1500, vt="car", zone=(6, 74.0)),
    dict(pct=12.0, level="moderate", score=2, cause="school_dropoff", occ=48.0, types={"car": 7, "bus": 1}, dwell=420, vt="car", zone=None),
    dict(pct=2.0, level="normal", score=0, cause="general_congestion", occ=25.0, types={"car": 5}, dwell=60, vt="car", zone=None),
]
FALLBACK_ROADS = [
    ("ROAD_001", "Noida", 28.5355, 77.3910), ("ROAD_002", "Delhi", 28.6139, 77.2090),
    ("ROAD_003", "Ghaziabad", 28.6692, 77.4538), ("ROAD_004", "Faridabad", 28.4089, 77.3178),
]
SHAPE = [0.35, 0.55, 0.8, 1.0, 0.9, 0.7, 0.85, 0.95, 0.75, 1.0]  # last window == profile value
WIDTH_M = 7.0


def call(api, method, path, body=None, dry=False):
    if dry:
        print(f"  [dry-run] {method} {path}")
        return 200, []
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(api + path, data=data, method=method, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            raw = r.read().decode()
            return r.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:200]
    except Exception as e:  # connection refused etc.
        print(f"\nCannot reach the backend at {api}: {e}\nStart it first:  python start_backend.py")
        sys.exit(1)


def report(label, res):
    ok = res[0] < 300
    print(f"  {'OK  ' if ok else 'FAIL'} {label}" + ("" if ok else f"  -> {res[0]} {res[1]}"))
    return ok


def build_observations(road_id, p):
    out = []
    for i, k in enumerate(SHAPE):
        pct = round(p["pct"] * k, 1)
        out.append({
            "road_id": road_id, "window_index": i, "window_start_seconds": i * 60, "window_end_seconds": (i + 1) * 60,
            "vehicle_count": sum(p["types"].values()), "vehicle_type_breakdown": p["types"],
            "movement_state_breakdown": {"moving": 6, "parked": max(1, round(pct / 8))},
            "road_length_meters": 60.0, "road_width_meters": WIDTH_M,
            "occupancy_pct": round(p["occ"] * (0.7 + 0.3 * k), 1), "parked_space_pct": pct,
            "parked_width_meters": round(pct / 100 * WIDTH_M, 2), "blocked_pct": pct,
            "severity": p["level"], "priority_score": p["score"], "cause": p["cause"],
            "cause_explanation": f"DEMO DATA: pattern consistent with {p['cause'].replace('_', ' ')}.",
        })
    return out


def build_events(road_id, p):
    events = []
    n = 4 if p["score"] >= 3 else 2 if p["score"] == 2 else 1
    for i in range(n):
        loss = round(p["pct"] * (1.0 - 0.18 * i), 1)
        dur = max(30, int(p["dwell"] * (1.0 - 0.25 * i)))
        events.append({
            "event_id": f"DEMO-{road_id}-{i + 1}", "road_id": road_id, "camera_id": "CAM_01",
            "vehicle_id": 100 + i, "vehicle_type": p["vt"] if i % 2 == 0 else "car",
            "start_time": float(i * 90), "end_time": float(i * 90 + dur), "duration_sec": float(dur),
            "location": [480.0 + 40 * i, 300.0], "bbox": [420.0 + 40 * i, 250.0, 540.0 + 40 * i, 350.0],
            "road_width_m": WIDTH_M, "occupied_width_m": round(loss / 100 * WIDTH_M, 2),
            "road_space_loss_pct": loss, "recurrence_score": p["zone"][1] if p["zone"] else 20.0,
            "cause": p["cause"], "cause_confidence": round(0.92 - 0.06 * i, 2),
            "cause_explanation": "DEMO DATA: long dwell with high share of road width lost.",
            "severity": p["level"], "status": "active" if i < 2 else "resolved", "metadata": {"demo": True},
        })
    return events


def main():
    ap = argparse.ArgumentParser(description="Seed demo data so the dashboard has content.")
    ap.add_argument("--api", default="http://localhost:8000")
    ap.add_argument("--dry-run", action="store_true", help="print the calls without sending them")
    a = ap.parse_args()
    api, dry = a.api.rstrip("/"), a.dry_run

    print("1/6 Roads")
    _, roads = call(api, "GET", "/roads", dry=dry)
    ids = [r["id"] for r in roads] if isinstance(roads, list) else []
    if not ids:
        for rid, name, lat, lon in FALLBACK_ROADS:
            report(f"create {rid}", call(api, "POST", "/roads", {"id": rid, "name": name, "latitude": lat, "longitude": lon}, dry))
        ids = [r[0] for r in FALLBACK_ROADS]
    ids = ids[: len(PROFILES)]
    print(f"     using roads: {', '.join(ids)}")
    pairs = list(zip(ids, PROFILES))

    print("2/6 Analysis windows (fills usable-space numbers and history charts)")
    for rid, p in pairs:
        report(f"{rid}: {len(SHAPE)} windows", call(api, "POST", "/analysis/bulk", {"observations": build_observations(rid, p)}, dry))

    print("3/6 Obstruction events (fills the event log and triggers alerts)")
    for rid, p in pairs:
        for e in build_events(rid, p):
            report(e["event_id"], call(api, "POST", "/events", e, dry))

    print("4/6 Chronic zones (repeat offenders)")
    zones = [{"road_id": rid, "dominant_cause": p["cause"], "occurrence_count": p["zone"][0], "severity_score": p["zone"][1],
              "notes": "DEMO DATA: same obstruction seen in many windows."} for rid, p in pairs if p["zone"]]
    report(f"{len(zones)} zones", call(api, "POST", "/chronic-zones/bulk", zones, dry))

    print("5/6 Recommendations")
    for rid, p in pairs:
        if p["score"] >= 2:
            report(rid, call(api, "POST", "/recommendations/generate",
                             {"road_id": rid, "cause": p["cause"], "cause_confidence": 0.85, "road_space_loss_pct": p["pct"]}, dry))

    print("6/6 One measured outcome (closed-loop validation panel)")
    rid = ids[0]
    report(rid, call(api, "POST", "/interventions/outcome", {
        "road_id": rid, "intervention_type": "Designated loading zone with time-window restriction",
        "implementation_date": "2026-09-20", "baseline_window_description": "14 days before",
        "post_window_description": "14 days after",
        "baseline_metrics": {"road_space_loss_pct": 18.2, "avg_dwell_min": 49.0},
        "post_metrics": {"road_space_loss_pct": 7.1, "avg_dwell_min": 12.0},
        "notes": "DEMO DATA: illustrative figures, not a real measurement.",
    }, dry))

    print("\nDone. Refresh http://localhost:5173")


if __name__ == "__main__":
    main()
