from __future__ import annotations

import hashlib
import json
import re
from redis import Redis


def tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in {"the", "a", "an", "please", "tell", "me"}}


class LocalLangCache:
    """Small event-only token-similarity cache for public FAQ answers."""

    def __init__(self, redis: Redis, event_id: str):
        self.redis = redis
        self.prefix = f"iris:event:{event_id}:cache:"

    def lookup(self, question: str) -> str | None:
        wanted = tokens(question)
        if not wanted:
            return None
        best_score, best_answer = 0.0, None
        for key in self.redis.scan_iter(match=self.prefix + "*", count=100):
            raw = self.redis.get(key)
            if not raw:
                continue
            entry = json.loads(raw)
            seen = set(entry["tokens"])
            score = len(wanted & seen) / len(wanted | seen)
            if score > best_score:
                best_score, best_answer = score, entry["answer"]
        return best_answer if best_score >= 0.8 else None

    def store(self, question: str, answer: str) -> None:
        digest = hashlib.sha256(question.lower().strip().encode()).hexdigest()[:20]
        self.redis.set(self.prefix + digest, json.dumps({"tokens": sorted(tokens(question)), "answer": answer}), ex=86400)

