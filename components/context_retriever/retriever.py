from __future__ import annotations

from contracts.models import Evidence
from components.rdi_simulator.board import MissionBoard
from components.redis_search.store import SearchStore


class LocalContextRetriever:
    def __init__(self, search: SearchStore, board: MissionBoard):
        self.search_store = search
        self.board = board

    def retrieve(self, question: str, include_status: bool = False) -> list[Evidence]:
        evidence = self.search_store.search(question)
        if include_status:
            station = self.board.get()
            evidence.append(Evidence(
                "charging-live", "Charging station live status",
                f"Charging station is {station['status']}.", station["source"],
            ))
        return evidence

