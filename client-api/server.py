from __future__ import annotations

from contextlib import asynccontextmanager
import logging
from uuid import UUID, uuid4

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time
from competition.fetch_competition import COMPETITION
from competition.fetch_competition_list import COMPETITION_LIST_STORE
from league.fetch_league import LEAGUE
from league.fetch_league_list import LEAGUE_LIST_STORE
from live_endpoint import get_live_payload, startup_live_endpoint
from metrics import METRICS
from server_config import HOST, LOG_LEVEL, PORT


logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
LOGGER = logging.getLogger("api")


@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        METRICS.start()
        startup_live_endpoint()
    except Exception:
        LOGGER.exception("Live endpoint startup failed")
        raise

    yield

    METRICS.stop()


app = FastAPI(
    title="Competition and League API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def attach_request_id(request: Request, call_next):
    started_at = time.perf_counter()
    request_id = request.headers.get("X-Request-Id") or str(uuid4())
    client_id = request.query_params.get("client_id") or request.headers.get("X-Client-Id")
    request.state.request_id = request_id
    METRICS.record_unique_client_session(client_id)

    try:
        response = await call_next(request)
    except Exception:
        duration_ms = (time.perf_counter() - started_at) * 1000.0
        METRICS.record_http_request(
            method=request.method,
            path=request.scope.get("route").path if request.scope.get("route") else request.url.path,
            status_code=500,
            duration_ms=duration_ms,
        )
        raise

    duration_ms = (time.perf_counter() - started_at) * 1000.0
    METRICS.record_http_request(
        method=request.method,
        path=request.scope.get("route").path if request.scope.get("route") else request.url.path,
        status_code=response.status_code,
        duration_ms=duration_ms,
    )
    response.headers["X-Request-Id"] = request_id
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": 422,
                "message": "Validation error",
                "details": exc.errors(),
            },
            "requestId": request.state.request_id,
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    detail = exc.detail if isinstance(exc.detail, str) else "Request failed"
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.status_code,
                "message": detail,
            },
            "requestId": request.state.request_id,
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    LOGGER.exception("Unhandled error for request_id=%s", request.state.request_id)
    return JSONResponse(
        status_code=502,
        content={
            "error": {
                "code": 502,
                "message": "Failed to fetch competition data",
            },
            "requestId": request.state.request_id,
        },
    )


@app.get("/api/health")
@app.get("/api/healthz")
async def health(request: Request) -> dict:
    return {
        "status": "ok",
        "requestId": request.state.request_id,
    }


@app.get("/api/competition/{competition_id}")
async def competition(competition_id: UUID, request: Request) -> dict:
    try:
        payload, was_cached = COMPETITION.get(str(competition_id))
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail="Failed to fetch competition data") from exc

    return payload


@app.get("/api/competition-list")
async def competition_list(request: Request) -> dict:
    try:
        payload = COMPETITION_LIST_STORE.get()
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail="Failed to fetch competition list") from exc

    return {
        "data": payload,
        "requestId": request.state.request_id,
    }


@app.get("/api/league/{league_id}")
async def league(league_id: UUID, request: Request) -> dict:
    try:
        payload, was_cached = LEAGUE.get(str(league_id))
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail="Failed to fetch league data") from exc

    return payload


@app.get("/api/league-list")
async def league_list(request: Request) -> dict:
    try:
        payload = LEAGUE_LIST_STORE.get()
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail="Failed to fetch league list") from exc

    return {
        "data": payload,
        "requestId": request.state.request_id,
    }


@app.get("/api/live/{competition_id}")
async def live_by_competition(competition_id: UUID, request: Request) -> dict:
    try:
        payload = get_live_payload(str(competition_id))
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return payload


def run_server() -> None:
    uvicorn.run(
        "server:app",
        host=HOST,
        port=PORT,
        log_level=LOG_LEVEL,
        proxy_headers=True,
        forwarded_allow_ips="*",
    )


if __name__ == "__main__":
    run_server()
