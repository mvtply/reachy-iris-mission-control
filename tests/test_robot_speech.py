import io
import threading
import time
import wave

import numpy as np

from components.robot_io.robot import ReachyRobot, laptop_speaker


def wav_bytes(seconds=0.2, rate=16000):
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as writer:
        writer.setnchannels(1)
        writer.setsampwidth(2)
        writer.setframerate(rate)
        writer.writeframes(np.zeros(int(seconds * rate), dtype="<i2").tobytes())
    return buffer.getvalue()


def test_laptop_speaker_selection_skips_external_outputs():
    class Audio:
        def query_devices(self):
            return [
                {"name": "Reachy USB", "hostapi": 0, "max_output_channels": 2, "default_samplerate": 48000},
                {"name": "MacBook Pro Speakers", "hostapi": 0, "max_output_channels": 2, "default_samplerate": 48000},
            ]

        def query_hostapis(self, index):
            return {"name": "Core Audio"}

    assert laptop_speaker(Audio()) == (1, "MacBook Pro Speakers", 48000)


def test_audio_uses_laptop_device_and_marks_speaking_only_during_playback():
    robot = ReachyRobot.__new__(ReachyRobot)
    robot.np = np
    robot.muted = False
    robot._speaker_index = 4
    robot._speaker_rate = 16000
    robot.speaker_device = "MacBook Pro Speakers"
    robot._lock = threading.Lock()
    robot._audio_lock = threading.Lock()
    robot._speech_started = 0.0
    robot._speech_profile = []
    robot._sweep_started = 123.0
    robot.last_action = "ready"

    class Audio:
        def play(self, data, samplerate, device, blocking):
            assert data.shape == (3200, 1)
            assert samplerate == 16000
            assert device == 4
            assert blocking is True
            assert robot.is_speaking
            assert len(robot._speech_profile) == 1

    class Sway:
        def __init__(self, sample_rate):
            assert sample_rate == 16000

        def feed(self, mono):
            return [{"yaw_rad": 0.1}]

    robot.sd = Audio()
    robot._sway_class = Sway
    robot.mini = object()
    robot.play_wav(wav_bytes())
    assert not robot.is_speaking
    assert robot._speech_profile == []
    assert robot._sweep_started == 0.0
    assert robot.last_action == "speech complete"


def test_motion_loop_holds_tracking_pose_during_speech():
    from reachy_mini.utils import create_head_pose
    from reachy_mini.utils.interpolation import compose_world_offset

    robot = ReachyRobot.__new__(ReachyRobot)
    robot.np = np
    robot._create_head_pose = create_head_pose
    robot._compose_world_offset = compose_world_offset
    robot._speech_hop_seconds = 0.05
    robot._lock = threading.Lock()
    robot._target = (320, 240)
    robot._wave_started = 0.0
    robot._sweep_started = 0.0
    robot._speech_started = time.monotonic() - 0.05
    robot._speech_profile = [{"x_mm": 0, "y_mm": 0, "z_mm": 0, "roll_rad": 0.02, "pitch_rad": 0.03, "yaw_rad": 0.08}] * 20
    robot.motion_error = None
    robot.last_action = "ready"

    class OneTick:
        calls = 0

        def wait(self, interval):
            self.calls += 1
            return self.calls > 2

    class Mini:
        targets = []

        def look_at_image(self, x, y, perform_movement):
            assert (x, y) == (320, 240)
            return create_head_pose(yaw=12)

        def set_target(self, **kwargs):
            self.targets.append(kwargs)
            if len(self.targets) == 1:
                with robot._lock:
                    robot._target = None

    robot._stop = OneTick()
    robot.mini = Mini()
    robot._motion_loop()
    assert len(robot.mini.targets) == 2
    commanded = robot.mini.targets[0]
    assert "body_yaw" not in commanded
    assert not np.allclose(commanded["head"], create_head_pose(yaw=12))
    held = robot.mini.targets[1]
    assert "body_yaw" not in held
    assert np.allclose(held["head"], commanded["head"], atol=0.01)
    assert robot.motion_error is None
