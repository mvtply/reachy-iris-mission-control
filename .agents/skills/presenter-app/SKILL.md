---
name: reachy-presenter-app
description: Change the local Redis-branded presenter screen and its interactive demo controls.
---

# Presenter app

Own `components/presenter_app/`. Keep component badges honest and readable for mixed business and technical audiences. The presenter controls registration, scripted scenes, questions, station changes, track override, and event deletion. Use Redis red `#FF4438` and the supplied Space fonts; avoid recreating a Redis logo.

When `audio_muted` is true, visibly show that state and never invoke browser speech synthesis. Clear displayed participant facts and disable controls after event deletion.

Verify the page in a browser, including a narrow viewport, keyboard focus, API errors, and the final deletion state. Do not print participant facts into browser logs.
