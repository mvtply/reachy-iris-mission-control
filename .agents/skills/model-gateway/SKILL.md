---
name: reachy-model-gateway
description: Integrate or change Hugging Face recognition and answers or OpenAI speech output.
---

# Model gateway

Own `components/model_gateway/gateway.py`. Endpoint URLs and tokens are local environment values; do not put credentials in source or traces. The configured Hugging Face answer deployment uses OpenAI-compatible chat completions with `HF_ANSWER_MODEL`; the configured ASR deployment accepts raw WAV. OpenAI Speech API supplies WAV when `HF_TTS_URL` is blank, reading `OPENAI_API_KEY` or the existing `openai_secret`. Keep presenter text input and answer template available when endpoints are missing, and identify those modes in the UI.

When a service is provided, test an actual request and response, audio format for Reachy's speaker, timeout, and failure path before closing the corresponding `OPEN_TASKS.md` entry.
