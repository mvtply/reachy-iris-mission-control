from __future__ import annotations

import io
import wave

import httpx
from contracts.models import Evidence
from settings import Settings


class ModelGateway:
    def __init__(self, settings: Settings):
        self.settings = settings

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.settings.hf_api_token}"} if self.settings.hf_api_token else {}

    def answer(self, question: str, evidence: list[Evidence], participant: dict | None) -> tuple[str, str]:
        if self.settings.hf_answer_url:
            prompt = (
                "Answer the user's mission question concisely using only the evidence below. "
                "Cite source titles in brackets. Do not infer identity from camera tracking. "
                "If an opt-in fact is provided, include that exact fact phrase in the answer. "
                "If a live station status is provided, state its exact current value.\n"
                + "\n".join(f"[{e.title}] {e.text} ({e.provenance})" for e in evidence)
                + (f"\nOpt-in participant fact: {participant['name']}: {participant['fact']}" if participant else "")
                + f"\nQuestion: {question}\nAnswer:"
            )
            try:
                with httpx.Client(timeout=20) as client:
                    if self.settings.hf_answer_model:
                        response = client.post(
                            self.settings.hf_answer_url.rstrip("/") + "/v1/chat/completions",
                            headers=self._headers(),
                            json={
                                "model": self.settings.hf_answer_model,
                                "messages": [{"role": "user", "content": prompt}],
                                "max_tokens": 240,
                                "temperature": 0.2,
                                "chat_template_kwargs": {"enable_thinking": False},
                            },
                        )
                    else:
                        response = client.post(self.settings.hf_answer_url, headers=self._headers(), json={"inputs": prompt})
                    response.raise_for_status()
                    payload = response.json()
                if isinstance(payload, dict) and payload.get("choices"):
                    text = payload["choices"][0].get("message", {}).get("content")
                else:
                    if isinstance(payload, list):
                        payload = payload[0]
                    text = payload.get("generated_text") or payload.get("text") or payload.get("answer")
                if text:
                    if text.startswith(prompt):
                        text = text[len(prompt):]
                    if "</think>" in text:
                        text = text.split("</think>", 1)[1]
                    if "<think>" in text:
                        text = ""
                    if text.strip():
                        additions = []
                        if participant and participant["fact"].casefold() not in text.casefold():
                            additions.append(f"{participant['name']}, I remember that {participant['fact']}.")
                        priority = next((item for item in evidence if item.source_id == "priority"), None)
                        if participant and priority and priority.provenance not in text:
                            additions.append(f"{priority.text} [{priority.provenance}]")
                        live = next((item for item in evidence if item.source_id == "charging-live"), None)
                        if live and "CLOSED" in live.text and "CLOSED" not in text:
                            additions.append(f"{live.text} [{live.provenance}]")
                        if additions:
                            return " ".join(additions + [text.strip()]), "hosted Hugging Face answer + confirmed-data guardrail"
                        return text.strip(), "hosted Hugging Face answer endpoint"
            except Exception as exc:
                return self._template(evidence, participant), f"local answer template (HF {type(exc).__name__})"
        return self._template(evidence, participant), "local answer template (HF endpoint pending)"

    @staticmethod
    def _template(evidence: list[Evidence], participant: dict | None) -> str:
        parts = []
        if participant:
            parts.append(f"{participant['name']}, I remember that {participant['fact']}.")
        live = next((item for item in evidence if item.source_id == "charging-live"), None)
        priority = next((item for item in evidence if item.source_id == "priority"), None)
        if participant and live:
            selected = [item for item in (priority, live) if item]
        elif live:
            selected = [live] + [item for item in evidence if item.source_id != "charging-live"][:1]
        else:
            selected = evidence[:2]
        for item in selected:
            parts.append(f"{item.text} [{item.provenance}]")
        return " ".join(parts) if parts else "I do not have enough mission evidence to answer that yet."

    def transcribe(self, wav_bytes: bytes) -> str:
        if not self.settings.hf_asr_url:
            raise RuntimeError("HF_ASR_URL is not configured; use presenter text input")
        with httpx.Client(timeout=30) as client:
            response = client.post(self.settings.hf_asr_url, headers={**self._headers(), "Content-Type": "audio/wav"}, content=wav_bytes)
            response.raise_for_status()
            data = response.json()
        return str(data.get("text") or data.get("transcription") or "").strip()

    def synthesize(self, text: str) -> bytes:
        if self.settings.hf_tts_url:
            url = self.settings.hf_tts_url
            headers = self._headers()
            body = {"inputs": text}
        elif self.settings.openai_api_key:
            url = "https://api.openai.com/v1/audio/speech"
            headers = {"Authorization": f"Bearer {self.settings.openai_api_key}"}
            body = {
                "model": self.settings.openai_tts_model,
                "voice": self.settings.openai_tts_voice,
                "input": text,
                "instructions": "Speak clearly and warmly as a friendly small robot presenting a live demo.",
                "response_format": "wav",
            }
        else:
            raise RuntimeError("No speech output service is configured")
        with httpx.Client(timeout=30) as client:
            response = client.post(url, headers=headers, json=body)
            response.raise_for_status()
        try:
            with wave.open(io.BytesIO(response.content), "rb") as reader:
                if reader.getsampwidth() != 2:
                    raise ValueError("Expected nonempty 16-bit PCM WAV")
                channels, rate = reader.getnchannels(), reader.getframerate()
                pcm = reader.readframes(reader.getnframes())
                if not pcm:
                    raise ValueError("Expected nonempty 16-bit PCM WAV")
        except (wave.Error, EOFError, ValueError) as exc:
            raise RuntimeError("Speech service did not return playable 16-bit PCM WAV") from exc
        canonical = io.BytesIO()
        with wave.open(canonical, "wb") as writer:
            writer.setnchannels(channels)
            writer.setsampwidth(2)
            writer.setframerate(rate)
            writer.writeframes(pcm)
        return canonical.getvalue()
