"""Initialize the one-container, local-only Redis Enterprise trial.

Credentials are generated into an ignored 0600 file, never printed or passed in shell arguments.
"""
from __future__ import annotations

import json
import os
import secrets
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
SECRET = ROOT / ".secrets" / "enterprise-admin.json"
API = "https://127.0.0.1:19443"


def credentials() -> dict[str, str]:
    SECRET.parent.mkdir(exist_ok=True)
    if SECRET.exists():
        return json.loads(SECRET.read_text())
    data = {"username": "reachy-demo@localhost", "password": secrets.token_urlsafe(32)}
    fd = os.open(SECRET, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as stream:
        json.dump(data, stream)
    return data


def main() -> None:
    creds = credentials()
    with httpx.Client(verify=False, timeout=20) as client:
        for _ in range(30):
            try:
                response = client.get(API + "/v1/bootstrap")
                response.raise_for_status()
                break
            except httpx.HTTPError:
                time.sleep(2)
        else:
            raise RuntimeError("Redis Enterprise management API did not become ready")
        state = response.json()["bootstrap_status"]["state"]
        if state in {"idle", "error"}:
            response = client.post(API + "/v1/bootstrap/create_cluster", json={
                "action": "create_cluster",
                "cluster": {"name": "reachy-iris.local", "nodes": []},
                "credentials": creds,
            })
            response.raise_for_status()
            print("Cluster bootstrap accepted")
        elif state != "completed":
            print(f"Cluster bootstrap already in progress: {state}")
        for _ in range(90):
            response = client.get(API + "/v1/bootstrap", auth=(creds["username"], creds["password"]))
            response.raise_for_status()
            body = response.json()["bootstrap_status"]
            if body["state"] == "completed":
                break
            if body["state"] == "error":
                raise RuntimeError(f"Cluster bootstrap failed: {body.get('error_code')} {body.get('error_details')}")
            time.sleep(2)
        else:
            raise RuntimeError("Cluster bootstrap did not finish in three minutes")
        print("Cluster ready")
        auth = (creds["username"], creds["password"])
        response = client.get(API + "/v1/bdbs", auth=auth)
        response.raise_for_status()
        databases = response.json()
        if any(item.get("name") == "reachy-iris" for item in databases):
            print("Demo database already exists")
            return
        response = client.post(API + "/v1/bdbs", auth=auth, json={
            "name": "reachy-iris", "type": "redis", "memory_size": 268435456, "port": 12000,
        })
        response.raise_for_status()
        print("Demo database creation accepted")


if __name__ == "__main__":
    main()
