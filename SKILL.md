---
name: rentalready-cli
description: "Read your RentalReady *owner* (host space) content from the terminal via the bundled `rr` command — property info, current-month KPIs (occupancy, net revenue, ADR, current guest), and the full reservations financial breakdown (rental revenue, commission, cleaning, platform/payment fees, tourist tax, net revenue) with per-period totals, filterable by platform and date. RentalReady's owner portal (pms.rentalready.io) is a server-rendered Django app behind a two-factor session login with NO owner-facing JSON API (the /api/v* DRF endpoints are manager-only and 403 for owners), so the CLI authenticates exactly like the owner's browser — reusing the Django `sessionid` cookie read straight from a locally logged-in Chromium browser (Chrome/Arc/Brave/Edge) by decrypting its cookie store with the macOS keychain key (the notion-cli trick) — and parses the host-space HTML into structured data. Every read command supports --json. Use when the user wants to read their RentalReady owner data: reservations, earnings/revenue, occupancy, property details, or profile."
---

# rentalready-cli

Read your **RentalReady owner (host space)** content from the terminal —
property details, month KPIs, and the reservations financial breakdown — by
acting as the logged-in owner against `pms.rentalready.io`.

## How to invoke

Invoke it as **`rr`** — on `$PATH` via a symlink in `~/.local/bin` onto this
repo's `bin/rr`, so it always runs the current checkout: a `git pull`, or even
an uncommitted edit, takes effect immediately with nothing to reinstall.

```bash
rr overview
```

Examples in this doc are written that way. If `rr` is not on `$PATH`, run the
bundled launcher `bin/rr` resolved against this skill's own directory (PEP 723
— `uv` resolves deps inline on first run), or link it once:

```bash
ln -sfn <skill-dir>/bin/rr ~/.local/bin/rr
```

## Why it reuses the browser session (no login flow)

RentalReady's owner portal is a **server-rendered Django app** protected by a
**two-factor session login**. There is **no owner-facing JSON API**: the
`/api/v1/` and `/api/v2/` DRF endpoints exist but are **manager-only** — as the
owner role they return `403 "Vous n'êtes pas autorisé"`. So the only owner
surface is the HTML "host space" (`/authentification/host_*` and
`/host_space/*`).

Rather than re-implement the 2FA login wizard, the CLI authenticates exactly
like the owner's browser — with the Django **`sessionid` cookie**. It reads that
cookie **straight from a locally logged-in Chromium browser** (Chrome, Arc,
Brave, Edge) by decrypting the cookie store with the app's **macOS keychain
key** (the same approach as `notion-cli`). Nothing to paste; you only log in
again in the browser when the session expires (~14 days).

## Authentication

Preferred — automatic extraction from a logged-in browser:

```bash
rr login           # tries Chrome/Arc/Brave/Edge, first valid session wins
rr doctor          # show which sessions were found and which resolved
```

Manual fallback — paste the `sessionid` cookie (devtools → Application → Cookies
→ `https://pms.rentalready.io` → `sessionid`):

```bash
rr auth                          # prompts, hidden input
rr auth --sessionid <value>
```

`$RENTALREADY_SESSIONID` overrides everything. The resolved session is stored
chmod-600 in `~/.config/rentalready-cli/config.json` (alongside the discovered
property id). A command that redirects to `/account/login/` means the session
expired — log back into `pms.rentalready.io` in your browser and re-run
`rr login`.

## Commands

Every read command accepts `--json` for piping into other tools / agents.

### `rr overview`
Current-month KPIs: occupancy rate (booked / available / owner nights), net
revenue, average daily rate, and the guest currently checked in.

### `rr reservations [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--platform airbnb|booking|hoststay]`
Reservations with the **full financial breakdown** — rental revenue,
commission, cleaning revenue/fee, platform fee, payment fee, tourist tax, net
revenue — per reservation, **plus period totals** (nights, travelers, and every
column summed). Defaults to the 1st of the current month → today. Each row also
carries the guest name, nights, adults/children and platform.

The underlying table paginates at 10 rows/page; the command **follows every
page automatically** so the full period is returned (the per-row sums reconcile
exactly with the totals row). The JSON output includes `count` and `pages`.

### `rr projection [--fill]`
Projected **annual net revenue**. A trailing-12-month sum understates a matured
year because the property's first season ran at ramp-up prices; instead, for
each of the 12 calendar months this uses the **most recent year that has data**
(so Jul/Aug come from the latest season, not the first) and sums them. It also
prints the naive trailing-12-month figure for comparison. `--fill` scales a
peak month that is still under-booked (e.g. an August not yet fully booked) from
its current nightly rate up to the best occupancy that month has historically
reached, so an in-progress season isn't undercounted.

### `rr property`
Property info sheet: name, status, address, owner contact, Wi-Fi name/password,
entry codes, parking / bins / breaker / water-shutoff locations.

### `rr profile [--reveal]`
Owner profile: identity, address, payout bank details. **IBAN, BIC, phone and
date of birth are masked** unless `--reveal` is passed.

### `rr whoami`
The logged-in owner (name, email) and their property.

### `rr get <path> [--text] [--json]`
Escape hatch — fetch any owner path and print raw HTML (`--text` for readable
text, `--json` if it returns JSON). Use for surfaces without a typed command:
`/authentification/host_calendars/`, `/authentification/host_analytics/`,
`/authentification/host_feed/`, `/authentification/host_notifications/`.

### `rr doctor`
Diagnose session resolution: env var, stored config, browser sessions found,
and the resolved property id.

## Caching

Owner content changes slowly, and the portal is slow (~4 s/request), so
`overview`, `property` and `reservations` cache their GET responses on disk
(`~/.cache/rentalready-cli/`, TTL 6 h — override with `$RR_CACHE_TTL` seconds).
A warm `reservations` over a year drops from ~30 s to ~0.2 s. Pass `--refresh`
on any of them to bypass and rewrite the cache. `profile`/`whoami` are **never**
cached — they carry IBAN/BIC/DOB, which must not touch a plaintext cache.

## What is NOT exposed as a typed command

The **calendar**, **analytics** charts and **guest reviews** are rendered
client-side (Highcharts / JS), so they aren't parsed into typed output — reach
them with `rr get <path> --text`, or open the portal in a browser.

## Tests

```bash
uv run --with pytest --with click --with requests --with beautifulsoup4 \
  --with lxml --with pycryptodome python -m pytest tests/ -q
```

## Project layout

```
rentalready-cli/
  SKILL.md            # this file
  README.md
  bin/rr              # PEP 723 launcher — invoke this (session client + parsers)
  tests/test_rr.py    # unit tests for the pure parsing helpers
```
