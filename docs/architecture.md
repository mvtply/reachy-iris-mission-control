# Architecture

This application is a presenter-controlled story. `app.py` serves the screen and API, `settings.py` reads environment variables, `contracts/models.py` defines shared response shapes, and `components/demo_orchestrator/service.py` composes each answer. The component-specific agent instructions live in `.agents/skills/<component>/SKILL.md`.

## Component map

| Component | Owns | Runtime boundary |
| --- | --- | --- |
| `redis_enterprise` | Local container bootstrap, connection, and Search/JSON probe | Redis Enterprise database on localhost |
| `redis_search` | Four mission documents, JSON index, cited search | Native Redis Search and JSON |
| `rdi_simulator` | Charging station state | Direct JSON write to Redis; **simulated RDI** |
| `agent_memory` | Confirmed opt-in facts and session events | Local Redis equivalent; native adapter inactive |
| `langcache` | Public FAQ answer reuse | Local token-similarity equivalent; native adapter inactive |
| `context_retriever` | Evidence assembly from search and live board | Local equivalent; native MCP adapter inactive |
| `decision_router` | Typed choice among memory, FAQ, search, status, finale | Rules fallback or optional RSI-Jev HTTP service |
| `model_gateway` | Answer generation, transcription, speech synthesis | Template fallback or optional hosted APIs |
| `participant_tracking` | RT-DETR detections and temporary ByteTrack IDs | Optional in-memory camera processing |
| `attention_manager` | Stable target, invitation, conversation lock, handoff | Temporary tracks; no name inference |
| `robot_io` | Camera, microphone, laptop audio, head, body, antennas | Sole writer of robot motion commands |
| `demo_orchestrator` | Scene composition, trace labels, event lifecycle | Calls the components above |
| `presenter_app` | Stage script, controls, and component trace | Browser UI served from `app.py` |

## Answer path

1. A presenter submits `/api/ask` with a question and, only after spoken identification, an optional registered participant ID.
2. The router chooses a typed route. The screen reports whether RSI-Jev or the rules fallback made that choice.
3. The orchestrator uses only the components needed for that route. Public FAQ answers may come from the local cache; mission rules come from Redis Search; station status comes from the direct-write board; participant facts come from opt-in memory.
4. The gateway uses a configured answer endpoint or a deterministic template. The response includes `Answer.text`, `route`, `route_engine`, cited `evidence`, component `trace`, and `cache_hit`.
5. Speech synthesis is optional. The app remains usable with typed questions and muted mock mode.

The presenter endpoints are in `app.py`: `/api/setup` seeds the story; `/api/register`, `/api/participants`, `/api/ask`, and `/api/readback` handle conversation; `/api/board` changes live status; `/api/attention/*` handles target override and handoff; `/api/mock/tracks` rehearses without a robot; `/api/listen` captures five seconds for configured recognition; `/api/event/end` deletes local event data. `/api/status` reports the active modes and dependencies.

## Event data and privacy

Keys use an `iris:event:<event_id>:` prefix. Confirmed facts are JSON documents, session events are Redis Streams, the FAQ cache uses expiring strings, and the mission documents and station status use JSON. Event keys expire after 24 hours. Ending the event scans and deletes its keys, drops its Search index, and writes a 24-hour closure marker so that the same event ID cannot be reused accidentally. A new event needs a new `DEMO_EVENT_ID`.

Camera frames stay in memory. ByteTrack IDs are temporary and are not linked to names by vision. The presenter must confirm identification and consent before a fact can be recalled. The native Iris adapters are reference code, not active data paths; their lifecycle and event deletion remain open checks in `OPEN_TASKS.md`.
