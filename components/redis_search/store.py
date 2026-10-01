from __future__ import annotations

import json
import re
from redis import Redis
from redis.exceptions import ResponseError
from contracts.models import Evidence

MISSION_DOCS = [
    {"id": "safety", "title": "Mission safety rule", "body": "The robot may invite a participant only after it has a stable visual track. If a participant declines, thank them and move on. The presenter can pause or skip at any time.", "source": "Mission Handbook §1"},
    {"id": "charging", "title": "Charging station rule", "body": "A courier may use the charging station only when its live status is OPEN. If it is CLOSED, choose the alternate station and explain why.", "source": "Mission Handbook §2"},
    {"id": "priority", "title": "Priority delivery rule", "body": "A priority delivery goes to the volunteer who has not yet taken a turn. Personal facts may personalize the greeting only after the volunteer identifies themselves and has opted in.", "source": "Mission Handbook §3"},
    {"id": "faq", "title": "Mission Control FAQ", "body": "Redis Search finds indexed documents. Agent Memory keeps session and long-term context. LangCache can reuse similar public answers. Context Retriever assembles governed evidence for an answer.", "source": "Mission Handbook FAQ"},
]


class SearchStore:
    def __init__(self, redis: Redis, event_id: str):
        self.redis = redis
        self.event_id = event_id
        self.index = f"iris:idx:{event_id}:docs"
        self.prefix = f"iris:event:{event_id}:doc:"

    def seed(self) -> None:
        for doc in MISSION_DOCS:
            self.redis.execute_command("JSON.SET", self.prefix + doc["id"], "$", json.dumps(doc))
            self.redis.expire(self.prefix + doc["id"], 86400)
        try:
            self.redis.execute_command(
                "FT.CREATE", self.index, "ON", "JSON", "PREFIX", "1", self.prefix,
                "SCHEMA", "$.title", "AS", "title", "TEXT", "$.body", "AS", "body", "TEXT",
            )
        except ResponseError as exc:
            if "Index already exists" not in str(exc):
                raise

    def search(self, question: str, limit: int = 3) -> list[Evidence]:
        terms = re.findall(r"[a-zA-Z0-9]+", question.lower())
        terms = [t for t in terms if len(t) > 2 and t not in {"the", "what", "where", "does", "have", "can", "with", "and", "for", "about", "our", "your"}]
        query = " | ".join(dict.fromkeys(terms[:7])) or "*"
        result = self.redis.execute_command("FT.SEARCH", self.index, query, "LIMIT", "0", str(limit), "DIALECT", "2")
        found: list[Evidence] = []
        for pos in range(1, len(result), 2):
            key = result[pos]
            raw = self.redis.execute_command("JSON.GET", key)
            if raw:
                doc = json.loads(raw)
                found.append(Evidence(doc["id"], doc["title"], doc["body"], doc["source"]))
        return found

    def clear_index(self) -> None:
        try:
            self.redis.execute_command("FT.DROPINDEX", self.index)
        except ResponseError as exc:
            if "Unknown Index name" not in str(exc):
                raise
