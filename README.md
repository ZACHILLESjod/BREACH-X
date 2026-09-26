# BREACH-X

BREACH-X is a React/Vite security exposure dashboard backed by FastAPI and PostgreSQL. The dashboard reads the persisted asset inventory and exposure assessments; protected write and NVD operations are intended for trusted API clients.

## Deploy to Render

Create a Render PostgreSQL database, one Python Web Service, and one Static Site. Configure the monorepo root directories as `backend` and `frontend` respectively. No `render.yaml` is included so creating a deploy does not implicitly provision or replace production resources.

### PostgreSQL

Use the Render database's **internal connection URL** for the backend's `DATABASE_URL`. The backend accepts `postgresql+psycopg://...` and normalizes plain `postgresql://` or `postgres://` URLs to the installed psycopg 3 driver. Keep the URL only in Render's backend environment settings.

For a new, empty database, run `python create_tables.py` once from the backend service context after setting `DATABASE_URL`. This creates the current tables, but it is not a versioned migration system. Review schema changes and use a separate migration process for ongoing production upgrades; Alembic can be introduced in a later milestone.

Do not blindly run `seed_demo_data.py` against production. It inserts demo assets and synthetic demo vulnerability records. It is intended for demo or staging databases.

### Backend Web Service

- **Root directory:** `backend`
- **Runtime:** Python 3.13 (also pinned by repository `.python-version`)
- **Build command:** `pip install -r requirements.txt`
- **Start command:** `python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **Health check path:** `/health`

Set these backend environment variables in Render:

| Variable | Requirement |
| --- | --- |
| `DATABASE_URL` | Required for database-backed API routes. Use the Render PostgreSQL internal URL. |
| `BREACHX_API_KEY` | Required to enable protected write and NVD-fetch operations. Keep it only in backend secrets. Send it from trusted API clients as `X-API-Key`. |
| `CORS_ORIGINS` | Set to the exact static-site origin, for example `https://your-site.onrender.com` (no trailing slash). Comma-separate additional exact origins. If omitted, only local Vite origins are allowed. |
| `NVD_API_KEY` | Optional. When set, backend requests include it in NVD's `apiKey` request header. It is never sent to the browser. |

`GET /health` reports process health without checking PostgreSQL or calling NVD. `GET /health/db` separately checks database connectivity and returns 503 if the database is unavailable.

These routes require `X-API-Key`: `POST /assets`, `POST /software`, `POST /vulnerabilities`, `GET /cve/{cve_id}`, `POST /nvd/assess`, and `POST /nvd/sync`. The CVE lookup is protected because a cache miss makes an outbound NVD request. Public dashboard reads (`GET /`, `/health`, `/assets`, and `/assets/{asset_id}/exposure`) remain unauthenticated. Stateless calculation routes (`POST /match-vulnerability`, `/match-cve`, and `/assess-risk`) remain public because they do not write data or call NVD.

### Frontend Static Site

- **Root directory:** `frontend`
- **Build command:** `npm ci && npm run build`
- **Publish directory:** `dist`
- **Build-time environment variable:** `VITE_API_BASE_URL=https://<backend-domain>`
- **Rewrite rule:** source `/*`, destination `/index.html`, action `Rewrite` (supports direct visits and refreshes on client-side routes).

Replace the example value with the deployed backend origin. `VITE_API_BASE_URL` is embedded in public browser assets; never put API keys, database URLs, or other secrets in any `VITE_` variable. The local default remains `/api` for the Vite development proxy. Rebuild the static site whenever the backend origin changes.

### CORS and API keys

Set `CORS_ORIGINS` to the exact frontend origin after creating the Render static site. Wildcard origins are rejected; browser credentials are disabled because the app uses no cookie/session authentication. The frontend does not need or receive `BREACHX_API_KEY`; protected operations are for trusted clients outside the public dashboard.

NVD synchronization is request-triggered and bounded. No background scheduler is configured. An NVD key is optional for requests, but may be useful to reduce rate limiting during production use; see the [NVD API documentation](https://nvd.nist.gov/developers/vulnerabilities).
