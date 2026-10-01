---
name: reachy-decision-router
description: Change the typed RSI-Jev route selection or its visible rehearsal fallback.
---

# Decision router

Own `components/decision_router/router.py`. RSI-Jev is a typed choice model, not a text generator. Call its `/v1/systemone` API with five named route criteria and read `answers.route.choice` and probabilities. The official serving contract is https://github.com/Shanghua-Gao/RSI-Jev/blob/main/serve/README.md.

`DEMO_JEV_URL` points to a locally running RSI-Jev server. If absent or failing, use and label rules fallback. Explicit memory, search, status, and finale requests have a visible deterministic guardrail when the model disagrees. Run `pytest tests/test_router.py`; do not claim the model ran unless the HTTP response passed validation. Synthetic Mac latency has been measured, while live audience latency remains open.
