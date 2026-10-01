# Running and retiring the demo

## Local rehearsal

Use Python 3.12 and Docker Desktop. From the repository root:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -e '.[test]'
cp .env.example .env
docker compose up -d
.venv/bin/python -m components.redis_enterprise.bootstrap
set -a; source .env; set +a
.venv/bin/uvicorn app:app --host 127.0.0.1 --port 8765
```

Open `http://127.0.0.1:8765`; the presenter seeds the mission when Redis is available. Use **Simulate three people** to rehearse. The default is a mock robot, muted audio, rules routing, and no camera model. Install `.[vision,test]` only when you need the physical robot and local detector. The optional RSI-Jev setup is in the root README.

The bootstrap creates a local Enterprise database at port 12000. Its generated admin credential is stored in `.secrets/enterprise-admin.json`, which is ignored by Git. `.env` is ignored too. Keep both files local, owner-readable, and out of screenshots or issue reports. Never commit model weights, audio recordings, participant facts, or browser traces.

## Optional services

Start from `.env.example`. The relevant groups are:

| Group | Variables | Effect |
| --- | --- | --- |
| Robot and vision | `DEMO_ROBOT_MODE`, `DEMO_MUTE_ROBOT`, `DEMO_VISION_MODE`, `DEMO_VISION_MODEL`, `DEMO_AUDIENCE_ROI` | Physical Reachy and temporary person tracking |
| Local router | `DEMO_ROUTER_MODE`, `DEMO_JEV_URL`, `DEMO_JEV_API_KEY` | Typed RSI-Jev choice service |
| Hosted answer and ASR | `HF_ANSWER_URL`, `HF_ANSWER_MODEL`, `HF_ASR_URL`, `HF_API_TOKEN` | Answer generation and speech recognition |
| Speech output | `HF_TTS_URL` or `OPENAI_API_KEY`, plus optional `OPENAI_TTS_MODEL`, `OPENAI_TTS_VOICE` | Audio through the MacBook's built-in speakers |
| Managed Iris placeholders | `IRIS_AGENT_MEMORY_*`, `IRIS_LANGCACHE_*`, `IRIS_CONTEXT_*` | Native adapter configuration only; the app still runs local equivalents |

Use `DEMO_MUTE_ROBOT=true` during setup and testing. Set it to `false` only for a voiced presentation. `/api/listen` records five seconds of microphone audio and sends it to the configured ASR service; use it only when participants know a recording is being made. No raw camera frames are stored.

## Finish and clean up

1. In the presenter, choose **End event and delete its data**. Verify the returned `deleted_event_keys` count and `event_closed=true`. This deletes local event keys, not any managed Iris data.
2. Stop the presenter and optional router processes with their normal terminal interrupt. Stop the Reachy daemon and put the robot to sleep using the Reachy SDK's supported shutdown path.
3. Run `docker compose down` to stop the local Enterprise container. Add `-v` only when you intend to permanently erase its local database volume.
4. If you provisioned managed Redis Cloud or Hugging Face resources, delete each by its exact ID in those services' consoles and verify it disappears from the resource list. Deleting the local container does not remove cloud resources, and deleting a shared cloud database can affect unrelated workloads.

The source tree can be published because `.env`, `.secrets/`, `.cache/`, recordings, and build artifacts are ignored. Before any public push, review `git status` and the staged diff for credentials and account-specific data.
