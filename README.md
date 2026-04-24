# how to use it

Example `docker-compose.yml`:

```yaml
services:
  influxdb:
    image: influxdb:2.7
    ports:
      - "127.0.0.1:8086:8086"
    environment:
      DOCKER_INFLUXDB_INIT_MODE: setup
      DOCKER_INFLUXDB_INIT_USERNAME: admin
      DOCKER_INFLUXDB_INIT_PASSWORD: replace-with-influxdb-password
      DOCKER_INFLUXDB_INIT_ORG: sams-scoreboard
      DOCKER_INFLUXDB_INIT_BUCKET: client-api
      DOCKER_INFLUXDB_INIT_ADMIN_TOKEN: replace-with-influxdb-token
    volumes:
      - ./influxdb/data:/var/lib/influxdb2

  client-api:
    build:
      context: ./client-api
    depends_on:
      - influxdb
    ports:
      - "127.0.0.1:8000:8000"
    environment:
      SERVER_CONFIG_PATH: /app/config/server_config.json
    volumes:
      - ./client-api/config/server_config.local.json:/app/config/server_config.json:ro
      - ./client-api/cache:/app/cache

  web:
    build:
      context: ./web
    depends_on:
      - client-api
    ports:
      - "127.0.0.1:8080:80"
    environment:
      API_BASE_URL: https://your-domain.com/api
```

This setup assumes you may run an external `nginx` on the host in front of these localhost-only container ports.

Example nginx site config:

```nginx
server {
  listen 80;
  server_name your-domain.com;

  location /api/ {
    proxy_pass http://127.0.0.1:8000/api/;
  }

  location / {
    proxy_pass http://127.0.0.1:8080/;
  }
}
```



# modules provided by this repo
## client-api

The `client-api` directory contains a FastAPI server for exposing competition data from the upstream SAMS API.

Context warm-up and maintenance:

* Read [`conecept.yml`](./conecept.yml) before starting work on `client-api` in a fresh Codex context
* Treat [`conecept.yml`](./conecept.yml) as the canonical high-level concept file for `client-api`
* Whenever `client-api` structure, behavior, environment variables, caching, live integration, or operational constraints change, update [`conecept.yml`](./conecept.yml) in the same workstream

Install dependencies:

```bash
cd client-api
pip install -r requirements.txt
```

Run the API server:

```bash
cd client-api
SERVER_CONFIG_PATH=./config/server_config.local.json \
uvicorn server:app --host 0.0.0.0 --port 8000
```

Runtime configuration:

* `SERVER_CONFIG_PATH` is required and must point to the JSON config file used by `client-api`
* startup fails immediately if the config file is missing, invalid JSON, or missing required keys
* the config file contains `host`, `port`, `log_level`, `tz`, `write_raw_cache`, `influxdb`, `ssvb_api_key`, `live_api_urls`, and `live_api_snapshot_refresh_seconds`
* `influxdb` is a nested object with `enabled`, `url`, `org`, `bucket`, `token`, and `timeout_seconds`
* defaults still apply for `host`, `port`, `log_level`, `write_raw_cache`, `influxdb.enabled`, `influxdb.timeout_seconds`, and `live_api_snapshot_refresh_seconds` when omitted from the file

Configuration files:

* [`client-api/config/server_config_template.json`](./client-api/config/server_config_template.json) contains the full anonymous config schema for `client-api`
* create a real config file such as `client-api/config/server_config.local.json` from that template and point `SERVER_CONFIG_PATH` at it
* [`docker-compose.yml.example`](./docker-compose.yml.example) contains the same `influxdb`, `client-api`, and `web` example
* the config file supports `tz`, which is applied as the process timezone
* `write_raw_cache` controls whether `*-raw.json` cache files are written; it defaults to `false`
* the InfluxDB config is optional; when enabled, `client-api` writes best-effort request metrics without affecting API responses if InfluxDB is unavailable
* required config keys are `ssvb_api_key` and `live_api_urls`
* `API_BASE_URL` for the `web` container must be a browser-reachable URL, not an internal Docker service hostname, because it is injected into client-side JavaScript

Endpoints:

* `GET /api/health` returns `{ "status": "ok", "requestId": ... }`
* `GET /api/healthz` returns `{ "status": "ok", "requestId": ... }`
* `GET /api/competition/<uuid>` returns the competition payload as JSON
* `GET /api/competition-list` returns `{ "data": [...], "requestId": ... }`
* `GET /api/live/<uuid>` returns the same payload shape, filtered server-side to one competition
* `GET /docs` serves the Swagger UI
* `GET /redoc` serves the ReDoc UI

Example:

```bash
curl http://127.0.0.1:8000/api/competition/<uuid>
curl http://127.0.0.1:8000/api/competition-list
curl "http://127.0.0.1:8000/api/live/<uuid>"
curl http://127.0.0.1:8000/api/healthz
curl http://127.0.0.1:8000/docs
```

Load test with `k6`:

```bash
k6 run load-tests/simple.js
./load-tests/run-simple.sh
```

Useful environment variables:

* `BASE_URL` defaults to `http://127.0.0.1:8000`
* `COMPETITION_ID` enables `GET /api/competition/<uuid>` and `GET /api/live/<uuid>` in each iteration
* `SLEEP_SECONDS` defaults to `1`

Each test iteration requests:

* `GET /api/healthz`
* `GET /api/competition-list`
* optionally `GET /api/competition/<uuid>` and `GET /api/live/<uuid>` when `COMPETITION_ID` is set

Examples:

```bash
k6 run load-tests/simple.js
./load-tests/run-simple.sh
BASE_URL=http://127.0.0.1:8000 COMPETITION_ID=<uuid> k6 run load-tests/simple.js
BASE_URL=http://127.0.0.1:8000 COMPETITION_ID=<uuid> SLEEP_SECONDS=0.2 k6 run load-tests/simple.js
./load-tests/run-simple.sh --vus 20 --duration 30s
```

## web

The `web` directory contains the Vite frontend.

Install dependencies:

```bash
cd web
npm install
```

Run the frontend:

```bash
cd web
npm run dev
```

Configure the frontend API base URL for local development with `VITE_API_BASE_URL`:

```bash
cd web
VITE_API_BASE_URL=https://your-api.example/api npm run dev
```

If `VITE_API_BASE_URL` is not set during local development, the frontend defaults to:

```text
http://localhost:8000/api
```

For Docker/runtime deployments, the frontend reads `API_BASE_URL` when the container starts and writes it into `/app-config.js`. The live feed is loaded from the same base URL at the `/live` endpoint. Example:

```bash
docker run \
  -e API_BASE_URL=https://your-api.example/api \
  -p 8080:80 <image>
```

If `API_BASE_URL` is not set in the container, the runtime default is:

```text
http://localhost:8000/api
```

# docs
## wiki

* https://wiki.sams-server.de/wiki/REST-API-Schnittstelle

note: REST API requires an API key provided by the responsible association

```
{
  "_links": {
    "self": {
      "href": "https://www.ssvb.org/api/v2/"
    },
    "swagger": {
      "href": "https://www.ssvb.org/api/v2/swagger.json"
    },
    "associations": {
      "href": "https://www.ssvb.org/api/v2/associations"
    },
    "seasons": {
      "href": "https://www.ssvb.org/api/v2/seasons"
    },
    "teams": {
      "href": "https://www.ssvb.org/api/v2/teams"
    },
    "leagues": {
      "href": "https://www.ssvb.org/api/v2/leagues"
    },
    "match_groups": {
      "href": "https://www.ssvb.org/api/v2/match-groups"
    },
    "event_types": {
      "href": "https://www.ssvb.org/api/v2/event-types"
    },
    "competitions": {
      "href": "https://www.ssvb.org/api/v2/competitions"
    },
    "committees": {
      "href": "https://www.ssvb.org/api/v2/committees"
    },
    "league_hierarchies": {
      "href": "https://www.ssvb.org/api/v2/league-hierarchies"
    },
    "user_details": {
      "href": "https://www.ssvb.org/api/v2/user-details"
    },
    "league_matches": {
      "href": "https://www.ssvb.org/api/v2/league-matches"
    },
    "super_competitions": {
      "href": "https://www.ssvb.org/api/v2/super-competitions"
    },
    "competition_matches": {
      "href": "https://www.ssvb.org/api/v2/competition-matches"
    },
    "sportsclubs": {
      "href": "https://www.ssvb.org/api/v2/sportsclubs"
    },
    "match_days": {
      "href": "https://www.ssvb.org/api/v2/match-days"
    },
    "locations": {
      "href": "https://www.ssvb.org/api/v2/locations"
    },
    "events": {
      "href": "https://www.ssvb.org/api/v2/events"
    }
  }
}
```

## sams live ticker

* https://backend.sams-ticker.de/live/indoor/tickers/dvv
* https://backend.sams-ticker.de/live/indoor/tickers/ssvb

front end 
* https://dvv.sams-ticker.de/
* https://ssvb.sams-ticker.de/
