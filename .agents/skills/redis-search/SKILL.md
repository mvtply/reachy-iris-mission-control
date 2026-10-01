---
name: reachy-redis-search
description: Change native Redis JSON mission documents, indexing, and cited FT.SEARCH queries.
---

# Redis Search and JSON

Own `components/redis_search/store.py`. The local Enterprise database genuinely executes `JSON.SET`, `FT.CREATE`, and `FT.SEARCH`. Keep mission documents event-scoped and source-labelled. Avoid claiming search results came from an LLM.

Verify index creation and query results on the Enterprise database, then run `pytest tests/test_story.py`. Search and JSON capability must remain a native badge in the presenter UI only after the capability probe passes.

