# Reachy Mini Mission Control

This repository is an event-only demo. Read the matching skill in `.agents/skills/<component>/SKILL.md` when changing a component; the shared shapes are in `contracts/models.py`.

The real local database is Redis Enterprise with Redis Search and JSON. `rdi_simulator` writes directly to Redis and must always be labelled as simulated RDI. `agent_memory`, `langcache`, and `context_retriever` are local equivalents until native Iris calls are verified. Never claim that the Enterprise container includes those Iris services.

Keep participant facts opt-in and event-scoped. Do not store camera frames or use face recognition. `robot_io` is the only writer of motor commands; `participant_tracking` publishes temporary tracks and `attention_manager` chooses whom to invite. Keep missing API and physical-hardware checks in `OPEN_TASKS.md` until tested end to end.

