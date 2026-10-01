from components.attention_manager.manager import AttentionManager
from components.robot_io.robot import MockRobot
from contracts.models import TrackedPerson


def person(track_id: int) -> TrackedPerson:
    return TrackedPerson(track_id, (track_id * 100, 40, track_id * 100 + 80, 300), (track_id * 100 + 40, 90), 0.95, 0)


def test_attention_locks_and_hands_off_after_answer():
    robot = MockRobot()
    manager = AttentionManager(robot)
    manager.update([person(1), person(2), person(3)])
    manager.update([person(1), person(2), person(3)])
    assert manager.active_id == 1
    assert "wave" in robot.last_action

    manager.engage()
    manager.update([person(3), person(2), person(1)])
    assert manager.active_id == 1
    assert robot.aim == person(1).aim

    manager.complete()
    second = manager.active_id
    assert second in {2, 3}
    assert manager.served == {1}
    manager.skip()
    assert manager.active_id in ({2, 3} - {second})
    assert manager.served == {1, second}


def test_lost_target_does_not_switch_mid_turn(monkeypatch):
    clock = [100.0]
    monkeypatch.setattr("components.attention_manager.manager.time.monotonic", lambda: clock[0])
    robot = MockRobot()
    manager = AttentionManager(robot)
    manager.update([person(1), person(2)])
    manager.update([person(1), person(2)])
    manager.engage()
    manager.update([person(2)])
    clock[0] += 2.1
    manager.update([person(2)])
    assert manager.active_id == 1
    assert manager.state == "lost"
    assert robot.aim is None
    manager.update([person(1), person(2)])
    assert manager.active_id == 1
    assert manager.state == "engaged"
    manager.reset()
    manager.update([person(2)])
    assert manager.active_id is None
