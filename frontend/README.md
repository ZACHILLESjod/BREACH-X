# BREACH-X Dashboard

React and Vite dashboard for the BREACH-X FastAPI backend.

## Local development

```powershell
npm install
Copy-Item .env.example .env.local
npm run dev
```

The development server proxies `/api/*` to `http://127.0.0.1:8000/*`, avoiding a backend CORS change. Set `VITE_API_BASE_URL` to an API origin when deploying the frontend elsewhere.

## Data available in this milestone

The dashboard loads an asset by ID through `GET /assets/{asset_id}/exposure`. Loaded IDs are remembered in browser local storage. There is currently no `GET /assets` directory or global aggregate endpoint, so the dashboard labels its counts as scoped to assets loaded in this browser. Exposure rows cover the local vulnerability records returned by the backend for each installed software entry.
