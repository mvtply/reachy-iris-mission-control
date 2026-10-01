---
name: reachy-redis-enterprise
description: Operate or change the local Redis Enterprise Docker cluster and database for the Reachy Iris demo.
---

# Local Redis Enterprise

Own `compose.yaml` and `components/redis_enterprise/`. The container is development-only and binds management and database ports to localhost. Bootstrap generates an ignored admin credential file with mode 0600. Do not print it or pass it through a shell argument. `README.md` has setup commands.

Verify `PING`, `JSON.SET`/`JSON.GET`, and `FT.CREATE`/`FT.SEARCH` on port 12000. Check existing containers and ports before changing Compose. Do not add PostgreSQL; the ingestion scene is implemented in `rdi_simulator`.

