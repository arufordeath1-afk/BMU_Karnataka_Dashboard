# Deploying to Render (free tier, one click)

## 1. Push this repo to GitHub

```bash
cd india-post
git init
git add .
git commit -m "India Post Karnataka Circle dashboard + API"
```
Then create an empty repo on GitHub (github.com/new — don't initialize with a
README) and push:
```bash
git remote add origin https://github.com/<your-username>/india-post.git
git branch -M main
git push -u origin main
```

## 2. Deploy the Blueprint

1. Go to https://dashboard.render.com/blueprints
2. Click **New Blueprint Instance**, connect your GitHub account, pick the
   `india-post` repo. Render finds `render.yaml` automatically.
3. Click **Apply**. Render provisions:
   - `india-post-db` — free Postgres
   - `india-post-api` — the FastAPI backend (runs migrations + seeds demo
     data on first boot, then serves on its own free web service)
   - `india-post-dashboard` — the static HTML frontend, pre-wired to call
     the API

That's it — Render gives you two URLs, e.g.:
- `https://india-post-api.onrender.com` (API + Swagger docs at `/docs`)
- `https://india-post-dashboard.onrender.com` (the dashboard — open this one)

## 3. If Render assigned different service names

`render.yaml` hardcodes the frontend's API URL as
`https://india-post-api.onrender.com`, assuming that name was free. If
Render appended a suffix (e.g. `india-post-api-a1b2`) because the name was
taken, the frontend won't reach it. Fix it once:
- Open the `india-post-dashboard` service → **Environment** → **Shell**, or
  just edit `frontend/index.html` locally (find `__API_BASE__` — after the
  build step it'll already say the wrong URL, so search for
  `const API_BASE` instead) and set it to your actual API URL, then push —
  Render redeploys automatically on every push to `main`.

## 4. Tighten CORS once you know the frontend's real URL

In the Render dashboard, open `india-post-api` → **Environment**, set
`CORS_ORIGINS` to your dashboard's exact URL (e.g.
`https://india-post-dashboard.onrender.com`) instead of `*`, then redeploy.

## Free tier limits to know about

- Both services spin down after 15 minutes idle and take ~30–60s to wake up
  on the next request. Fine for evaluating the tool, not for people relying
  on it daily — upgrade the `india-post-api` service's plan when ready.
- Free Postgres on Render is deleted after 30 days of no active paid plan
  attached to the workspace — check Render's current free-tier database
  policy before treating this as long-term storage.

## Changing anything later

Every `git push` to `main` auto-redeploys both services. Database schema
changes: run `alembic revision --autogenerate -m "..."` locally, commit the
new migration file, push — `alembic upgrade head` in the start command
applies it automatically on next boot.
