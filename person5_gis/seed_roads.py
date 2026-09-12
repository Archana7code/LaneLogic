"""
LaneLogic - PERSON 5: GIS/Mapping
====================================
seed_roads.py - one-time helper that pushes demo road metadata
(sample_roads.json) into Person 3's backend so the map has something to
display (id, name, lat/lng, polygon) before any live video has been
processed.

Run:
  python seed_roads.py --api http://localhost:8000
"""

import argparse
import json

import requests


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", default="http://localhost:8000")
    parser.add_argument("--file", default="sample_roads.json")
    args = parser.parse_args()

    with open(args.file) as f:
        roads = json.load(f)

    for road in roads:
        resp = requests.post(f"{args.api}/roads", json=road, timeout=10)
        resp.raise_for_status()
        print(f"[Person5] Seeded road {road['id']} - {road['name']}")


if __name__ == "__main__":
    main()
