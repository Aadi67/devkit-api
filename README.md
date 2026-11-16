
# DevKit API

Free developer utilities through a simple REST API.

## Features

- JSON validation
- JSON formatting
- SHA-256 hashing
- UUID v4 generation
- API health checks

## Base URL

https://your-deployment-url

## Authentication

No API key required for the MVP.

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | /v1/health | Health check |
| POST | /v1/json/validate | Validate JSON |
| POST | /v1/json/format | Format JSON |
| POST | /v1/hash/sha256 | Generate SHA-256 |
| POST | /v1/uuid | Generate UUIDs |

## Example: Generate UUID

Request:

POST /v1/uuid

{
  "count": 3
}

Response:

{
  "success": true,
  "data": {
    "uuids": ["..."],
    "count": 3
  }
}

## Local Development

git clone YOUR_REPOSITORY_URL

cd devkit-api

python3 -m venv .venv

source .venv/bin/activate

python -m pip install -r requirements.txt

uvicorn app.main:app --reload

## Documentation

- Swagger: /docs
- ReDoc: /redoc
- OpenAPI: /openapi.json

## License

MIT
