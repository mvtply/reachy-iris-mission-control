---
name: reachy-attention-manager
description: Change how Reachy selects, invites, follows, and hands off between audience members.
---

# Attention and handoff

Own `components/attention_manager/manager.py`. Consume `TrackedPerson` snapshots from `participant_tracking`; send motion intent only through `robot_io`. Keep the selected track locked through its conversation, even if another person crosses the view. After answer, decline, or timeout, mark that temporary track served and select another unserved track. On loss, pause pursuit and expose presenter override instead of silently switching.

Run `pytest tests/test_attention.py`. Physical three-person validation remains required in `OPEN_TASKS.md`.

