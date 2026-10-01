from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    redis_url: str = "redis://localhost:12000/0"
    event_id: str = "mission-control-demo"
    robot_mode: str = "mock"
    mute_robot: bool = True
    router_mode: str = "rules"
    vision_mode: str = "off"
    vision_model: str = "PekingU/rtdetr_r18vd"
    audience_roi: str = "0,0,1,1"
    jev_model: str = "shgao/rsi-jev-v1.0-qwen3.5-0.8b"
    jev_url: str = ""
    jev_api_key: str = ""
    hf_answer_url: str = ""
    hf_answer_model: str = ""
    hf_asr_url: str = ""
    hf_tts_url: str = ""
    hf_api_token: str = ""
    openai_api_key: str = ""
    openai_tts_model: str = "gpt-4o-mini-tts"
    openai_tts_voice: str = "coral"
    iris_agent_memory_url: str = ""
    iris_agent_memory_store_id: str = ""
    iris_agent_memory_api_key: str = ""
    iris_langcache_url: str = ""
    iris_langcache_cache_id: str = ""
    iris_langcache_api_key: str = ""
    iris_context_retriever_url: str = ""
    iris_context_agent_key: str = ""

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(**{
            field: os.getenv("DEMO_" + field.upper(), getattr(cls, field))
            for field in ("redis_url", "event_id", "robot_mode", "router_mode", "vision_mode", "vision_model", "audience_roi", "jev_model", "jev_url", "jev_api_key")
        }, mute_robot=os.getenv("DEMO_MUTE_ROBOT", "true").strip().lower() not in {"0", "false", "no", "off"}, **{
            field: os.getenv(field.upper(), getattr(cls, field))
            for field in (
                "hf_answer_url", "hf_answer_model", "hf_asr_url", "hf_tts_url", "hf_api_token",
                "openai_tts_model", "openai_tts_voice",
                "iris_agent_memory_url", "iris_agent_memory_store_id", "iris_agent_memory_api_key",
                "iris_langcache_url", "iris_langcache_cache_id", "iris_langcache_api_key",
                "iris_context_retriever_url", "iris_context_agent_key",
            )
        }, openai_api_key=os.getenv("OPENAI_API_KEY") or os.getenv("openai_secret", ""))
