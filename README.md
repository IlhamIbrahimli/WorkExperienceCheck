# AppWatch

A small FastAPI app that watches work experience / internship application pages and notifies me the moment one changes — built so I don't miss application windows opening.

## How it works

1. Add a page through the web UI (name, link, year to apply).
2. Activate a cron job on a site like cronjob.org to GET /check/0 weekly.
3. Each page is rendered with Playwright, stripped of noisy elements (nav, scripts, images, etc.) with BeautifulSoup, and hashed with SHA-256.
4. If the hash has changed since last time, the new hash is saved and a push notification is sent to my phone via a Supabase Edge Function (`send-push-notif`).
5. The edge function POSTS to a notfy.sh topic which appears as a phone notification. This step can be written in the `main.py` function, however Render does not allow it.

## Stack

- **FastAPI** + **Jinja2** + **HTMX** — server-rendered UI with partial page swaps
- **Playwright** — Renders the webpages to ensure all of the JS components load
- **Supabase** — Postgres table (`experience`) for storage + Edge Function for notifications
- **HTTP Basic Auth** — protects the web UI and add/delete routes

## Setup

Requires Python 3.13+.

```bash
uv sync                      # or: pip install -e .
uv run playwright install chromium
```

Create a `.env` file:

```
SUPABASE_URL=
SUPABASE_TOKEN=
CRON_SECRET=       # shared secret required to trigger /check
AUTH_USER=         # basic auth for the web UI
AUTH_PASS=
NOTIFY_LINK=       # used by the Supabase notify function
```

Run locally:

```bash
uv run uvicorn main:app --reload
```

## Usage

- Visit `/` (basic auth required) to add, view, and delete tracked pages.
- Set up a cronjob to `GET /check/0` with header `X-Secret-Key: <CRON_SECRET>` on a schedule — this checks all pages in the background.
- `GET /check/{id}` checks a single page the same way.
- `HEAD /keepup` — a no-op endpoint for pinging the app to keep it awake on free hosting tiers if using a service like Render to host the site. I use uptime robot to stop Render from putting the site to sleep.
