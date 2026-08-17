# how to use it

## API 1.0 Docker Compose example

Example `docker-compose.yml` for API 1.0, InfluxDB, and the web 1.0 frontend:

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
      DOCKER_INFLUXDB_INIT_BUCKET: api-1.0
      DOCKER_INFLUXDB_INIT_ADMIN_TOKEN: replace-with-influxdb-token
    volumes:
      - ./influxdb/data:/var/lib/influxdb2

  api-1.0:
    build:
      context: ./api-1.0
    depends_on:
      - influxdb
    ports:
      - "127.0.0.1:8000:8000"
    environment:
      SERVER_CONFIG_PATH: /app/config/server_config.json
    volumes:
      - ./api-1.0/config/server_config.local.json:/app/config/server_config.json:ro
      - ./api-1.0/cache:/app/cache

  web-1.0:
    build:
      context: ./web-1.0
    depends_on:
      - api-1.0
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
## api-1.0

The `api-1.0` directory contains a FastAPI server for exposing competition data from the upstream SAMS API.

Context warm-up and maintenance:

* Read [`concept.yml`](./api-1.0/concept.yml) before starting work on `api-1.0` in a fresh Codex context
* Treat [`concept.yml`](./api-1.0/concept.yml) as the canonical high-level concept file for `api-1.0`
* Whenever `api-1.0` structure, behavior, environment variables, caching, live integration, or operational constraints change, update [`concept.yml`](./api-1.0/concept.yml) in the same workstream

Install dependencies:

```bash
cd api-1.0
pip install -r requirements.txt
```

Run the API server:

```bash
cd api-1.0
SERVER_CONFIG_PATH=./config/server_config.local.json \
uvicorn server:app --host 0.0.0.0 --port 8000
```

Runtime configuration:

* `SERVER_CONFIG_PATH` defaults to `/app/config/server_config.json` and can be overridden when needed
* startup fails immediately if the config file is missing, invalid JSON, or missing required keys
* the config file contains `host`, `port`, `log_level`, `tz`, `write_raw_cache`, `influxdb`, `ssvb_api_key`, `ssvb_api_url`, `live_api_urls`, and `live_api_snapshot_refresh_seconds`
* `influxdb` is a nested object with `enabled`, `url`, `org`, `bucket`, `token`, and `timeout_seconds`
* defaults still apply for `host`, `port`, `log_level`, `write_raw_cache`, `influxdb.enabled`, `influxdb.timeout_seconds`, and `live_api_snapshot_refresh_seconds` when omitted from the file

Configuration files:

* [`api-1.0/config/server_config_template.json`](./api-1.0/config/server_config_template.json) contains the full anonymous config schema for `api-1.0`
* create a real config file such as `api-1.0/config/server_config.local.json` from that template and point `SERVER_CONFIG_PATH` at it
* [`docker-compose.yml.example`](./docker-compose.yml.example) contains the same `influxdb`, `api-1.0`, and `web-1.0` example
* the config file supports `tz`, which is applied as the process timezone
* `write_raw_cache` controls whether `*-raw.json` cache files are written; it defaults to `false`
* the InfluxDB config is optional; when enabled, `api-1.0` writes best-effort request metrics without affecting API responses if InfluxDB is unavailable
* required config keys are `ssvb_api_key`, `ssvb_api_url`, and `live_api_urls`
* `API_BASE_URL` for the `web-1.0` container must be a browser-reachable URL, not an internal Docker service hostname, because it is injected into client-side JavaScript

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

## api-2.0

`api-2.0` is a two-stage SAMS-data service. A background synchronizer mirrors every
season into SQLite; its HTTP routes read only from that local database.
This prevents a user request from triggering a chain of upstream SAMS calls.

```bash
cd api-2.0
pip install -r requirements.txt
cp config/server_config_template.json config/server_config.local.json
# Set ssvb_api_key in config/server_config.local.json.
SERVER_CONFIG_PATH=config/server_config.local.json python server.py
```

### API 2.0 Docker Compose starter

Create `api-2.0/config/server_config.local.json` from the template and set its
`ssvb_api_key`. This minimal Compose setup persists SQLite at
`./data/sams-database` on the host.

```yaml
services:
  api-2.0:
    build:
      context: ./api-2.0
    ports:
      - "127.0.0.1:8001:8001"
    volumes:
      - ./api-2.0/config/server_config.local.json:/app/config/server_config.json:ro
      - ./data:/app/data
```

The first synchronization imports every season, then competitions by season, followed
by leagues by season. It fetches referenced teams or associations only when they are
not already in SQLite. Each competition and league receives its season's
`currentSeason` flag. See
[`api-2.0/concept.yml`](./api-2.0/concept.yml) for the persistence model, lifecycle,
and environment variables.

## web-1.0

The `web-1.0` directory contains the Vite frontend for API 1.0.

Install dependencies:

```bash
cd web-1.0
npm install
```

Run the frontend:

```bash
cd web-1.0
npm run dev
```

Configure the frontend API base URL for local development with `VITE_API_BASE_URL`:

```bash
cd web-1.0
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
