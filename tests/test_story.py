import os
import uuid

import pytest
from redis import Redis

from components.attention_manager.manager import AttentionManager
from components.demo_orchestrator.service import MissionControl
from components.robot_io.robot import MockRobot
from settings import Settings


@pytest.fixture
def live_demo():
    client = Redis.from_url(os.environ.get("DEMO_REDIS_URL", "redis://localhost:12000/0"), decode_responses=True)
    try:
        client.ping()
        client.execute_command("MODULE", "LIST")
    except Exception as exc:
        pytest.skip(f"local Redis Enterprise not available: {exc}")
    settings = Settings(redis_url=os.environ.get("DEMO_REDIS_URL", "redis://localhost:12000/0"), event_id="test-" + uuid.uuid4().hex)
    robot = MockRobot()
    demo = MissionControl(client, settings, robot, AttentionManager(robot))
    demo.setup()
    yield demo
    if not client.exists(demo.closed_key):
        demo.end_event()
    client.delete(demo.closed_key)


def test_story_memory_cache_citations_board_and_deletion(live_demo):
    demo = live_demo
    maya = demo.register("Maya", "I love astronomy", True)
    leo = demo.register("Leo", "I build tiny robots", True)
    assert demo.memory.by_id(maya["id"])["fact"] == "I love astronomy"
    assert demo.memory.by_id(leo["id"])["fact"] == "I build tiny robots"
    assert demo.ask("What do you remember about me?", maya["id"]).text.find("astronomy") >= 0
    assert "astronomy" not in demo.ask("What do you remember about me?", leo["id"]).text

    first = demo.ask("What does Redis Iris help an agent do?")
    second = demo.ask("What does Redis Iris help an agent do?")
    assert not first.cache_hit and second.cache_hit
    assert second.text == first.text

    rule = demo.ask("What is the priority delivery rule?")
    assert any(item.provenance == "Mission Handbook §3" for item in rule.evidence)
    assert demo.update_station("CLOSED")["status"] == "CLOSED"
    finale = demo.ask("Combine what you remember about me with the priority rule and charging status.", leo["id"])
    assert "tiny robots" in finale.text
    assert "priority delivery" in finale.text
    assert "Charging station is CLOSED." in finale.text
    assert any("simulated RDI" in item.provenance for item in finale.evidence)

    participant_key = demo.memory.prefix + "participant:" + maya["id"]
    assert demo.redis.exists(participant_key)
    result = demo.end_event()
    assert result["deleted_event_keys"] > 0
    assert not demo.redis.exists(participant_key)
    assert not demo.redis.exists(demo.board.key)
    with pytest.raises(ValueError, match="ended"):
        demo.ask("What is the rule?")
