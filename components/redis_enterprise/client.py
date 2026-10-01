from __future__ import annotations

from redis import Redis


def connect(url: str) -> Redis:
    return Redis.from_url(url, decode_responses=True, socket_connect_timeout=2, socket_timeout=3)


def probe(client: Redis) -> dict[str, object]:
    try:
        pong = bool(client.ping())
        modules = client.execute_command("MODULE", "LIST")
        names = []
        for module in modules:
            fields = dict(zip(module[::2], module[1::2]))
            names.append(str(fields.get("name", "")).lower())
        return {"reachable": pong, "modules": names, "search_json_ready": "search" in names and "rejson" in names}
    except Exception as exc:
        return {"reachable": False, "error": str(exc)}
