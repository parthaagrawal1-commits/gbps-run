# TrueSpeed – deploy & growth guide

One file (`index.html`), no backend, no build step. Test data comes from Cloudflare's
public speed endpoints (`speed.cloudflare.com`), which Cloudflare runs from 300+ cities,
so the server is close to every visitor and you pay nothing for bandwidth.

## What it measures (and why it beats the usual tests)

| Metric | How | Why it matters |
|---|---|---|
| Download / upload | Multi-stream (5→8 down, 3→6 up), adaptive, steady-state average with warm-up excluded, plus peak | Accurate on gigabit plans; single-stream tests read low |
| Ping, jitter, packet loss | 12 idle probes, server processing time subtracted via `Server-Timing` | True network latency, not server time |
| **Ping under load + Bufferbloat grade (A+–F)** | Pings every 250 ms *during* download and upload | The #1 cause of "fast plan but calls freeze"; most tests never show it |
| Consistency % | Variance of 500 ms throughput windows | Spots flaky Wi‑Fi that averages look fine on |
| Real-world verdicts | 8 use cases graded Great/OK/Weak with a plain-English reason | People don't want numbers, they want "will Zoom work" |
| Plan check + advice | Enter plan speed, Wi‑Fi/wired toggle → % of plan and specific fixes | Turns a number into an action |
| Download-time calculator | 4K movie, 100 GB game, phone update, backup | Makes speed tangible |
| History + chart + monitor mode | localStorage; auto-test every 5–60 min while open | Catch evening slowdowns, prove ISP issues |
| Share | Copy summary, result PNG card, native share sheet | Free distribution |
| No ads, no tracking, dark/light, keyboard, mobile-first, ~50 KB | | Loads instantly; people come back |

## Deploy in 2 minutes (free)

**Cloudflare Pages (recommended – same network as the test servers):**
1. Go to dash.cloudflare.com → Workers & Pages → Create → Pages → **Upload assets**.
2. Name the project, drag `index.html` in, deploy. You get `https://yourname.pages.dev`.
3. Custom domain: Pages project → Custom domains → add `speed.yourdomain.com` (or buy a domain in Cloudflare Registrar, ~$10/yr).

Also works on Netlify Drop, Vercel, GitHub Pages, or any static host.

**Before deploying, edit these lines in `index.html`:**
- `<link rel="canonical" href="https://example.com/">` and `og:url` → your real URL.
- Rename "TrueSpeed" (search/replace) if you want your own brand.
- Optional: add an `og:image` (1200×630 PNG) so links unfurl nicely on social.

## Getting to 100,000 visits/month

Code gets you a product people prefer; traffic comes from distribution. In order of payoff:

1. **Own a domain with intent keywords** – e.g. `speedcheck.pro`, `wifispeedtest.app`. The page already ships title/description, FAQ schema, and WebApplication schema for rich results.
2. **Add one page per intent** (copy index.html, change the title/H1/FAQ): "WiFi speed test", "Xfinity speed test", "Starlink speed test", "bufferbloat test", "upload speed test", "gaming ping test". Long-tail ISP + speed-test queries are huge and under-served. Link them all to each other.
3. **Submit to Google Search Console + Bing Webmaster**, add a sitemap.xml listing those pages.
4. **Reddit/communities**: r/HomeNetworking, r/wifi, r/Comcast_Xfinity, r/Starlink – answer "is my speed normal?" posts with the bufferbloat angle (no other free test grades it clearly). Don't spam; be useful.
5. **Embeddable widget**: offer `<iframe src="https://yoursite/?auto=1">` for forum signatures, router-review blogs, ISP comparison sites. Every embed is a backlink.
6. **Shareable result cards**: the PNG card + copy summary already carry your URL. Encourage "post your result" threads.
7. **Product Hunt / Hacker News launch**: angle = "a speed test that grades bufferbloat and tells you if Zoom will work, no ads, 50 KB."
8. **YouTube/TikTok shorts**: "Why your gigabit plan still lags on calls" → demo the bufferbloat grade. Tech creators love a free, clean tool to link.
9. **Analytics**: add Cloudflare Web Analytics (free, cookie-free, one script tag) to see what's working.

Realistic ramp: a few thousand/month from SEO in months 2–3, then compounding as intent pages rank; one good Reddit/HN hit can bring 20–50k in a day.

## Notes / limits
- Runs entirely in the browser; the only data sent anywhere is random test bytes to Cloudflare.
- Browsers can't tell Wi‑Fi from Ethernet reliably, hence the manual toggle.
- Over ~2.5 Gbps, the browser itself becomes the bottleneck; fine for 99.9% of users.
- If you later want your own test servers, swap the `CF` constant for any endpoint that serves `/__down?bytes=N` and accepts POST on `/__up` with CORS enabled.
