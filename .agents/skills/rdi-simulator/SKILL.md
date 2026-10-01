---
name: reachy-rdi-simulator
description: Change the presenter mission board that simulates RDI by writing station state directly to Redis.
---

# Simulated RDI

Own `components/rdi_simulator/board.py`. A presenter click writes a JSON station record directly to Redis. No PostgreSQL, CDC connector, or RDI pipeline is involved. Keep the source field and UI badge explicit about this boundary.

Verify that CLOSED immediately changes the subsequent status answer and that event-end deletion removes the record. Run `pytest tests/test_story.py`.

