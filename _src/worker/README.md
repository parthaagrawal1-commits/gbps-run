# gbps.run speed-test backend (Cloudflare Worker, free plan)

`worker.js` serves the same three endpoints the page uses — `/__down?bytes=N`, `POST /__up`, `/meta` — so the test runs
against gbps.run's own backend instead of the shared `speed.cloudflare.com`, which rate-limits busy clients (HTTP 429)
and makes tests collapse to zero. The page tries this backend first and falls back to Cloudflare's endpoint if it is
unreachable or over quota, so deploying it can only improve things.

## One-time deploy (about 5 minutes, no card needed)

Option A — dashboard, no tools:
1. Log in at dash.cloudflare.com → **Workers & Pages** → **Create** → **Create Worker** → name it `gbps-speed` → **Deploy**.
2. Click **Edit code**, replace the contents with `worker.js` from this folder, **Deploy**.
3. Note the URL it prints (`https://gbps-speed.<your-subdomain>.workers.dev`). Open `<that url>/meta` in a browser — you should see JSON with your city and ISP.

Option B — command line: `cd _src/worker && npx wrangler login && npx wrangler deploy`.

## Point the site at it
- If gbps.run's DNS is on Cloudflare: Worker → **Settings → Domains & Routes → Add → Custom domain** → `speed.gbps.run`. Done; the page already uses that hostname.
- If DNS is elsewhere (e.g. Hostinger): edit `BACKENDS[0]` in `_src/build.py` to the workers.dev URL, run `python3 build.py`, `cp -r site/. ..`, commit and push.

## Free-plan limits and what happens at them
- 100,000 requests/day (resets midnight UTC), 10 ms CPU per request, 100 MB max upload body, no response-size limit for streamed responses.
- A full test uses roughly 15–30 requests, so the free plan covers on the order of 3,000–6,000 tests/day. Past the quota Cloudflare returns error 1027; the page then silently uses `speed.cloudflare.com` for the rest of the day.
- The Worker stores nothing and logs nothing.
