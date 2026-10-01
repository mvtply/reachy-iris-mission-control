---
name: reachy-langcache
description: Change public-answer caching or add a verified native Redis LangCache integration.
---

# LangCache equivalent

Own `components/langcache/`. The current Redis-backed cache uses token similarity for public FAQ answers; call it a local similarity equivalent, not native semantic LangCache. `native.py` holds documented Data Plane calls but is inactive until a cache ID, endpoint, key, and event isolation/deletion are verified. Never cache participant facts or live station status. Local keys expire after 24 hours and are removed at event end.

If native LangCache access is supplied, verify cache creation, miss, hit, and deletion before changing the presenter label. Run `pytest tests/test_story.py`.
