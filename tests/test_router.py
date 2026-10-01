import httpx

from components.decision_router.router import DecisionRouter


def test_jev_choice_response(monkeypatch):
    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(200, json={"answers": {"route": {"choice": "search", "confidence": 0.72, "probabilities": {"search": 0.8}}}})

    real_client = httpx.Client
    monkeypatch.setattr("components.decision_router.router.httpx.Client", lambda **kwargs: real_client(transport=httpx.MockTransport(respond), **kwargs))
    router = DecisionRouter("jev", "http://localhost:18081")
    decision = router.decide("What is the rule?")
    assert decision.route == "search"
    assert decision.engine == "local RSI-Jev typed choice model"
    assert requests[0].url.path == "/v1/systemone"
    assert b'"type":"choice"' in requests[0].content


def test_router_falls_back_when_service_missing():
    router = DecisionRouter("jev", "")
    decision = router.decide("What is the charging station status right now?")
    assert decision.route == "status"
    assert "fallback" in decision.engine
    assert router.last_error


def test_explicit_rule_intent_overrides_bad_model_choice(monkeypatch):
    real_client = httpx.Client
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={"answers": {"route": {"choice": "faq", "confidence": 0.5}}}))
    monkeypatch.setattr("components.decision_router.router.httpx.Client", lambda **kwargs: real_client(transport=transport, **kwargs))
    decision = DecisionRouter("jev", "http://localhost:18081").decide("Cite the priority delivery rule")
    assert decision.route == "search"
    assert "guardrail" in decision.engine
