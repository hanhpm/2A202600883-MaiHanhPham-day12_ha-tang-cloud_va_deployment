"""Production-ready AI agent for Day 12."""
import json
import logging
import signal
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.auth import verify_api_key
from app.config import settings
from app.cost_guard import cost_guard
from app.rate_limiter import rate_limiter
from utils.mock_llm import ask as llm_ask


logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format='{"ts":"%(asctime)s","level":"%(levelname)s","message":"%(message)s"}',
)
logger = logging.getLogger(__name__)

START_TIME = time.time()
is_ready = False
request_count = 0
error_count = 0


@asynccontextmanager
async def lifespan(app: FastAPI):
    global is_ready
    logger.info(json.dumps({"event": "startup", "app": settings.app_name}))
    is_ready = True
    logger.info(json.dumps({"event": "ready"}))
    yield
    is_ready = False
    logger.info(json.dumps({"event": "shutdown"}))


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
)


@app.middleware("http")
async def request_middleware(request: Request, call_next):
    global request_count, error_count
    start = time.time()
    request_count += 1
    try:
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if "server" in response.headers:
            del response.headers["server"]
        logger.info(
            json.dumps(
                {
                    "event": "request",
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "ms": round((time.time() - start) * 1000, 1),
                }
            )
        )
        return response
    except Exception:
        error_count += 1
        logger.exception(json.dumps({"event": "request_error", "path": request.url.path}))
        raise


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    user_id: str = Field(default="anonymous", min_length=1, max_length=100)


class AskResponse(BaseModel):
    question: str
    answer: str
    model: str
    usage: dict
    timestamp: str


@app.get("/", tags=["Info"])
def root():
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "endpoints": {
            "ask": "POST /ask (requires X-API-Key)",
            "health": "GET /health",
            "ready": "GET /ready",
            "metrics": "GET /metrics (requires X-API-Key)",
        },
    }


@app.post("/ask", response_model=AskResponse, tags=["Agent"])
async def ask_agent(
    body: AskRequest,
    request: Request,
    api_key: str = Depends(verify_api_key),
):
    bucket = f"{api_key[:8]}:{body.user_id}"
    rate_info = rate_limiter.check(bucket)

    estimated_input_tokens = len(body.question.split()) * 2
    cost_guard.check_monthly_budget(body.user_id)
    answer = llm_ask(body.question)
    estimated_output_tokens = len(answer.split()) * 2
    usage = cost_guard.record_usage(
        body.user_id,
        input_tokens=estimated_input_tokens,
        output_tokens=estimated_output_tokens,
    )

    logger.info(
        json.dumps(
            {
                "event": "agent_call",
                "user_id": body.user_id,
                "client": request.client.host if request.client else "unknown",
                "question_chars": len(body.question),
            }
        )
    )

    return AskResponse(
        question=body.question,
        answer=answer,
        model=settings.llm_model,
        usage={**usage, "rate_limit_remaining": rate_info["remaining"]},
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@app.get("/health", tags=["Operations"])
def health():
    return {
        "status": "ok",
        "version": settings.app_version,
        "environment": settings.environment,
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "total_requests": request_count,
        "checks": {
            "llm": "mock" if not settings.openai_api_key else "openai",
            "redis": rate_limiter.backend_name,
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/ready", tags=["Operations"])
def ready():
    if not is_ready:
        raise HTTPException(status_code=503, detail="Not ready")
    return {"ready": True, "redis": rate_limiter.ping()}


@app.get("/metrics", tags=["Operations"])
def metrics(api_key: str = Depends(verify_api_key)):
    del api_key
    return {
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "total_requests": request_count,
        "error_count": error_count,
        "monthly_budget_usd": settings.monthly_budget_usd,
        "rate_limit_per_minute": settings.rate_limit_per_minute,
        "rate_limit_backend": rate_limiter.backend_name,
    }


def _handle_signal(signum, _frame):
    logger.info(json.dumps({"event": "signal", "signum": signum}))


signal.signal(signal.SIGTERM, _handle_signal)


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        timeout_graceful_shutdown=30,
    )
