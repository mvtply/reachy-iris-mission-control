---
name: reachy-context-retriever
description: Change cited evidence assembly or wire a verified native Iris Context Retriever surface.
---

# Context Retriever equivalent

Own `components/context_retriever/`. Return `Evidence` objects with explicit source and provenance. Indexed rules come from `redis_search`; live station state comes from `rdi_simulator`. The MCP URL and agent key are saved, and `search_missionrule_by_text` was verified. `native.py` remains a placeholder until its tool arguments, citations, and event cleanup are bound and tested. The MCP URL and key are sufficient for connecting; no separate surface ID is required. Preserve the local-assembler label until that path is enabled.

Do not let an answer cite a document that was not retrieved. Run `pytest tests/test_story.py` after changing evidence composition.
