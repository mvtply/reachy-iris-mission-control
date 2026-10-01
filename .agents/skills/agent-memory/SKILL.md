---
name: reachy-agent-memory
description: Change opt-in participant facts, session events, recall, or event deletion in the local memory equivalent.
---

# Agent Memory equivalent

Own `components/agent_memory/`. Confirm consent before storing a fact. The local store writes Redis JSON and Streams with 24-hour expiry and event-end deletion. `native.py` implements documented RAM Data Plane calls but is inactive until an endpoint, store ID, key, and event deletion behavior are verified. The presenter must retain the local-equivalent label.

Keep identities separate from temporary camera track IDs until a participant identifies themselves. When a native endpoint is provided, test actual write, recall, isolation, and deletion before changing the label. Run `pytest tests/test_story.py`.
