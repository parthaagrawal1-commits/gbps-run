# gbps.run — Backlink Playbook

Goal: 30–50 referring domains in 6 months. Everything here is either (a) automated already,
(b) a 2-minute paste for the owner, or (c) delegable to a VA for ~$50–100/month.

Site facts to paste anywhere a form asks:
- Name: gbps.run — Internet Speed Test
- Tagline: Free speed test with bufferbloat grade. No ads, no tracking, no app.
- Description (short): gbps.run measures download, upload, ping, jitter and — unlike most tests —
  latency under load (bufferbloat), then tells you in plain English whether your connection is good
  enough for 4K, video calls, gaming and WFH. Runs in the browser, no ads, no accounts. English,
  Spanish, Portuguese, Hindi. Free to embed on any site.
- Category: Network tools / Utilities / Internet
- Alternatives to: Speedtest by Ookla, Fast.com, Waveform Bufferbloat Test, Cloudflare Speed Test
- Logo: https://gbps.run/og.png (1200×630). Badge: https://gbps.run/badge.svg
- Pricing: Free. Platforms: Web (any browser). Launched: November 2026.

## A. Automated (no owner action)
1. **Embed = backlink.** The embed snippet on every page now includes a visible
   `Speed test by <a href="https://gbps.run/">gbps.run</a>` line plus an optional badge
   (`/badge.svg`). Every site that embeds the test gives us a crawlable link.
2. **Daily agent** (scheduled task) appends 5 new, deduplicated prospects per day to
   `_src/outreach/prospects.md` with contact URL + a tailored 4-line pitch. Owner or VA sends.
3. **Outage pages** (`/is-xfinity-down/` etc.) earn natural links on outage days from Reddit/X threads.

## B. Owner: one session, ~45 min total (highest value per minute)
Do these once. Each is a form; copy from "Site facts" above.

| # | Where | Why | Time |
|---|-------|-----|------|
| 1 | GitHub → make `gbps-run` repo **public**, add topics `speed-test bufferbloat internet-speed latency network-tools`, README first line links https://gbps.run | DR 95 domain, instant, indexed | 3 min |
| 2 | **AlternativeTo** → alternativeto.net/manage-item/ add gbps.run as alternative to Speedtest, Fast.com, Waveform Bufferbloat Test, Cloudflare Speed Test | DR 80, "X alternatives" is high-intent traffic | 10 min |
| 3 | **Product Hunt** → schedule launch for a Tuesday 12:01 AM PT; title "gbps.run — speed test that grades your bufferbloat"; first comment = why it exists (your real story: bought RS300, fast.com vs Safari mismatch) | DR 91 + launch-day traffic | 15 min |
| 4 | **Hacker News** → Show HN: "gbps.run – browser speed test that measures latency under load, no ads" (post Tue–Thu 8–10 AM ET; answer every comment for 2 h) | Tech links + possible roundup pickups | 5 min + follow-up |
| 5 | **SaaSHub, Slant, Uneed, DevHunt, Peerlist, Indie Hackers (product page), Startup Stash, LaunchingNext, SideProjectors** | Easy do-follow/nofollow mix; each ~2 min | 15 min |

## C. Community posts (genuine, not spammy — one post each)
- **OpenWrt forum** thread "2025: current recommendations for bufferbloat testing"
  (forum.openwrt.org/t/241303): reply describing how gbps.run measures loaded latency
  (2 warm-up probes discarded, 12-sample median, loaded ping every 250 ms, A+–F grade thresholds
  5/30/60/200/400 ms), ask for feedback. That crowd links to tools they trust.
- **bufferbloat.net** "Tests for Bufferbloat" wiki — email the bloat list
  (lists.bufferbloat.net/listinfo/bloat) asking for a listing; include methodology.
- **r/HomeNetworking, r/Ubiquiti, r/openwrt, r/Starlink, r/Xfinity, r/JioFiber, r/Airtel, r/IndianGaming** —
  never post the link cold; answer real questions and link only when it directly helps.
- **Quora** — Hindi + English answers under "Jio Fiber", "Airtel Xstream", "Internet speed".

## D. Outreach targets found so far (pitch the free embed, or a cite in an existing article)
Roundups that already list speed tests (ask to be added; offer the bufferbloat angle they lack):
- pixelscan.net/blog/free-internet-speed-tests-2026/
- analyticsinsight.net — "Best Websites to Test Your Internet Speed in 2026" (author Pardeep Sharma)
- propakistani.pk/how-to/top-10-internet-speed-testing-websites/
- internetadvisor.com/internet-speed-test-sites
- geeksforgeeks.org/best-internet-speed-test-sites/
India blogs/news (pitch Hindi test + Jio/Airtel pages):
- telecomtalk.info (data story: "what Jio/Airtel users actually measure" once we have volume)
- techmitra.in (ran a Jio AirFiber latency-under-load test — our bufferbloat grade is exactly their angle)
- diablotechblog.blogspot.com (JioFiber vs AirFiber comparison — offer embed)
Bufferbloat explainers that cite only Waveform (offer a second tool):
- blog.oppedahl.com/?p=12346, hamradio.my (bufferbloat article), admin-magazine.com "Managing Bufferbloat"

### Outreach email (roundup)
Subject: a speed test your 2026 roundup is missing (bufferbloat grade, no ads)

Hi {name}, I read your "{article}" — good list. One gap: none of the tools measure latency *under load*,
which is what actually makes video calls stutter on a "fast" connection. I built gbps.run, a free,
ad-free browser test that grades bufferbloat A+–F alongside download/upload/ping, and detects when
iCloud Private Relay or a VPN is skewing results. Works in Hindi/Spanish/Portuguese too.
If it fits, I'd be grateful for a mention; happy to send a comparison screenshot vs fast.com.
— {owner name}, gbps.run

### Outreach email (embed)
Subject: free speed-test widget for {site}

Hi {name}, your readers on {topic} constantly ask "is my speed normal?" You can answer it on-page:
one line of HTML embeds gbps.run (free, no ads, no tracking, grades bufferbloat too):
`<iframe src="https://gbps.run/embed/" width="100%" height="560" style="border:0"></iframe>`
No signup, nothing to maintain. Happy to make a version preset to {ISP}'s plan tiers if useful.
— {owner name}

## E. Delegate it (if the owner has no time)
Post on Upwork/Fiverr: "Submit my free web tool to ~25 directories and send ~40 outreach emails
from a prepared list. All copy and targets provided (BACKLINKS.md + prospects.md). Report links in a
sheet. Fixed price $60–120." Give the VA a dedicated mailbox like hello@gbps.run (Hostinger email).

## F. What NOT to do
- No paid link packages, PBNs, or Fiverr "1,000 backlinks" — Google penalties outweigh any gain.
- No Wikipedia edits adding gbps.run — it will be reverted and flagged as spam.
- No mass DMs. One helpful comment is worth more than 50 drive-by links.
