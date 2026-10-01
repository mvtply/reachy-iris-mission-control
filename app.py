from __future__ import annotations

import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from components.attention_manager.manager import AttentionManager
from components.demo_orchestrator.service import MissionControl
from components.redis_enterprise.client import connect, probe
from components.robot_io.robot import MockRobot, ReachyRobot
from contracts.models import TrackedPerson
from settings import Settings

ROOT = Path(__file__).parent
settings = Settings.from_env()
redis = connect(settings.redis_url)
robot_error = None
try:
    robot = ReachyRobot(muted=settings.mute_robot) if settings.robot_mode == "physical" else MockRobot(muted=settings.mute_robot)
except Exception as exc:
    robot_error = str(exc)
    robot = MockRobot(muted=settings.mute_robot)
attention = AttentionManager(robot)
mission = MissionControl(redis, settings, robot, attention)
vision_error = None
vision_ready = False
vision_stop = threading.Event()


def vision_loop() -> None:
    global vision_error, vision_ready
    try:
        from components.participant_tracking.tracker import PersonTracker
        roi = tuple(float(value.strip()) for value in settings.audience_roi.split(","))
        if len(roi) != 4 or not (0 <= roi[0] < roi[2] <= 1 and 0 <= roi[1] < roi[3] <= 1):
            raise ValueError("DEMO_AUDIENCE_ROI must be left,top,right,bottom fractions between 0 and 1")
        tracker = PersonTracker(settings.vision_model, roi)
        vision_ready = True
        while not vision_stop.is_set():
            frame = robot.get_frame()
            if frame is not None:
                attention.update(tracker.update(frame))
            attention.tick()
            vision_stop.wait(0.15)
    except Exception as exc:
        vision_error = str(exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    worker = None
    if settings.vision_mode == "rtdetr" and settings.robot_mode == "physical" and robot_error is None:
        worker = threading.Thread(target=vision_loop, name="reachy-vision", daemon=True)
        worker.start()
    yield
    vision_stop.set()
    if worker:
        worker.join(timeout=3)
    robot.close()


app = FastAPI(title="Reachy Mini: Redis Iris Mission Control", lifespan=lifespan)


def checked(call):
    try:
        return call()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Demo dependency unavailable: {exc}") from exc


class Registration(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    fact: str = Field(min_length=1, max_length=300)
    consent: bool


class Question(BaseModel):
    question: str = Field(min_length=1, max_length=500)
    participant_id: str | None = None
    identified_in_conversation: bool = False
    complete_turn: bool = True


class StationChange(BaseModel):
    status: str


class TrackSelection(BaseModel):
    track_id: int


class MockTracks(BaseModel):
    count: int = Field(ge=0, le=8)


@app.get("/")
def index():
    return FileResponse(ROOT / "components/presenter_app/index.html")


@app.get("/app.css")
def stylesheet():
    return FileResponse(ROOT / "components/presenter_app/app.css", media_type="text/css")


@app.get("/app.js")
def javascript():
    return FileResponse(ROOT / "components/presenter_app/app.js", media_type="application/javascript")


@app.get("/favicon.svg")
def favicon():
    return FileResponse(ROOT / "components/presenter_app/favicon.svg", media_type="image/svg+xml")


@app.get("/api/status")
def status():
    redis_status = probe(redis)
    native = {
        "Agent Memory": bool(settings.iris_agent_memory_url and settings.iris_agent_memory_store_id and settings.iris_agent_memory_api_key),
        "LangCache": bool(settings.iris_langcache_url and settings.iris_langcache_cache_id and settings.iris_langcache_api_key),
        "Context Retriever": bool(settings.iris_context_retriever_url and settings.iris_context_agent_key),
    }
    return {
        "event_id": settings.event_id,
        "redis": redis_status,
        "robot": "physical" if settings.robot_mode == "physical" and robot_error is None else "mock",
        "robot_error": robot_error,
        "robot_action": robot.last_action,
        "robot_speaking": robot.is_speaking,
        "robot_motion_loop_alive": robot.motion_loop_alive,
        "robot_motion_error": robot.motion_error,
        "robot_speech_motion_enabled": robot.speech_motion_enabled,
        "speaker_device": robot.speaker_device,
        "audio_muted": settings.mute_robot,
        "vision": "RT-DETR R18 + ByteTrack" if vision_ready and vision_error is None else "mock/off or loading",
        "vision_error": vision_error,
        "router": settings.router_mode,
        "router_service_configured": bool(settings.jev_url),
        "router_calls_verified": mission.router.verified,
        "router_error": mission.router.last_error,
        "native_iris_credentials_present": native,
        "native_iris_calls_verified": False,
        "hf_answer_configured": bool(settings.hf_answer_url),
        "hf_asr_configured": bool(settings.hf_asr_url),
        "hf_tts_configured": bool(settings.hf_tts_url),
        "tts_provider": "Hugging Face" if settings.hf_tts_url else "OpenAI" if settings.openai_api_key else None,
        "speaker_available": settings.robot_mode == "physical" and robot_error is None and bool(robot.speaker_device) and not settings.mute_robot and bool(settings.hf_tts_url or settings.openai_api_key),
        "event_closed": bool(redis.exists(mission.closed_key)) if redis_status["reachable"] else False,
    }


@app.post("/api/setup")
def setup():
    return checked(mission.setup)


@app.post("/api/register")
def register(body: Registration):
    return checked(lambda: mission.register(body.name, body.fact, body.consent))


@app.get("/api/participants")
def participants():
    return checked(mission.participants)


@app.post("/api/ask")
def ask(body: Question):
    if body.participant_id and not body.identified_in_conversation:
        raise HTTPException(status_code=400, detail="Ask the participant to identify themselves, then confirm that on the presenter screen")
    answer = checked(lambda: mission.ask(body.question, body.participant_id))
    speech = "muted for testing" if settings.mute_robot else "not configured"
    if (settings.hf_tts_url or settings.openai_api_key) and settings.robot_mode == "physical" and robot_error is None and not settings.mute_robot:
        try:
            robot.play_wav(mission.gateway.synthesize(answer.text))
            speech = "played on laptop"
        except Exception as exc:
            speech = f"failed: {exc}"
    if body.complete_turn:
        attention.complete()
    return {**answer.to_dict(), "speech": speech}


@app.post("/api/readback")
def readback(body: Registration):
    text = f"I heard {body.name.strip()} say: {body.fact.strip()}. Is that correct?"
    if (settings.hf_tts_url or settings.openai_api_key) and settings.robot_mode == "physical" and robot_error is None and not settings.mute_robot:
        return checked(lambda: (robot.play_wav(mission.gateway.synthesize(text)), {"text": text, "speech": "played on laptop"})[1])
    return {"text": text, "speech": "muted for testing" if settings.mute_robot else "presenter browser readback"}


@app.get("/api/board")
def board():
    return checked(mission.board.get)


@app.post("/api/board")
def change_board(body: StationChange):
    return checked(lambda: mission.update_station(body.status))


@app.get("/api/attention")
def get_attention():
    attention.tick()
    return attention.snapshot()


@app.post("/api/attention/select")
def select_track(body: TrackSelection):
    if not attention.select(body.track_id):
        raise HTTPException(status_code=404, detail="Track is no longer visible")
    return attention.snapshot()


@app.post("/api/attention/skip")
def skip_track():
    attention.skip()
    return attention.snapshot()


@app.post("/api/attention/next")
def next_track():
    attention.complete()
    return attention.snapshot()


@app.post("/api/mock/tracks")
def mock_tracks(body: MockTracks):
    if settings.robot_mode != "mock":
        raise HTTPException(status_code=400, detail="Mock tracks are only available in mock robot mode")
    tracks = [
        TrackedPerson(i + 1, (80 + i * 220, 80, 230 + i * 220, 400), (155 + i * 220, 145), 0.95, time.monotonic())
        for i in range(body.count)
    ]
    attention.update(tracks)
    attention.update(tracks)
    return attention.snapshot()


@app.post("/api/listen")
def listen():
    if not settings.hf_asr_url:
        raise HTTPException(status_code=409, detail="HF_ASR_URL is pending; use text input")
    return checked(lambda: {"text": mission.gateway.transcribe(robot.capture_wav(5))})


@app.post("/api/event/end")
def end_event():
    vision_stop.set()
    return checked(mission.end_event)
