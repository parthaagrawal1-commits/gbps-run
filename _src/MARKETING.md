# gbps.run — launch & growth playbook

Target: **100,000 visits/month**. That's ~3,300/day. Realistic timeline: 6–12 months, with
SEO intent pages doing the heavy lifting and 2–3 launch spikes along the way.

---

## 0. Deploy tonight (Hostinger, 5 minutes)

1. In hPanel: **Websites → Add website → "I have a website" / "Use existing files"** → choose **gbps.run** as the domain. (If you connected the domain to the Business plan, it will create a `domains/gbps.run/public_html` folder.)
2. Open **File Manager** for gbps.run → go into `public_html` → **Upload** `gbps-run-site.zip` → right-click → **Extract** → delete the zip. Make sure `.htaccess`, `index.html`, `sitemap.xml`, `og.png` are directly inside `public_html` (not inside a subfolder).
3. hPanel → **Security → SSL** → make sure SSL is active for gbps.run and "Force HTTPS" is on.
4. Visit https://gbps.run — run a test. Then open https://gbps.run/bufferbloat-test/ and https://gbps.run/sitemap.xml.
5. Add analytics: sign up for **Cloudflare Web Analytics** (free, cookie-free) → copy the one-line snippet → in `build.py` set `ANALYTICS = "<script ...>"` → rebuild → re-upload. (Or Plausible/Umami.)

To change anything later: edit `build.py` / `template.html` → `python3 build.py` → upload `site/`.

---

## 1. Week 1 — Search foundations (do once, compounds forever)

- **Google Search Console** → add property `gbps.run` (DNS verification in Hostinger) → submit `https://gbps.run/sitemap.xml` → "Request indexing" on the home page and 5 ISP pages.
- **Bing Webmaster Tools** → same (import from GSC in one click). Bing powers DuckDuckGo and Copilot answers.
- Make sure every page returns 200 over HTTPS, no www. (`.htaccess` handles this.)
- Check rich results: https://search.google.com/test/rich-results on the home page (FAQ + WebApplication schema should show).
- Add the site to your Hostinger domain's DNS as-is; **don't** put Cloudflare proxy in front unless you want to — not required.

## 2. Weeks 1–4 — Intent pages (the volume engine)

You already have 20. Add one per day. The template makes each one 10 minutes of writing:

**Next ISP pages (US):** Frontier Fiber, CenturyLink, Optimum, Mediacom, WOW, Astound/RCN, Brightspeed, Ziply, Metronet, Kinetic by Windstream, Hughesnet, Viasat, Verizon 5G Home, Spectrum Mobile.
**Device/platform:** PS5 speed test, Xbox speed test, Nintendo Switch, Steam download speed, Roku/Fire TV buffering, MacBook Wi‑Fi slow, Chromebook.
**Problem pages:** "internet slow at night", "why is my upload speed so slow", "packet loss test", "jitter test", "is 100 Mbps enough", "is 300 Mbps enough", "is 500 Mbps enough", "is 1 Gbps worth it", "how much speed do I need for 4 people".
**International (same template, local ISP names):** UK (BT, Virgin Media, Sky), Canada (Rogers, Bell, Telus), Australia (NBN, Telstra), India (Jio, Airtel), Germany (Telekom, Vodafone), Brazil (Vivo, Claro).

Rules: unique title/H1/intro/FAQ per page; link every page to every other via the nav (already automatic); never duplicate paragraphs across pages.

## 3. Weeks 2–6 — Launch spikes

**Show HN** (Tuesday–Thursday, 8–10am ET):
> **Show HN: gbps.run – a 50 KB speed test that grades bufferbloat and tells you if Zoom will work**
> Body: "I built this after buying a gigabit plan and still getting frozen video calls. Most speed tests only show download/upload; the thing that actually ruins calls and games is latency under load (bufferbloat). gbps.run runs 8 parallel streams against Cloudflare's nearest edge, pings during the load, grades A+–F, and gives plain-English verdicts for 4K/Zoom/gaming/WFH. No ads, no accounts, results stay in localStorage. Single HTML file, happy to answer questions about the measurement method."

**Product Hunt**: tagline "The speed test that tells you *why* your internet feels slow." Launch Tuesday 12:01am PT. First comment = the HN body above. Ask 10 friends to be online at launch.

**Reddit (be useful, never spam; 1 link per 10 helpful comments):** r/HomeNetworking, r/wifi, r/Comcast_Xfinity, r/Spectrum, r/Starlink, r/tmobileisp, r/fios, r/GoogleFiber, r/Ubiquiti, r/openwrt (bufferbloat crowd will love the grade). Template reply to "is my speed normal?" posts:
> "Download looks fine for your plan. The number that'd explain the stutter is ping under load — most tests don't show it. Run gbps.run/bufferbloat-test and post the grade; if it's C or worse, SQM on the router fixes it."

**Bufferbloat community**: post on the bufferbloat.net mailing list / r/openwrt asking for method feedback. These people are opinion leaders for router reviews.

## 4. Months 2–6 — Compounding channels

- **Embed program**: every router review blog, ISP forum and tech help site that embeds `<iframe src="https://gbps.run/embed/">` is a permanent backlink + traffic. Email 50 of them (template below).
- **YouTube/TikTok creators** (home-networking, "fix your Wi‑Fi" channels): offer the bufferbloat angle — "why your gigabit plan still lags" is a proven title format. Give them the embed and a shout-out; ask for a link in the description.
- **"Is [ISP] down?" pages**: outage searches spike into the millions on a bad day. A page per big ISP with "check if it's down for you: run the test + current status links" catches that traffic. Build these once the first 40 pages are indexed.
- **Share loop**: the result card already carries gbps.run. Add a line under results: "Post your grade — tag #gbpsrun" and run a monthly "worst bufferbloat grade" thread on Reddit.
- **Wikipedia-style comparison pages**: "Ookla vs fast.com vs gbps.run — what each measures" is a high-intent comparison query.

**Outreach email (blogs/forums):**
> Subject: free embeddable speed test with bufferbloat grading for [site]
> Hi [name] — I run gbps.run, a free, ad-free speed test. It's the only free one I know of that grades bufferbloat (ping under load) and explains results in plain English. It's embeddable with one iframe and adds a useful interactive element to router/ISP reviews. Zero tracking, no branding beyond a small "powered by" link. Happy to add a custom preset for your audience (e.g. plan speed pre-filled). Would it be useful on [specific page]? — [you]

## 5. Measure (weekly)

| Metric | Where | Month 1 | Month 3 | Month 6 | Month 12 |
|---|---|---|---|---|---|
| Visits/month | analytics | 5k | 25k | 60k | 100k+ |
| Indexed pages | Search Console | 20 | 60 | 120 | 200 |
| Pages ranking top-10 | Search Console | 2 | 15 | 40 | 80 |
| Referring domains | Search Console "Links" | 5 | 25 | 80 | 200 |
| Tests run / visit | add an event to analytics | >0.7 | | | |

If after 8 weeks the ISP pages aren't getting impressions in Search Console, the fix is more backlinks (embeds, HN, Reddit), not more pages.

## 6. Things that will quietly kill it

- Adding ads early. Speed-test visitors bounce in 30 seconds; ads pay pennies and cost trust. Monetise later with a single affiliate line ("better router for gigabit → [link]") if at all.
- Using "Speedtest" as a brand word anywhere in titles. Ookla owns the trademark.
- Letting the domain lapse. Set auto-renew on gbps.run today.
- Slow hosting. Check https://pagespeed.web.dev for gbps.run monthly; the page should score 95+ on mobile.
