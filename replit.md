# Reserved™

A Flask/Python preview of Reserved's October-launch product — a UK fintech/tax-technology app covering limited tax estimates and financial dashboards. Capital Gains Tax is outside v1 and its customer route is disabled.

## Running the app

```
.venv/bin/python run.py
```

The workflow "Start application" runs this automatically on port 5000. The app starts in **demo mode** — no bank accounts connected, no money moved.

## Stack

- Python 3.13, Flask 3.1.1, Flask-WTF 1.2.2, gunicorn 23.0.0
- Dependencies installed in `.venv/` (virtual environment)
- Jinja2 templates in `reserved/templates/`
- Design system CSS in `reserved/static/css/`

## Secrets

- `SESSION_SECRET` — required for Flask session signing (already set in Replit Secrets)
- `CANONICAL_BASE_URL` — **required for Yapily sandbox and production**. Set to the stable public URL of the app (e.g. `https://yourrepl.replit.dev`). Used to construct the Yapily OAuth callback URL. If absent the request host header is used as a fallback, which is unreliable in proxied environments and must not be relied on outside local development.
- `YAPILY_APPLICATION_UUID` — Yapily application identifier (required for live bank connections)
- `YAPILY_SECRET` — Yapily application secret (required for live bank connections)
- `CLERK_PUBLISHABLE_KEY` — Clerk frontend key (required for real user auth; demo-login is available without it in non-production environments)
- `AUTH_PUBLIC_ORIGIN` — exact HTTPS browser origin for Reserved, with no path (for example `https://app.reserved.example`); required for Clerk token validation
- `CLERK_AUTHORIZED_PARTIES` — optional comma-separated origin allowlist when more than one origin is intentionally supported; otherwise `AUTH_PUBLIC_ORIGIN` is used
- `CLERK_JWT_AUDIENCE` — optional expected audience only when a Clerk custom JWT template is configured with that audience; omit for default Clerk session tokens

## Project structure

```
reserved/
  api/          API blueprint (routes)
  engines/      Tax calculation engines (income tax, capital gains, allocation)
  models/       Data schemas
  providers/    Banking, payments, accounting provider stubs
  repositories/ Data access layer
  services/     Business logic (dashboard, roadmap)
  static/       CSS and JS assets
  templates/    Jinja2 HTML templates
  web/          Web blueprint (routes)
run.py          Entry point
```

## Tax engine

The core tax engines live in `reserved/engines/`. Key facts:

- **`utils.py`** — shared `money()` helper (ROUND_HALF_UP to 2 d.p.); all engines import from here.
- **`tax_config.py`** — 2026/27 thresholds (income tax, Class 4 NI, student loans for all 5 plans).
- **`income_tax.py`** — before/after differential estimator. Supports pension Relief at Source (basic-rate band extension), PA taper and single undergraduate-plan or undergraduate-plus-postgraduate cases. Simultaneous multiple undergraduate plans fail closed pending verification; no partial amount should be shown.
- **`allocation.py`** — legacy gross → tax reserve / platform fee splitter with a deprecated internal remainder and reconciliation assert; customer/dashboard contracts must not expose the remainder as “safe to spend”.
- **`capital_gains.py`** — dormant post-v1 CGT code retained internally; it is not an enabled or assured v1 customer capability.

Run the test suite: `.venv/bin/python -m pytest tests/`  
Generate assurance metadata: `.venv/bin/python scripts/generate_assurance_metadata.py`  
Dev-only assurance page: `/tax-assurance`  
Full methodology: `docs/TAX_ASSURANCE.md`

## User preferences

<!-- Add user preferences here as they are established -->
