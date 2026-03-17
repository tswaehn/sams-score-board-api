# client-api

The `client-api` directory contains a FastAPI server for exposing competition data from the upstream SAMS API.

Install dependencies:

```bash
cd client-api
pip install -r requirements.txt
```

Run the API server:

```bash
cd client-api
SSVB_API_KEY=your_api_key uvicorn server:app --host 0.0.0.0 --port 8000
```

Optional environment variables:

* `HOST` defaults to `0.0.0.0`
* `PORT` defaults to `8000`
* `LOG_LEVEL` defaults to `info`

Endpoints:

* `GET /competition/<uuid>` returns the result of `get_competition(<uuid>)` as JSON
* `GET /health`
* `GET /healthz`

Example:

```bash
curl http://127.0.0.1:8000/competition/<uuid>
curl http://127.0.0.1:8000/healthz
```


# wiki

* https://wiki.sams-server.de/wiki/REST-API-Schnittstelle


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

# sams ticker

* https://backend.sams-ticker.de/live/indoor/tickers/dvv
* https://backend.sams-ticker.de/live/indoor/tickers/ssvb

front end 
* https://ssvb.sams-ticker.de/
