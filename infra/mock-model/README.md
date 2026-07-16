# Mock Model Service - P2 Compose Placeholder

This directory contains a minimal HTTP server that serves as a placeholder
for the Model Gateway service in the P2 Docker Compose baseline.

## Purpose

- Provides health check endpoints for Compose orchestration
- Responds to HTTP requests with placeholder data
- Does NOT implement real model routing or processing
- Will be replaced or extended in P7 (Model Gateway & Edge Node)

## API Endpoints

### Health Checks

- `GET /health/live` - Returns 200 with status `ok`
- `GET /health/ready` - Returns 200 with status `ready`

### Placeholder Endpoints

- `POST /v1/chat/completions` - Returns mock completion response
- `POST /chat` - Returns mock chat response
- `POST /complete` - Returns mock completion response

All endpoints return 404 for unimplemented paths.

## Important Notes

⚠️ **This is NOT a real model gateway**

- Do not route real production requests to this service
- Do not use this for any actual AI/ML processing
- This service does not require API keys or external connections
- The service uses only Python standard library (zero external dependencies)

## Running Locally

```bash
cd infra/mock-model
python server.py
```

## Running in Docker

```bash
docker compose up mock-model
```

See the root `compose.yaml` for service configuration.