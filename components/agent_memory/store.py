from __future__ import annotations

import json
import re
import uuid
from redis import Redis


def normalized_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")


class LocalAgentMemory:
    """Direct confirmed facts and session events; no native Iris promotion claim."""

    def __init__(self, redis: Redis, event_id: str):
        self.redis = redis
        self.prefix = f"iris:event:{event_id}:"

    def register(self, name: str, fact: str, consent: bool) -> dict[str, str]:
        if not consent:
            raise ValueError("Opt-in consent is required to store a fact")
        name, fact = name.strip(), fact.strip()
        if not name or not fact or len(name) > 80 or len(fact) > 300:
            raise ValueError("Enter a name (1–80 characters) and fact (1–300 characters)")
        slug = normalized_name(name)
        if not slug:
            raise ValueError("Name must contain letters or numbers")
        existing = self.redis.get(self.prefix + "name:" + slug)
        participant_id = existing or uuid.uuid4().hex
        record = {"id": participant_id, "name": name, "fact": fact, "consent": True}
        key = self.prefix + "participant:" + participant_id
        self.redis.execute_command("JSON.SET", key, "$", json.dumps(record))
        self.redis.set(self.prefix + "name:" + slug, participant_id, ex=86400)
        self.redis.expire(key, 86400)
        self.record_event(participant_id, "confirmed_fact", fact)
        return record

    def by_id(self, participant_id: str | None) -> dict[str, str] | None:
        if not participant_id or not re.fullmatch(r"[a-f0-9]{32}", participant_id):
            return None
        raw = self.redis.execute_command("JSON.GET", self.prefix + "participant:" + participant_id)
        return json.loads(raw) if raw else None

    def by_name(self, name: str) -> dict[str, str] | None:
        pid = self.redis.get(self.prefix + "name:" + normalized_name(name))
        return self.by_id(pid)

    def record_event(self, participant_id: str, kind: str, text: str) -> None:
        key = self.prefix + "session:" + participant_id
        self.redis.xadd(key, {"kind": kind, "text": text[:500]}, maxlen=100, approximate=True)
        self.redis.expire(key, 86400)

    def forget_all(self) -> int:
        removed = 0
        for key in self.redis.scan_iter(match=self.prefix + "*", count=100):
            removed += self.redis.delete(key)
        return removed

