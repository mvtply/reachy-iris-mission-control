from components.robot_io.robot import MockRobot
from settings import Settings


def test_testing_audio_is_muted_by_default(monkeypatch):
    monkeypatch.delenv("DEMO_MUTE_ROBOT", raising=False)
    assert Settings.from_env().mute_robot is True
    robot = MockRobot()
    robot.play_wav(b"any audio")
    assert robot.last_action == "speaker muted (mock)"


def test_voiced_presentation_requires_explicit_unmute(monkeypatch):
    monkeypatch.setenv("DEMO_MUTE_ROBOT", "false")
    assert Settings.from_env().mute_robot is False
