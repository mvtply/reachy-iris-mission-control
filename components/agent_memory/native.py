"""Documented Redis Agent Memory Data Plane adapter; inactive until provisioned.

The demo uses LocalAgentMemory until event-scoped deletion is verified on a real
RAM store. The methods here keep the wire contract ready for that integration.
"""
from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import quote

import httpx


class NativeAgentMemory:
    def __init__(self, endpoint: str, store_id: str, api_key: str):
        if not all((endpoint, store_id, api_key)):
            raise ValueError("IRIS_AGENT_MEMORY_URL, STORE_ID and API_KEY are required")
        self.base = endpoint.rstrip("/") + "/v1/stores/" + quote(store_id, safe="")
        self.headers = {"Authorization": "Bearer " + api_key}

    def session_event(self, session_id: str, owner_id: str, role: str, text: str) -> dict:
        payload = {
            "sessionId": session_id,
            "actorId": owner_id,
            "role": role,
            "content": [{"text": text}],
            "createdAt": datetime.now(timezone.utc).isoformat(),
        }
        with httpx.Client(timeout=15) as client:
            response = client.post(self.base + "/session-memory/events", headers=self.headers, json=payload)
            response.raise_for_status()
            return response.json()

    def create_fact(self, memory_id: str, owner_id: str, text: str) -> dict:
        with httpx.Client(timeout=15) as client:
            response = client.post(self.base + "/long-term-memory", headers=self.headers, json={"memories": [{"id": memory_id, "text": text, "memoryType": "semantic", "ownerId": owner_id, "namespace": "reachy-event"}]})
            response.raise_for_status()
            return response.json()

    def search_facts(self, owner_id: str, query: str) -> dict:
        with httpx.Client(timeout=15) as client:
            response = client.post(self.base + "/long-term-memory/search", headers=self.headers, json={"text": query, "filter": {"ownerId": {"eq": owner_id}}})
            response.raise_for_status()
            return response.json()

    def delete_event(self, event_id: str) -> None:
        raise RuntimeError("Native RAM event deletion is pending a provisioned store and verified lifecycle contract")
