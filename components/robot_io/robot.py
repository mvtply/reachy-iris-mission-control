from __future__ import annotations

import io
import threading
import time
import wave


def laptop_speaker(sd) -> tuple[int, str, int]:
    """Select the built-in MacBook output, never a USB, HDMI, or virtual device."""
    for index, device in enumerate(sd.query_devices()):
        name = str(device["name"])
        host = sd.query_hostapis(device["hostapi"])["name"]
        built_in = (name.startswith("MacBook ") and name.endswith(" Speakers")) or name in {
            "Built-in Output", "Internal Speakers"
        }
        if host == "Core Audio" and built_in and device["max_output_channels"] > 0:
            return index, name, round(device["default_samplerate"])
    raise RuntimeError("MacBook built-in speakers are unavailable")


class MockRobot:
    def __init__(self, muted: bool = True):
        self.muted = muted
        self.last_action = "ready (mock robot)"
        self.aim = None

    def aim_at(self, pixel: tuple[int, int]) -> None:
        self.aim = pixel
        self.last_action = f"face participant at pixel {pixel} (mock)"

    def clear_aim(self) -> None:
        self.aim = None
        self.last_action = "neutral pose (mock)"

    def wave(self) -> None:
        self.last_action = "antenna invitation wave (mock)"

    def sweep(self) -> None:
        self.last_action = "audience sweep (mock)"

    def get_frame(self):
        return None

    def capture_wav(self, seconds: float = 5) -> bytes:
        raise RuntimeError("Physical Reachy Mini microphone is unavailable in mock mode")

    def play_wav(self, wav_bytes: bytes) -> None:
        self.last_action = "speaker muted (mock)" if self.muted else "played synthesized speech (mock)"

    @property
    def is_speaking(self) -> bool:
        return False

    @property
    def motion_loop_alive(self) -> bool:
        return False

    motion_error = None
    speech_motion_enabled = False
    speaker_device = None

    def close(self) -> None:
        pass


class ReachyRobot:
    """All motor writes are serialized in one loop; vision only sets a target pixel."""

    def __init__(self, muted: bool = True):
        import numpy as np
        import sounddevice as sd
        from reachy_mini import ReachyMini
        from reachy_mini.utils import create_head_pose
        from reachy_mini.utils.interpolation import compose_world_offset
        from reachy_mini.motion.speech_tapper import HOP_MS, SwayRollRT

        self.np = np
        self.sd = sd
        self._create_head_pose = create_head_pose
        self._compose_world_offset = compose_world_offset
        self._sway_class = SwayRollRT
        self._speech_hop_seconds = HOP_MS / 1000
        self.muted = muted
        self.mini = ReachyMini(media_backend="default", automatic_body_yaw=True)
        self.mini.stop_head_tracking()
        self.mini.enable_motors()
        self._speaker_index, self.speaker_device, self._speaker_rate = laptop_speaker(sd)
        self.speech_motion_enabled = not muted
        self._lock = threading.Lock()
        self._audio_lock = threading.Lock()
        self._stop = threading.Event()
        self._target: tuple[int, int] | None = None
        self._wave_started = 0.0
        self._sweep_started = 0.0
        self._speech_started = 0.0
        self._speech_profile: list[dict[str, float]] = []
        self.motion_error: str | None = None
        self.last_action = "ready (physical Reachy Mini)"
        self._thread = threading.Thread(target=self._motion_loop, name="reachy-motion", daemon=True)
        self._thread.start()

    def aim_at(self, pixel: tuple[int, int]) -> None:
        with self._lock:
            self._target = pixel

    def clear_aim(self) -> None:
        with self._lock:
            self._target = None

    def wave(self) -> None:
        with self._lock:
            self._wave_started = time.monotonic()
            self.last_action = "antenna invitation wave"

    def sweep(self) -> None:
        with self._lock:
            if self._target is None and not self._speech_started:
                self._sweep_started = time.monotonic()
                self.last_action = "slow audience sweep"

    @property
    def is_speaking(self) -> bool:
        with self._lock:
            return self._speech_started > 0

    @property
    def motion_loop_alive(self) -> bool:
        return self._thread.is_alive()

    def _motion_loop(self) -> None:
        last_pixel = None
        last_base_pose = None
        try:
            while not self._stop.wait(0.1):
                with self._lock:
                    target, wave_started, sweep_started = self._target, self._wave_started, self._sweep_started
                    speech_started = self._speech_started
                    speech_profile = self._speech_profile
                elapsed = time.monotonic() - wave_started
                antenna_angle = 0.0
                if wave_started and elapsed < 1.2:
                    antenna_angle = 0.30 if int(elapsed / 0.2) % 2 == 0 else -0.30
                antennas = self.np.array([antenna_angle, -antenna_angle])
                speaking = speech_started > 0
                speech_sample = None
                if speaking:
                    index = int((time.monotonic() - speech_started) / self._speech_hop_seconds)
                    if 0 <= index < len(speech_profile):
                        speech_sample = speech_profile[index]
                if target:
                    # Exponential smoothing limits abrupt jumps from detector jitter.
                    last_pixel = target if last_pixel is None else (
                        int(0.65 * last_pixel[0] + 0.35 * target[0]),
                        int(0.65 * last_pixel[1] + 0.35 * target[1]),
                    )
                    pose = self.mini.look_at_image(*last_pixel, perform_movement=False)
                    last_base_pose = pose
                elif speaking:
                    # Hold the previous participant-facing pose if tracking pauses mid-answer.
                    pose = last_base_pose if last_base_pose is not None else self.np.eye(4)
                elif sweep_started and time.monotonic() - sweep_started < 4.5:
                    phase = (time.monotonic() - sweep_started) / 4.5
                    yaw = self.np.deg2rad(-55 + 110 * phase)
                    self.mini.set_target(head=self.np.eye(4), body_yaw=float(yaw), antennas=antennas)
                    continue
                else:
                    last_pixel = None
                    last_base_pose = None
                    self.mini.set_target(head=self.np.eye(4), body_yaw=0.0, antennas=antennas)
                    continue
                if speech_sample is not None:
                    offset = self._create_head_pose(
                        x=speech_sample["x_mm"], y=speech_sample["y_mm"], z=speech_sample["z_mm"],
                        roll=speech_sample["roll_rad"], pitch=speech_sample["pitch_rad"],
                        yaw=speech_sample["yaw_rad"], mm=True, degrees=False,
                    )
                    pose = self._compose_world_offset(pose, offset)
                self.mini.set_target(head=pose, antennas=antennas)
        except Exception as exc:
            self.motion_error = str(exc)
            self.last_action = f"motion error: {exc}"

    def get_frame(self):
        return self.mini.media.get_frame()

    def capture_wav(self, seconds: float = 5) -> bytes:
        np = self.np
        self.mini.media.start_recording()
        samples = []
        deadline = time.monotonic() + seconds
        try:
            while time.monotonic() < deadline:
                chunk = self.mini.media.get_audio_sample()
                if chunk is not None and len(chunk):
                    samples.append(chunk)
                time.sleep(0.05)
        finally:
            self.mini.media.stop_recording()
        if not samples:
            raise RuntimeError("Reachy microphone returned no audio")
        audio = np.concatenate(samples, axis=0)
        pcm = (np.clip(audio, -1, 1) * 32767).astype("<i2")
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as writer:
            writer.setnchannels(pcm.shape[1] if pcm.ndim == 2 else 1)
            writer.setsampwidth(2)
            writer.setframerate(self.mini.media.get_input_audio_samplerate())
            writer.writeframes(pcm.tobytes())
        return buffer.getvalue()

    def play_wav(self, wav_bytes: bytes) -> None:
        if self.muted:
            self.last_action = "speaker muted"
            return
        np = self.np
        with wave.open(io.BytesIO(wav_bytes), "rb") as reader:
            if reader.getsampwidth() != 2:
                raise RuntimeError("TTS endpoint must return 16-bit PCM WAV")
            channels, source_rate = reader.getnchannels(), reader.getframerate()
            data = np.frombuffer(reader.readframes(reader.getnframes()), dtype="<i2").astype(np.float32) / 32768
        data = data.reshape((-1, channels))
        target_rate = self._speaker_rate
        if source_rate != target_rate:
            new_length = round(len(data) * target_rate / source_rate)
            x_old = np.linspace(0, 1, len(data), endpoint=False)
            x_new = np.linspace(0, 1, new_length, endpoint=False)
            data = np.column_stack([np.interp(x_new, x_old, data[:, i]) for i in range(channels)]).astype(np.float32)
        if channels > 2:
            data = data[:, :2]
        mono = data.mean(axis=1).astype(np.float32)
        profile = self._sway_class(sample_rate=target_rate).feed(mono)
        with self._audio_lock:
            try:
                with self._lock:
                    self._speech_started = time.monotonic()
                    self._speech_profile = profile
                    self._sweep_started = 0.0
                    self.last_action = f"speaking through {self.speaker_device}"
                self.sd.play(data, samplerate=target_rate, device=self._speaker_index, blocking=True)
            finally:
                with self._lock:
                    self._speech_started = 0.0
                    self._speech_profile = []
                    self.last_action = "speech complete"

    def close(self) -> None:
        self._stop.set()
        self._thread.join(timeout=3)
        self.mini.stop_head_tracking()
        self.mini.__exit__(None, None, None)
