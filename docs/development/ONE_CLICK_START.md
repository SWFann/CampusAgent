# One-Click Start

CampusAgent provides one-click launch scripts for local use. The scripts detect Docker automatically and fall back to SQLite when Docker is unavailable.

## Linux / WSL / macOS

From the repository root:

```bash
./scripts/start.sh
```

Useful variants:

```bash
./scripts/start.sh --mode sqlite
./scripts/start.sh --mode docker
./scripts/start.sh --no-install
./scripts/start.sh --no-seed
./scripts/start.sh --smoke
./scripts/start.sh --web-port 3001 --api-port 8001
```

## Windows PowerShell

From the repository root:

```powershell
.\scripts\start.ps1
```

Useful variants:

```powershell
.\scripts\start.ps1 -Mode sqlite
.\scripts\start.ps1 -Mode docker
.\scripts\start.ps1 -NoInstall
.\scripts\start.ps1 -NoSeed
.\scripts\start.ps1 -Smoke
.\scripts\start.ps1 -WebPort 3001 -ApiPort 8001
```

## What The Script Does

1. Checks required tools: Conda, `CampusAgent` environment, Node.js, corepack and Git.
2. Copies `.env.example` to `.env` if `.env` does not exist.
3. Chooses a runtime mode:
   - Docker mode: starts PostgreSQL, Redis and mock-model with Docker Compose.
   - SQLite mode: uses `.local/campus_agent.dev.db` and starts without Docker.
4. Installs dependencies unless `--no-install` / `-NoInstall` is provided.
5. Runs Alembic migrations.
6. Seeds demo data unless `--no-seed` / `-NoSeed` is provided.
7. Starts the API and Web development servers.

## URLs

After startup:

```text
Web:      http://localhost:3000
API:      http://localhost:8000
API Docs: http://localhost:8000/docs
```

If a default port is already in use, the scripts automatically choose the
next available port and print the actual URL. For example, if API port 8000
is busy, the API may start on `http://localhost:8001` instead.

## Demo Accounts

```text
demo_admin@example.com
demo_alice@example.com
demo_bob@example.com
demo_carol@example.com
```

Demo password:

```text
CampusAgentDemo2026!
```

## Docker Not Installed

If Docker is missing, the Linux/WSL/macOS script automatically uses SQLite:

```bash
./scripts/start.sh --mode sqlite
```

This is enough to open and explore the website. Readiness may show Redis/model dependencies as degraded, which is expected without Docker.

## Smoke Test Only

To verify the demo flow without starting servers:

```bash
./scripts/start.sh --smoke
```

## Temporary Public Sharing

Use this when all services are running on your own WSL machine, but classmates
need to access the site from other networks. This does not require a cloud
server, a domain name, or router port forwarding.

Terminal 1:

```bash
cd /root/CampusAgent
./scripts/start.sh --mode docker
```

Terminal 2:

```bash
cd /root/CampusAgent
./scripts/share_public.sh
```

The script starts:

1. A share-only web server on `http://127.0.0.1:3100`.
2. A local proxy on `http://127.0.0.1:8787`.
3. A Cloudflare Quick Tunnel that prints a public HTTPS URL.

Copy the URL that looks like:

```text
https://something.trycloudflare.com
```

Send that one URL to classmates. Keep both terminals open while they are using
the site.

Useful variants:

```bash
./scripts/share_public.sh --api-port 8000
./scripts/share_public.sh --web-port 3101
./scripts/share_public.sh --proxy-port 8788
```

Notes:

- The public URL is temporary and changes after restarting the tunnel.
- The local machine and WSL must stay awake and online.
- The script exposes one public origin. Browser requests to `/api/*` and
  `/api/v1/ws` are proxied back to the local API, so remote browsers do not try
  to access their own `localhost`.
