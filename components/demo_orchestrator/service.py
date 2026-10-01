from __future__ import annotations

from redis import Redis
from contracts.models import Answer, Evidence, TraceStep
from components.agent_memory.store import LocalAgentMemory
from components.context_retriever.retriever import LocalContextRetriever
from components.decision_router.router import DecisionRouter
from components.langcache.store import LocalLangCache
from components.model_gateway.gateway import ModelGateway
from components.rdi_simulator.board import MissionBoard
from components.redis_search.store import SearchStore
from settings import Settings


class MissionControl:
    def __init__(self, redis: Redis, settings: Settings, robot, attention):
        self.redis, self.settings = redis, settings
        self.robot, self.attention = robot, attention
        self.search = SearchStore(redis, settings.event_id)
        self.board = MissionBoard(redis, settings.event_id)
        self.memory = LocalAgentMemory(redis, settings.event_id)
        self.cache = LocalLangCache(redis, settings.event_id)
        self.retriever = LocalContextRetriever(self.search, self.board)
        self.router = DecisionRouter(settings.router_mode, settings.jev_url, settings.jev_api_key)
        self.gateway = ModelGateway(settings)
        self.closed_key = f"iris:event:{settings.event_id}:closed"

    def ensure_open(self) -> None:
        if self.redis.exists(self.closed_key):
            raise ValueError("This event has ended. Choose a new DEMO_EVENT_ID to start another event.")

    def setup(self) -> dict:
        self.ensure_open()
        self.search.seed()
        self.board.seed()
        return {"documents": 4, "station": self.board.get(), "search_index": self.search.index}

    def register(self, name: str, fact: str, consent: bool) -> dict:
        self.ensure_open()
        return self.memory.register(name, fact, consent)

    def participants(self) -> list[dict]:
        prefix = self.memory.prefix + "participant:"
        result = []
        for key in self.redis.scan_iter(match=prefix + "*", count=100):
            participant = self.memory.by_id(str(key).removeprefix(prefix))
            if participant:
                result.append(participant)
        return sorted(result, key=lambda row: row["name"].lower())

    def ask(self, question: str, participant_id: str | None = None) -> Answer:
        self.ensure_open()
        question = question.strip()
        if not question or len(question) > 500:
            raise ValueError("Question must be 1–500 characters")
        self.attention.engage()
        participant = self.memory.by_id(participant_id)
        if participant_id and not participant:
            raise ValueError("Participant is not registered for this event")
        if participant:
            self.memory.record_event(participant["id"], "user_question", question)
        route = self.router.decide(question)
        trace = [TraceStep("Decision Router", route.engine, f"{route.route}: {route.reason}")]
        if participant:
            trace.append(TraceStep("Agent Memory", "local Redis-backed equivalent", f"Opt-in participant: {participant['name']}"))

        if route.route == "faq" and not participant:
            cached = self.cache.lookup(question)
            trace.append(TraceStep("LangCache", "local token-similarity equivalent", "hit" if cached else "miss"))
            if cached:
                return Answer(cached, route.route, route.engine, [], trace, True)

        evidence: list[Evidence] = []
        if route.route in {"search", "status", "faq", "finale"}:
            include_status = route.route in {"status", "finale"}
            evidence = self.retriever.retrieve(question, include_status=include_status)
            trace.append(TraceStep("Redis Search + JSON", "native in Redis Enterprise", f"{len(evidence) - int(include_status)} indexed documents"))
            trace.append(TraceStep("Context Retriever", "local evidence assembler", f"{len(evidence)} cited items"))
            if include_status:
                trace.append(TraceStep("RDI", "SIMULATED: direct presenter write", self.board.get()["status"]))

        if route.route == "memory":
            if participant:
                text = f"{participant['name']}, I remember that {participant['fact']}. You told me before the presentation."
            else:
                text = "Please tell me your name and select your opt-in registration so I can recall your fact."
            engine = "local confirmed-fact recall"
        else:
            text, engine = self.gateway.answer(question, evidence, participant if route.route == "finale" else None)
        trace.append(TraceStep("Answer Model", engine, "Answer assembled from the listed evidence"))
        if route.route == "faq" and not participant:
            self.cache.store(question, text)
        if participant:
            self.memory.record_event(participant["id"], "robot_answer", text)
        return Answer(text, route.route, route.engine, evidence, trace)

    def update_station(self, status: str) -> dict:
        self.ensure_open()
        return self.board.update(status)

    def end_event(self) -> dict:
        removed = self.memory.forget_all()
        self.search.clear_index()
        self.redis.set(self.closed_key, "1", ex=86400)
        self.attention.reset()
        return {"deleted_event_keys": removed, "event_closed": True}
