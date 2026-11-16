
import hashlib
import json
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator

from fastapi.encoders import jsonable_encoder

MAX_REQUEST_SIZE = 128 * 1024  # 128 KB


# --------------------------------------------------
# Request size protection
# --------------------------------------------------

class RequestSizeLimitMiddleware:
    """Limit incoming HTTP request bodies to 128 KB."""

    def __init__(self, app, max_size=MAX_REQUEST_SIZE):
        self.app = app
        self.max_size = max_size

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        body = bytearray()
        messages = []

        while True:
            message = await receive()
            messages.append(message)

            if message["type"] == "http.disconnect":
                break

            if message["type"] == "http.request":
                body.extend(message.get("body", b""))

                if len(body) > self.max_size:
                    response = JSONResponse(
                        status_code=413,
                        content={
                            "success": False,
                            "error": {
                                "code": "REQUEST_TOO_LARGE",
                                "message": "Request body exceeds the 128 KB limit."
                            }
                        }
                    )
                    await response(scope, receive, send)
                    return

                if not message.get("more_body", False):
                    break

        async def replay_receive():
            if messages:
                return messages.pop(0)
            return await receive()

        await self.app(scope, replay_receive, send)


# --------------------------------------------------
# Application
# --------------------------------------------------

app = FastAPI(
    title="DevKit API",
    description=(
        "Free developer utilities for JSON processing, "
        "hashing and UUID generation."
    ),
    version="1.0.0",
    contact={"name": "DevKit API"},
    license_info={"name": "MIT"},
)

app.add_middleware(RequestSizeLimitMiddleware)


# --------------------------------------------------
# Response helpers
# --------------------------------------------------

def success_response(data: dict):
    return {
        "success": True,
        "data": data
    }


def error_response(code: str, message: str, details=None):
    error = {
        "code": code,
        "message": message
    }

    if details is not None:
        error["details"] = details

    return {
        "success": False,
        "error": error
    }


# --------------------------------------------------
# Global validation error handling
# --------------------------------------------------

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError
):
    return JSONResponse(
        status_code=422,
        content=error_response(
            code="VALIDATION_ERROR",
            message="Request validation failed.",
            details=jsonable_encoder(exc.errors())
        )
    )


# --------------------------------------------------
# Request models
# --------------------------------------------------

class TextPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str = Field(
        ...,
        min_length=1,
        max_length=64_000,
        description="Input text, maximum 64 KB."
    )

    @field_validator("content")
    @classmethod
    def validate_content(cls, value):
        if not value.strip():
            raise ValueError("Content cannot be empty or whitespace only.")

        return value


class UuidPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    count: int = Field(
        default=1,
        ge=1,
        le=10,
        description="Number of UUIDs to generate (1–10)."
    )


# --------------------------------------------------
# System endpoints
# --------------------------------------------------

@app.get("/", tags=["System"])
def root():
    return success_response({
        "name": "DevKit API",
        "version": app.version,
        "docs": "/docs",
        "health": "/v1/health"
    })


@app.get("/v1/health", tags=["System"])
def health():
    return success_response({
        "status": "ok",
        "service": "devkit-api",
        "version": app.version
    })


# --------------------------------------------------
# JSON utilities
# --------------------------------------------------

@app.post("/v1/json/validate", tags=["JSON"])
def validate_json(payload: TextPayload):
    try:
        parsed = json.loads(payload.content)

        return success_response({
            "valid": True,
            "type": type(parsed).__name__
        })

    except json.JSONDecodeError as exc:
        return JSONResponse(
            status_code=400,
            content=error_response(
                code="INVALID_JSON",
                message="The supplied content is not valid JSON.",
                details={
                    "reason": exc.msg,
                    "line": exc.lineno,
                    "column": exc.colno
                }
            )
        )


@app.post("/v1/json/format", tags=["JSON"])
def format_json(payload: TextPayload):
    try:
        parsed = json.loads(payload.content)

        return success_response({
            "formatted": json.dumps(
                parsed,
                indent=2,
                ensure_ascii=False
            )
        })

    except json.JSONDecodeError as exc:
        return JSONResponse(
            status_code=400,
            content=error_response(
                code="INVALID_JSON",
                message="The supplied content is not valid JSON.",
                details={
                    "reason": exc.msg,
                    "line": exc.lineno,
                    "column": exc.colno
                }
            )
        )


# --------------------------------------------------
# Hashing utility
# --------------------------------------------------

@app.post("/v1/hash/sha256", tags=["Encoding & Hashing"])
def sha256(payload: TextPayload):
    digest = hashlib.sha256(
        payload.content.encode("utf-8")
    ).hexdigest()

    return success_response({
        "algorithm": "SHA-256",
        "hash": digest
    })


# --------------------------------------------------
# UUID utility
# --------------------------------------------------

@app.post("/v1/uuid", tags=["Utilities"])
def generate_uuid(payload: UuidPayload):
    values = [
        str(uuid.uuid4())
        for _ in range(payload.count)
    ]

    return success_response({
        "uuids": values,
        "count": len(values)
    })
