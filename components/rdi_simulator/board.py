from __future__ import annotations

import json
from redis import Redis


class MissionBoard:
    def __init__(self, redis: Redis, event_id: str):
        self.redis = redis
        self.key = f"iris:event:{event_id}:station:charging"

    def seed(self) -> None:
        if not self.redis.exists(self.key):
            self.update("OPEN")

    def update(self, status: str) -> dict[str, str]:
        status = status.upper()
        if status not in {"OPEN", "CLOSED"}:
            raise ValueError("Station status must be OPEN or CLOSED")
        record = {"station": "charging", "status": status, "source": "simulated RDI: direct presenter write"}
        self.redis.execute_command("JSON.SET", self.key, "$", json.dumps(record))
        self.redis.expire(self.key, 86400)
        return record

    def get(self) -> dict[str, str]:
        raw = self.redis.execute_command("JSON.GET", self.key)
        return json.loads(raw) if raw else {"station": "charging", "status": "UNKNOWN", "source": "simulated RDI"}
