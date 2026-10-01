---
name: reachy-robot-io
description: Change Reachy Mini Lite camera, microphone, speaker, head, body, or antenna behavior in the demo.
---

# Robot I/O

Own `components/robot_io/robot.py`. Keep one motor-writing loop. Other components set an aim or request a gesture; they do not call `ReachyMini.set_target` directly. Disable daemon-side head tracking while application-side participant selection controls the head.

Audio is muted by default for testing (`DEMO_MUTE_ROBOT=true`). Keep `play_wav` silent in that mode, and do not enable browser narration while testing. Microphone input can still be checked. Only unmute for a voiced presentation after the physical speaker path is verified.

Read the current Reachy SDK motion and media API before changing hardware calls: https://github.com/pollen-robotics/reachy_mini/blob/main/docs/source/SDK/python-sdk.md. Verify any motor or audio change on the physical Lite before marking `OPEN_TASKS.md` complete. Mock mode is for rehearsal, not hardware proof.
