from __future__ import annotations

import threading
import time
from contracts.models import TrackedPerson


class AttentionManager:
    def __init__(self, robot, timeout_seconds: float = 45):
        self.robot = robot
        self.timeout_seconds = timeout_seconds
        self._lock = threading.RLock()
        self.tracks: dict[int, TrackedPerson] = {}
        self.stability: dict[int, int] = {}
        self.served: set[int] = set()
        self.active_id: int | None = None
        self.state = "scanning"
        self.started_at = 0.0
        self.last_seen = 0.0
        self.last_scan = 0.0
        self.conversation_complete_count = 0
        self.stopped = False

    def update(self, tracks: list[TrackedPerson]) -> None:
        with self._lock:
            if self.stopped:
                return
            current = {person.track_id: person for person in tracks}
            self.stability = {pid: self.stability.get(pid, 0) + 1 for pid in current}
            self.tracks = current
            if self.active_id in current:
                self.last_seen = time.monotonic()
                self.robot.aim_at(current[self.active_id].aim)
                if self.state == "lost":
                    self.state = "engaged"
            elif self.active_id is not None and time.monotonic() - self.last_seen > 2:
                self.state = "lost"
                self.robot.clear_aim()
            if self.active_id is None:
                self._select_unserved()

    def _select_unserved(self) -> bool:
        candidates = [p for p in self.tracks.values() if p.track_id not in self.served and self.stability.get(p.track_id, 0) >= 2]
        if not candidates:
            self.state = "scanning"
            return False
        # Prefer a clear, larger participant box while keeping the choice stable once made.
        chosen = max(candidates, key=lambda p: (p.box[2] - p.box[0]) * (p.box[3] - p.box[1]) * p.confidence)
        self._invite(chosen)
        return True

    def _invite(self, person: TrackedPerson) -> None:
        self.active_id = person.track_id
        self.started_at = self.last_seen = time.monotonic()
        self.state = "inviting"
        self.robot.aim_at(person.aim)
        self.robot.wave()

    def select(self, track_id: int) -> bool:
        with self._lock:
            if self.stopped:
                return False
            person = self.tracks.get(track_id)
            if not person:
                return False
            self._invite(person)
            return True

    def engage(self) -> None:
        with self._lock:
            if self.active_id is not None:
                self.state = "engaged"
                self.started_at = time.monotonic()

    def complete(self) -> None:
        with self._lock:
            if self.active_id is not None:
                self.served.add(self.active_id)
                self.conversation_complete_count += 1
            self.active_id = None
            self.robot.clear_aim()
            self.state = "scanning"
            self._select_unserved()

    def skip(self) -> None:
        self.complete()

    def tick(self) -> None:
        with self._lock:
            if self.stopped:
                return
            now = time.monotonic()
            if self.active_id is not None and now - self.started_at > self.timeout_seconds:
                self.complete()
            elif self.active_id is None and not self.tracks and now - self.last_scan > 6:
                self.last_scan = now
                self.robot.sweep()

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "state": self.state,
                "active_track_id": self.active_id,
                "served_track_ids": sorted(self.served),
                "tracks": [person.to_dict() for person in self.tracks.values()],
                "completed_interactions": self.conversation_complete_count,
            }

    def reset(self) -> None:
        with self._lock:
            self.stopped = True
            self.tracks.clear()
            self.stability.clear()
            self.served.clear()
            self.active_id = None
            self.state = "stopped"
            self.robot.clear_aim()
