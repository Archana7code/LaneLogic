import requests

obs = []
for i in range(5):
    obs.append({
        "road_id": "ROAD_001",
        "window_index": i,
        "window_start_seconds": i * 2,
        "window_end_seconds": (i + 1) * 2,
        "vehicle_count": 4,
        "vehicle_type_breakdown": {"car": 3, "truck": 1},
        "movement_state_breakdown": {"moving": 1, "parked": 2, "signal_waiting": 1},
        "occupancy_pct": 35.0,
        "blocked_pct": 22.0,
        "cause": "loading_unloading",
        "cause_explanation": "test data",
    })

r = requests.post("http://localhost:8000/analysis/bulk", json={"observations": obs})
print(r.status_code, r.json())