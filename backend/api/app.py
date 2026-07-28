"""FastAPI application factory and middleware."""
from __future__ import annotations

import os
import time
import uuid

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from api import dependencies as deps
from api.routers import datamuse, health, integrations, storage, words, words_mutations
from logger_config import log_api_call

load_dotenv()

API_VERSION = "2.2.0"


def _configure_cors(app: FastAPI) -> None:
    default_origins = [
        "http://localhost:4200",
        "http://localhost:4201",
        "http://127.0.0.1:4200",
        "http://127.0.0.1:4201",
        "https://word-dol.pages.dev",
        "https://word-filter-app.pages.dev",
        "https://terse-aw8.pages.dev",
    ]
    cors_env = os.getenv("CORS_ORIGINS", "").strip()
    if cors_env == "*":
        cors_origins = ["*"]
        cors_credentials = False
    elif cors_env:
        cors_origins = [origin.strip() for origin in cors_env.split(",") if origin.strip()] or default_origins
        cors_credentials = True
    else:
        cors_origins = default_origins
        cors_credentials = True

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=cors_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def create_app() -> FastAPI:
    app = FastAPI(
        title="Word Filter API - Unified",
        description="API for filtering words with local file and Object Store storage options",
        version=API_VERSION,
    )

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        deps.total_api_requests += 1
        request_id = str(uuid.uuid4())
        start_time = time.time()
        request.state.request_id = request_id

        deps.logger.info(
            "Request started: %s %s",
            request.method,
            request.url.path,
            extra={
                "extra_fields": {
                    "request_id": request_id,
                    "method": request.method,
                    "url": str(request.url),
                    "client_ip": request.client.host if request.client else None,
                    "user_agent": request.headers.get("user-agent"),
                }
            },
        )

        try:
            response = await call_next(request)
            duration = time.time() - start_time
            log_api_call(
                request.method,
                request.url.path,
                response.status_code,
                duration,
                request_id=request_id,
                response_size=response.headers.get("content-length", 0),
            )
            return response
        except Exception as e:
            duration = time.time() - start_time
            deps.logger.error(
                "Request failed: %s %s - %s",
                request.method,
                request.url.path,
                str(e),
                exc_info=True,
                extra={
                    "extra_fields": {
                        "request_id": request_id,
                        "duration_seconds": duration,
                        "error": str(e),
                    }
                },
            )
            raise

    _configure_cors(app)

    @app.on_event("startup")
    async def startup_event():
        deps.logger.info("Application startup initiated")
        try:
            await deps.load_words_concurrent()
            deps.logger.info("Application startup completed successfully")
        except Exception:
            deps.logger.error("Application startup failed", exc_info=True)
            raise

    @app.on_event("shutdown")
    async def shutdown_event():
        deps.logger.info("Application shutdown initiated")
        try:
            await deps.shutdown_pools()
            deps.logger.info("Application shutdown completed successfully")
        except Exception as e:
            deps.logger.error("Error during application shutdown", exc_info=True)

    app.include_router(health.router)
    app.include_router(words.router)
    app.include_router(words_mutations.router)
    app.include_router(storage.router)
    app.include_router(integrations.router)
    app.include_router(datamuse.router)

    return app


app = create_app()
