from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from uuid import UUID, uuid4

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from fetch_competition import get_competition


HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "info").lower()

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
LOGGER = logging.getLogger("competition-api")
CACHE_DIR = Path(__file__).with_name("cache")
COMPETITION_LIST_PATH = CACHE_DIR / "competition-list.json"

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
        payload = get_competition(str(competition_id))
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail="Failed to fetch competition data") from exc

    return {
        "data": payload,
        "requestId": request.state.request_id,
    }


@app.get("/api/competition-list")
async def competition_list(request: Request) -> dict:
    try:
        with COMPETITION_LIST_PATH.open("r", encoding="utf-8") as input_file:
            payload = json.load(input_file)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="competition-list.json not found") from exc
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail="competition-list.json is invalid") from exc

    return {
        "data": payload,
        "requestId": request.state.request_id,
    }


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
