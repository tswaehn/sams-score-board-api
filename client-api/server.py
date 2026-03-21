from __future__ import annotations

import logging
import os
import threading
import time
from uuid import UUID, uuid4

import requests
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from requests import RequestException

from fetch_competition import get_competition
from fetch_competition_list import get_competition_list


HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "info").lower()
LIVE_API_URL = os.getenv("LIVE_API_URL")
LIVE_API_TIMEOUT_SECONDS = 30
LIVE_API_CACHE_SECONDS = 1.0
LIVE_API_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "no-cache",
    "Connection": "close",
    "Pragma": "no-cache",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "cross-site",
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/127.0.0.0 Safari/537.36"
    ),
}
LIVE_API_REQUEST_LOCK = threading.Lock()
LIVE_API_CACHE_PAYLOAD: dict | None = None
LIVE_API_CACHE_UPDATED_AT = 0.0

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
LOGGER = logging.getLogger("competition-api")

app = FastAPI(
    title="Competition API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
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
    request_id = request.headers.get("X-Request-Id") or str(uuid4())
    request.state.request_id = request_id

    response = await call_next(request)
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
        payload, was_cached = get_competition(str(competition_id))
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail="Failed to fetch competition data") from exc

    return payload


@app.get("/api/competition-list")
async def competition_list(request: Request) -> dict:
    try:
        payload = get_competition_list()
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail="Failed to fetch competition list") from exc

    return {
        "data": payload,
        "requestId": request.state.request_id,
    }


@app.get("/api/live")
async def live(request: Request) -> dict:
    global LIVE_API_CACHE_PAYLOAD, LIVE_API_CACHE_UPDATED_AT

    if not LIVE_API_URL:
        raise HTTPException(status_code=500, detail="Missing environment variable: LIVE_API_URL")

    try:
        with LIVE_API_REQUEST_LOCK:
            now = time.monotonic()
            cache_age = now - LIVE_API_CACHE_UPDATED_AT

            if LIVE_API_CACHE_PAYLOAD is not None and cache_age < LIVE_API_CACHE_SECONDS:
                payload = LIVE_API_CACHE_PAYLOAD
                was_cached = True
            else:
                response = requests.get(
                    LIVE_API_URL,
                    headers=LIVE_API_HEADERS,
                    timeout=LIVE_API_TIMEOUT_SECONDS,
                )
                response.raise_for_status()
                payload = response.json()
                LIVE_API_CACHE_PAYLOAD = payload
                LIVE_API_CACHE_UPDATED_AT = time.monotonic()
                was_cached = False
    except RequestException as exc:
        raise HTTPException(status_code=502, detail="Failed to fetch live data") from exc
    except ValueError as exc:
        raise HTTPException(status_code=502, detail="Live API did not return valid JSON") from exc

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
