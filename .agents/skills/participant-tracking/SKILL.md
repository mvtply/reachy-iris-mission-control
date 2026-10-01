---
name: reachy-participant-tracking
description: Maintain Reachy Mini camera person detection and temporary track IDs when changing audience tracking behavior.
---

# Participant tracking

Own `components/participant_tracking/`. Read `contracts/models.py` for `TrackedPerson` before changing its output. This component detects people with RT-DETR R18, associates boxes with ByteTrack, and refines the aim point with a local face detector. It does not recognize identities or store frames.

Keep heavy model imports lazy so text rehearsal still starts without vision dependencies. Run `pytest tests/test_attention.py` after changing track output, then rehearse with physical Reachy because prerecorded frames cannot prove motor behavior. Current SDK camera and motion interfaces are documented at https://github.com/pollen-robotics/reachy_mini/blob/main/docs/source/SDK/python-sdk.md.
