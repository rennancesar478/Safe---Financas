# Deploy

The frontend runs on Vercel. The Flask API runs on Render with a persistent disk for SQLite.

## Render

1. In Render, create a Blueprint and select this GitHub repository. Render reads `render.yaml` and creates the API service and its persistent disk. The `starter` plan is required for the disk.
2. Copy the service URL, for example `https://safe-financas-api.onrender.com`.

## Vercel

1. Import the same GitHub repository as a Vercel project and set **Root Directory** to `frontend`.
2. Add the environment variable `VITE_API_URL` with the Render service URL, without a trailing slash or `/api`.
3. Deploy. The Vercel URL is covered by the Render CORS pattern for `*.vercel.app`. If using a custom domain, add that exact origin to Render's `FRONTEND_ORIGINS` environment variable and redeploy the API.

## Optional email configuration

To enable password-reset emails, configure `SMTP_HOST`, `SMTP_PORT`, `SMTP_USUARIO`, and `SMTP_SENHA` in Render. Do not commit these values.

The hosted database starts empty. The local `safe_financas.db` is not copied to Render; import existing data separately through a secure transfer if it needs to be retained.