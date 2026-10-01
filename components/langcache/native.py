"""Documented Redis LangCache Data Plane adapter; inactive until provisioned."""
from __future__ import annotations

from urllib.parse import quote

import httpx


class NativeLangCache:
    def __init__(self, endpoint: str, cache_id: str, api_key: str):
        if not all((endpoint, cache_id, api_key)):
            raise ValueError("IRIS_LANGCACHE_URL, CACHE_ID and API_KEY are required")
        self.base = endpoint.rstrip("/") + "/v1/caches/" + quote(cache_id, safe="")
        self.headers = {"Authorization": "Bearer " + api_key}

    def health(self) -> dict:
        with httpx.Client(timeout=10) as client:
            response = client.get(self.base + "/health", headers=self.headers)
            response.raise_for_status()
            return response.json()

    def search(self, question: str) -> dict:
        with httpx.Client(timeout=15) as client:
            response = client.post(self.base + "/entries/search", headers=self.headers, json={"prompt": question})
            response.raise_for_status()
            return response.json()

    def store(self, question: str, answer: str) -> dict:
        with httpx.Client(timeout=15) as client:
            response = client.post(self.base + "/entries", headers=self.headers, json={"prompt": question, "response": answer})
            response.raise_for_status()
            return response.json()

    def delete_event(self, event_id: str) -> None:
        raise RuntimeError("Native LangCache event isolation/deletion is pending a provisioned cache")
