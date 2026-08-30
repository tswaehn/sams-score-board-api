from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from uuid import UUID

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from config import (
    DATABASE_PATH,
    HISTORICAL_SYNC_INTERVAL_SECONDS,
    HOST,
    LOG_LEVEL,
    PORT,
    SSVB_API_KEY,
    SSVB_API_URL,
    UPSTREAM_MAX_RETRIES,
    UPSTREAM_MIN_DELAY_SECONDS,
)
from database import Database
from internal_log import InternalLogWriter
from upstream_sync import HistoricalSync
from upstream_queue import UpstreamQueue


logging.basicConfig(level=LOG_LEVEL.upper(), format="%(asctime)s %(levelname)s %(name)s %(message)s")
LOGGER = logging.getLogger("api2.server")
DATABASE = Database(DATABASE_PATH)
INTERNAL_LOG = InternalLogWriter(DATABASE.path.parent / "internal.log")
UPSTREAM = UpstreamQueue(
    SSVB_API_URL,
    SSVB_API_KEY,
    min_delay_seconds=UPSTREAM_MIN_DELAY_SECONDS,
    max_retries=UPSTREAM_MAX_RETRIES,
    request_time_logger=INTERNAL_LOG.record_request_time,
    timeout_logger=INTERNAL_LOG.record_request_timeout,
)
SYNC = HistoricalSync(
    DATABASE,
    UPSTREAM,
    repeat_after_seconds=HISTORICAL_SYNC_INTERVAL_SECONDS,
    collection_failure_logger=INTERNAL_LOG.record_collection_failure,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    DATABASE.initialize()
    INTERNAL_LOG.start()
    LOGGER.info("Starting SAMS scoreboard API")
    INTERNAL_LOG.record_startup()
    UPSTREAM.start()
    SYNC.start()
    yield
    SYNC.stop()
    UPSTREAM.stop()
    INTERNAL_LOG.stop()


app = FastAPI(title="SAMS historical mirror API", version="2.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/api/healthz")
@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "database": DATABASE.status(), "sync": SYNC.status()}


@app.get("/api/seasons")
def seasons() -> dict:
    return {"data": DATABASE.list_seasons()}


@app.get("/api/associations")
def associations() -> dict:
    return {"data": DATABASE.list_associations()}


@app.get("/api/competition-list")
def competition_list(season_id: UUID | None = None, association_id: UUID | None = None) -> dict:
    return {"data": DATABASE.list_entities("competition", str(season_id) if season_id else None, str(association_id) if association_id else None)}


@app.get("/api/league-list")
def league_list(season_id: UUID | None = None, association_id: UUID | None = None) -> dict:
    return {"data": DATABASE.list_entities("league", str(season_id) if season_id else None, str(association_id) if association_id else None)}


@app.get("/api/competition/{competition_id}")
def competition(competition_id: UUID) -> dict:
    payload = DATABASE.get_entity("competition", str(competition_id))
    if payload is None:
        raise HTTPException(404, "Competition is not in the historical mirror")
    return payload


@app.get("/api/league/{league_id}")
def league(league_id: UUID) -> dict:
    payload = DATABASE.get_entity("league", str(league_id))
    if payload is None:
        raise HTTPException(404, "League is not in the historical mirror")
    return payload


if __name__ == "__main__":
    uvicorn.run(app, host=HOST, port=PORT)
