# Public Demo Deployment Plan

> **For agentic workers:** read this file before changing deployment code. The project root is `/root/CampusAgent`. Keep real secrets out of git. `.env` is local-only.

**Goal:** make CampusAgent reachable by classmates over the public internet for a live multi-user demo.

**Current State**
- Local web: Next.js on `http://localhost:3000`.
- Local API: FastAPI on `http://localhost:8000`.
- Docker Compose includes `web`, `api`, `postgres`, `redis`, and `mock-model`.
- The real model provider is StepFun-compatible OpenAI chat completions, configured through environment variables.
- Cookies are HttpOnly and domain-scoped. Different remote users can log in independently from their own browsers. One local browser profile can only hold one active account per site.

**Recommended Deployment Paths**

## Path A: Fast Public Demo With Cloudflare Tunnel

Use this when you need a public HTTPS URL quickly and can keep the WSL host running.

1. Run CampusAgent locally:
   ```bash
   cd /root/CampusAgent
   ./scripts/start.sh --mode docker
   ```

2. Confirm local services:
   ```bash
   curl -f http://localhost:3000
   curl -f http://localhost:8000/health/live
   ```

3. Create a Cloudflare Tunnel in the Cloudflare Zero Trust dashboard.

4. Route:
   - Public web hostname -> `http://localhost:3000`
   - Public API hostname -> `http://localhost:8000`

5. Set frontend build/runtime environment:
   ```env
   NEXT_PUBLIC_API_URL=https://<api-public-hostname>
   ```

6. Restart the web service after changing `NEXT_PUBLIC_API_URL`.

**Acceptance Criteria**
- A remote browser can open the public web URL.
- A remote user can register and log in.
- A remote user can open `/conversations`, `/organizations`, `/agents`, `/memory`, `/scenes/dinner`.
- WebSocket chat still connects.

## Path B: Stable Demo With VPS + Caddy

Use this for judge/classmate access that should remain stable.

1. Provision a Linux VPS with Docker and Docker Compose.
2. Clone the repo.
3. Create production `.env` from `.env.example`.
4. Generate strong secrets:
   ```bash
   openssl rand -hex 32
   openssl rand -hex 32
   ```
5. Configure:
   ```env
   APP_ENV=production
   APP_SECRET=<strong-secret>
   FIELD_ENCRYPTION_KEY=<strong-secret>
   ENABLE_EXTERNAL_MODEL=true
   MODEL_GATEWAY_BASE_URL=https://api.stepfun.com/v1
   MODEL_GATEWAY_MODEL=step-3.7-flash
   MODEL_GATEWAY_API_KEY=<local-secret-only>
   LOG_PROMPT_CONTENT=false
   DB_ECHO_SQL=false
   ```
6. Put Caddy in front:
   - `https://campus.example.com` -> web container `3000`
   - `https://api-campus.example.com` -> api container `8000`
7. Set `NEXT_PUBLIC_API_URL=https://api-campus.example.com`.
8. Start:
   ```bash
   docker compose up -d --build
   docker compose ps
   docker compose logs -f api web
   ```

**Acceptance Criteria**
- HTTPS works without browser warnings.
- Three different users on different networks can log in concurrently.
- Cookies work over HTTPS.
- `/health/live`, `/health/ready`, and `/metrics` are reachable as intended.
- No real API key appears in `git grep`.

## Required Safety Checks Before Public Demo

Run:
```bash
git grep -n "MODEL_GATEWAY_API_KEY\\|APP_SECRET\\|FIELD_ENCRYPTION_KEY" -- . ':!.env'
git grep -n "2Y73" -- . ':!.env'
docker compose config
```

Expected:
- No real secret is printed from tracked files.
- Compose config is valid.

## Scope Boundary

This plan does not require weakening cookie security to support multiple local browser accounts. For same-machine multi-account demos, use:
- Chrome normal window
- Chrome incognito
- Edge/Firefox or a second Chrome Profile
