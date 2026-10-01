from __future__ import annotations

import httpx
from contracts.models import RouteDecision

ROUTES = ("memory", "faq", "search", "status", "finale")


def rules_route(question: str) -> RouteDecision:
    q = question.lower()
    if any(x in q for x in ("combine", "together", "my fact", "for me and", "given what you know")):
        route = "finale"
    elif any(x in q for x in ("remember", "my name", "my fact", "about me")):
        route = "memory"
    elif any(x in q for x in ("status", "open", "closed", "charging station", "right now")):
        route = "status"
    elif any(x in q for x in ("rule", "handbook", "cite", "source", "priority")):
        route = "search"
    else:
        route = "faq"
    return RouteDecision(route, "local rules fallback", "Transparent rehearsal routing")


class DecisionRouter:
    def __init__(self, mode: str, url: str, api_key: str = ""):
        self.mode, self.url, self.api_key = mode, url, api_key
        self.last_error: str | None = None
        self.verified = False

    def decide(self, question: str) -> RouteDecision:
        if self.mode != "jev":
            return rules_route(question)
        if not self.url:
            self.last_error = "DEMO_JEV_URL is not configured"
            fallback = rules_route(question)
            return RouteDecision(fallback.route, "local rules fallback (JEV service pending)", self.last_error)
        try:
            request = {
                "model": "jev-latest",
                "state": [{"role": "user", "content": question}],
                "questions": {"route": {
                    "type": "choice",
                    "instructions": "Which route should handle this robot request? Choose the most specific option.",
                    "criteria": {
                        "memory": "Recall an opted-in participant's name or fact from earlier conversation",
                        "faq": "Answer a public, repeatable general question",
                        "search": "Find and cite a rule or document",
                        "status": "Read the current live station state",
                        "finale": "Combine personal memory, a cited rule, and live state",
                    },
                }},
            }
            headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
            with httpx.Client(timeout=25) as client:
                response = client.post(self.url.rstrip("/") + "/v1/systemone", json=request, headers=headers)
                response.raise_for_status()
                result = response.json()["answers"]["route"]
            choice = result["choice"]
            if choice not in ROUTES:
                raise ValueError(f"Unknown route from JEV: {choice}")
            self.last_error = None
            self.verified = True
            confidence = result.get("confidence")
            explicit = rules_route(question)
            if explicit.route != "faq" and choice != explicit.route:
                return RouteDecision(
                    explicit.route,
                    "local RSI-Jev proposal + explicit-intent guardrail",
                    f"model proposed {choice} (confidence={confidence}); explicit request requires {explicit.route}",
                )
            return RouteDecision(choice, "local RSI-Jev typed choice model", f"confidence={confidence}; probabilities={result.get('probabilities')}")
        except Exception as exc:
            self.last_error = str(exc)
            fallback = rules_route(question)
            return RouteDecision(fallback.route, "local rules fallback (JEV service unavailable)", str(exc)[:160])
