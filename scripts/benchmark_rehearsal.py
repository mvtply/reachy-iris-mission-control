"""Synthetic latency probe for model loading and one detector + router cycle.

It does not measure multi-person accuracy, tracking stability, or Reachy motion.
"""
from __future__ import annotations

import json
import os
import statistics
import time

import numpy as np

from components.decision_router.router import DecisionRouter
from components.participant_tracking.tracker import PersonTracker


def main() -> None:
    router = DecisionRouter("jev", os.environ["DEMO_JEV_URL"])
    start = time.perf_counter()
    tracker = PersonTracker(os.environ.get("DEMO_VISION_MODEL", "PekingU/rtdetr_r18vd"))
    loading_seconds = time.perf_counter() - start
    # No photo is recorded. The blank image is for timing only.
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    prompts = [
        "What do you remember about me?",
        "What does Redis Iris help an agent do?",
        "What is the priority delivery rule?",
        "Is the charging station open right now?",
        "Combine what you remember about me with the priority rule and charging status.",
    ]
    rows = []
    for question in prompts:
        start = time.perf_counter()
        tracker.update(frame)
        detector_seconds = time.perf_counter() - start
        decision = router.decide(question)
        route_seconds = time.perf_counter() - start - detector_seconds
        rows.append({"question": question, "route": decision.route, "engine": decision.engine, "detector_seconds": round(detector_seconds, 3), "router_seconds": round(route_seconds, 3), "combined_seconds": round(time.perf_counter() - start, 3)})
    print(json.dumps({"kind": "synthetic blank-frame latency only", "device": tracker.device, "load_seconds": round(loading_seconds, 3), "median_combined_seconds": round(statistics.median(row["combined_seconds"] for row in rows), 3), "rows": rows}, indent=2))


if __name__ == "__main__":
    main()
