#!/usr/bin/env python3
"""Builds the gbps.run static site into ./site from template.html.
Run: python3 build.py   →  upload the contents of ./site to public_html on Hostinger."""
import json, os, shutil, html, datetime

ROOT = "https://gbps.run"
OUT = "site"
TEMPLATE = open("template.html", encoding="utf-8").read()
ANALYTICS = "<!-- Analytics: paste your Cloudflare Web Analytics or Plausible snippet here -->"

def faq_html(faqs, first_open=True):
    out = []
    for i, (q, a) in enumerate(faqs):
        out.append(f'      <details{" open" if i == 0 and first_open else ""}><summary>{html.escape(q)}</summary><p>{a}</p></details>')
    return "\n".join(out)

def faq_json(faqs):
    import re
    return ",".join(json.dumps({"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": re.sub(r"<[^>]+>", "", a)}}) for q, a in faqs)

GENERIC_FAQ = [
    ("What is a good internet speed?", "For one person, 25–50 Mbps download covers 4K streaming and video calls. A household with several people streaming, gaming and working from home is comfortable at 100–300 Mbps. Upload matters more than most people think: 10 Mbps or more keeps video calls sharp and lets backups finish."),
    ("Why is my Wi‑Fi slower than my plan?", "Wi‑Fi loses speed through walls and distance, shares airtime with neighbours, and older devices cap the link. Test in the same room as the router, use the 5 GHz or 6 GHz band, and compare with a wired test to see whether the limit is Wi‑Fi or your provider. On a gigabit plan, 800–940 Mbps on Wi‑Fi is excellent."),
    ("What is bufferbloat and why does it matter?", "Bufferbloat is the rise in ping when your connection is busy, for example during a big download. It's why video calls freeze when someone else starts a backup. We measure ping while loading the line and grade the increase: A means almost no change, F means hundreds of milliseconds. Routers with SQM or \"smart queue\" settings fix it."),
    ("Why do different speed tests give different numbers?", "Tests use different servers, open a different number of parallel connections and average differently. Single-connection tests often read low on fast plans. Compare trends over a few runs rather than one number."),
    ("What do ping and jitter mean?", "Ping is the round-trip time to the server. Under 20 ms is excellent, under 50 ms is great for gaming, and 100 ms+ feels sluggish. Jitter is how much ping varies; low jitter keeps calls and games smooth."),
    ("How accurate is this test?", "It opens up to eight parallel connections to Cloudflare's nearest data centre (usually within a few hundred miles of you), ignores the first two seconds of ramp-up and averages the steady state. That mirrors how Ookla-style tests work and reads correctly on gigabit plans. Over about 2.5 Gbps the browser itself becomes the bottleneck."),
]

# slug, title, description, h1, intro, plan_preset, faqs, nav_label
PAGES = [
    dict(slug="", nav="Speed test", plan=0,
         title="gbps.run – Free Internet Speed Test (Download, Upload, Ping, Bufferbloat)",
         desc="Free, ad-free internet speed test. Measures download, upload, ping, jitter and bufferbloat, then tells you in plain English whether your connection handles 4K streaming, gaming, video calls and working from home.",
         h1="Internet speed test",
         intro="Download, upload, ping, jitter and bufferbloat in about 25 seconds — then plain-English verdicts on what your connection can actually handle. No ads, no sign-up.",
         faqs=GENERIC_FAQ),
    dict(slug="wifi-speed-test", nav="Wi‑Fi", plan=0,
         title="Wi‑Fi Speed Test – How Fast Is Your Wi‑Fi Really? | gbps.run",
         desc="Test your Wi‑Fi speed from any phone or laptop. See download, upload, ping and bufferbloat, compare it with your plan, and learn why Wi‑Fi is slower than wired.",
         h1="Wi‑Fi speed test",
         intro="Run this on your phone or laptop over Wi‑Fi, then once more next to the router. The gap between the two is what your walls, distance and router are costing you.",
         faqs=[("Why is Wi‑Fi slower than my plan?", "Every wall and metre of distance costs signal; 2.4 GHz is slow and crowded; older routers and devices cap the link. Expect 50–90% of your plan near the router and far less in distant rooms."),
               ("How do I get faster Wi‑Fi?", "Put the router up high and in the open, use the 5 GHz or 6 GHz band for nearby devices, turn on 160 MHz channels on Wi‑Fi 6/6E/7 routers, update firmware, and add a wired access point or mesh node for far rooms."),
               ("Should I test wired too?", "Yes. If an Ethernet test is near your plan speed and Wi‑Fi is far below, the fix is on your side (router, placement, band). If wired is also slow, contact your provider."),
               ("What Wi‑Fi speed do I need?", "25 Mbps per 4K stream, 5–10 Mbps per video call, under 50 ms ping for gaming. Most homes are comfortable with 100–300 Mbps actually delivered over Wi‑Fi.")]),
    dict(slug="xfinity-speed-test", nav="Xfinity", plan=0,
         title="Xfinity Speed Test – Are You Getting the Speed You Pay For? | gbps.run",
         desc="Independent speed test for Xfinity (Comcast) internet. Check download, upload, ping and bufferbloat, enter your plan and see the percentage you're actually getting.",
         h1="Xfinity speed test",
         intro="An independent test for Xfinity customers. Enter your plan speed after the test to see exactly what percentage you're getting — and whether the shortfall is Wi‑Fi or the line.",
         faqs=[("What speeds should I get on Xfinity?", "Xfinity cable plans typically range from about 150 Mbps to 2 Gbps download depending on your area, with upload speeds that are much lower on most tiers (often 10–35 Mbps, higher in upgraded markets). Gigabit plans are commonly provisioned slightly above 1,000 Mbps, so a wired test near 940 Mbps is normal."),
               ("Why is my Xfinity upload so slow?", "Cable networks dedicate far more capacity to download than upload. That's by design, not a fault. If upload matters for you (video calls, backups, streaming), check whether an upgraded tier or fibre is available at your address."),
               ("My Xfinity speed is low — what do I check first?", "Run a wired test. If it's also low, restart the modem, check the coax connections, and test at a quiet time. If it stays low, ask Xfinity to check signal levels. If wired is fine but Wi‑Fi is slow, the fix is the router or its placement."),
               ("Is this the official Xfinity speed test?", "No. gbps.run is independent and not affiliated with Comcast. It tests to Cloudflare's nearest server, which is a fair representation of real-world internet performance rather than a test inside the provider's own network.")]),
    dict(slug="spectrum-speed-test", nav="Spectrum", plan=0,
         title="Spectrum Speed Test – Check Your Real Download & Upload Speed | gbps.run",
         desc="Independent speed test for Spectrum internet. Measure download, upload, ping and bufferbloat and compare with your 300 Mbps, 500 Mbps or Gig plan.",
         h1="Spectrum speed test",
         intro="Independent test for Spectrum customers. Spectrum plans are usually 300 Mbps, 500 Mbps or 1 Gig — enter yours after the test to see what you're really getting.",
         faqs=[("What speed should Spectrum deliver?", "Spectrum's main tiers are around 300, 500 and 1,000 Mbps download. Upload is typically 10–35 Mbps on cable, with higher uploads in markets that have been upgraded. Wired tests at 85–95% of the plan are normal; Wi‑Fi will be lower."),
               ("Why is Spectrum slow in the evening?", "Cable is shared with your neighbourhood, so 7–11 pm can be congested. Use monitor mode on this page to log speeds across a day; if evenings are consistently far lower, that's useful evidence when you contact Spectrum."),
               ("Should I use Spectrum's router?", "The provided router is fine for basic use but often lacks Wi‑Fi 6/6E/7 and good bufferbloat handling. Many customers get better Wi‑Fi from their own router in bridge mode."),
               ("Is this affiliated with Spectrum?", "No. gbps.run is an independent, ad-free test and is not affiliated with Charter or Spectrum.")]),
    dict(slug="att-speed-test", nav="AT&T", plan=0,
         title="AT&T Speed Test – Fiber & Internet Air | gbps.run",
         desc="Independent speed test for AT&T Fiber and AT&T Internet. Check symmetrical fibre speeds, ping and bufferbloat and compare with your plan.",
         h1="AT&T speed test",
         intro="For AT&T Fiber and AT&T Internet customers. Fibre plans are symmetrical, so your upload should be close to your download — this test shows both.",
         faqs=[("What should AT&T Fiber speeds look like?", "AT&T Fiber tiers are symmetrical (for example 300, 500, 1,000, 2,000 and 5,000 Mbps), so upload should roughly match download. A 1 Gig plan tests around 900–940 Mbps wired; multi-gig plans need a 2.5 Gbps or faster port to show more than ~940 Mbps."),
               ("Why does my AT&T gigabit test show only 940 Mbps?", "A standard gigabit Ethernet port tops out at about 940 Mbps of usable throughput. That's the cable, not AT&T. Over Wi‑Fi, 600–900 Mbps is a good result."),
               ("AT&T Internet Air is slow — is that normal?", "Internet Air is fixed wireless (5G), so speeds vary with signal and congestion, commonly 75–225 Mbps. Try moving the gateway near a window facing the tower."),
               ("Is this the official AT&T test?", "No. gbps.run is independent and not affiliated with AT&T.")]),
    dict(slug="verizon-fios-speed-test", nav="Verizon Fios", plan=0,
         title="Verizon Fios Speed Test – Check Your Fibre Speed | gbps.run",
         desc="Independent speed test for Verizon Fios and Verizon 5G Home. Measure symmetrical download and upload, ping, jitter and bufferbloat.",
         h1="Verizon Fios speed test",
         intro="Fios is symmetrical fibre, so upload should be close to download. If it isn't, something between the ONT and your device is the limit.",
         faqs=[("What speeds should Fios give me?", "Fios tiers are symmetrical, commonly 300, 500, 1 Gig and 2 Gig. Wired gigabit tests at about 900–940 Mbps are normal. The 2 Gig plan needs a multi-gig port to show more."),
               ("My Fios upload is lower than download — why?", "Fios should be symmetrical. If upload is far lower, test wired; Wi‑Fi uplink is often weaker than downlink on phones. If wired upload is also low, check the router and contact Verizon."),
               ("Is Verizon 5G Home slower than Fios?", "Usually yes. 5G Home speeds vary with signal and congestion, often 85–300 Mbps and higher in strong Ultra Wideband areas. Ping is also higher than fibre."),
               ("Is this affiliated with Verizon?", "No. gbps.run is independent and ad-free.")]),
    dict(slug="t-mobile-home-internet-speed-test", nav="T‑Mobile Home", plan=0,
         title="T‑Mobile Home Internet Speed Test – 5G Gateway Check | gbps.run",
         desc="Speed test for T‑Mobile 5G Home Internet. See download, upload, ping and bufferbloat, and learn how gateway placement changes your speed.",
         h1="T‑Mobile Home Internet speed test",
         intro="5G home internet lives and dies by signal. Run this test, move the gateway to a different window, and run it again — the difference can be huge.",
         faqs=[("What speeds are normal on T‑Mobile Home Internet?", "T‑Mobile quotes typical download speeds roughly in the 87–415 Mbps range and uploads of about 14–56 Mbps, depending on signal and network load. Ping is typically higher than cable or fibre."),
               ("How do I make it faster?", "Placement is everything: high up, near a window, facing the nearest tower, away from metal and thick walls. The T‑Mobile app shows signal bars; a 5G signal on the n41 band gives the best speeds."),
               ("Why does the speed change through the day?", "It's shared cellular capacity, so evenings in busy areas slow down. Use monitor mode on this page to log a full day."),
               ("Is this affiliated with T‑Mobile?", "No. gbps.run is independent.")]),
    dict(slug="starlink-speed-test", nav="Starlink", plan=0,
         title="Starlink Speed Test – Satellite Download, Upload & Latency | gbps.run",
         desc="Independent speed test for Starlink. Check download, upload, ping, jitter and bufferbloat, and see what's normal for satellite internet.",
         h1="Starlink speed test",
         intro="Satellite speed swings with weather, obstructions and how busy your cell is. Run a few tests at different times — and watch the ping and jitter, not just the download number.",
         faqs=[("What Starlink speeds are normal?", "Residential Starlink commonly delivers roughly 50–250 Mbps download, 10–25 Mbps upload and 25–60 ms ping, varying by region, time of day and plan. Brief drops are normal as satellites hand off."),
               ("Why is my Starlink slow right now?", "Common causes: obstructions (check the app's obstruction map), heavy rain or snow, a congested cell at peak hours, or Wi‑Fi limits inside the house. Test wired to the router to rule out Wi‑Fi."),
               ("Is Starlink good for gaming and calls?", "Usually fine for calls; gaming is playable but ping of 30–60 ms with occasional spikes isn't competitive-grade. Jitter and bufferbloat grades on this page tell you more than download speed."),
               ("Is this affiliated with Starlink or SpaceX?", "No. gbps.run is independent.")]),
    dict(slug="google-fiber-speed-test", nav="Google Fiber", plan=0,
         title="Google Fiber Speed Test – 1 Gig to 8 Gig | gbps.run",
         desc="Speed test for Google Fiber customers. Check symmetrical gigabit speeds, ping and bufferbloat, and learn why multi-gig plans need multi-gig hardware.",
         h1="Google Fiber speed test",
         intro="Google Fiber plans are symmetrical from 1 Gig up to 8 Gig. Over a standard gigabit port or Wi‑Fi you'll see up to ~940 Mbps; the faster tiers need 2.5G/10G hardware to show their full speed.",
         faqs=[("What should a Google Fiber test show?", "1 Gig wired: about 900–940 Mbps both ways. 2, 5 and 8 Gig: only as fast as your Ethernet port, Wi‑Fi and the browser allow — expect 900–2,300 Mbps on typical home gear."),
               ("Why doesn't my test show 2 Gbps?", "A gigabit Ethernet port caps at ~940 Mbps. You need a 2.5 Gbps port, a Wi‑Fi 6E/7 router with 160/320 MHz channels, and a recent device. Browsers also cap out around 2–3 Gbps."),
               ("Is this the Google Fiber official test?", "No. gbps.run is independent and not affiliated with Google.")]),
    dict(slug="cox-speed-test", nav="Cox", plan=0,
         title="Cox Speed Test – Check Your Real Internet Speed | gbps.run",
         desc="Independent speed test for Cox internet. Measure download, upload, ping and bufferbloat and compare against your Cox plan.",
         h1="Cox speed test",
         intro="Independent test for Cox customers. Enter your plan after the test to see the percentage delivered, and check the bufferbloat grade if calls or games stutter.",
         faqs=[("What speeds should Cox deliver?", "Cox tiers typically run from about 100 Mbps to 2 Gbps download, with uploads of roughly 5–100 Mbps depending on tier and market. Wired tests at 85–95% of plan are normal."),
               ("Why is Cox upload so low?", "Cable upload capacity is limited by design. If you need more, check whether an upgraded tier or fibre is available."),
               ("Is this affiliated with Cox?", "No. gbps.run is independent and ad-free.")]),
    dict(slug="quantum-fiber-speed-test", nav="Quantum Fiber", plan=0,
         title="Quantum Fiber Speed Test (CenturyLink Fiber) | gbps.run",
         desc="Speed test for Quantum Fiber and CenturyLink customers. Check symmetrical fibre speeds, ping, jitter and bufferbloat.",
         h1="Quantum Fiber speed test",
         intro="Quantum Fiber (formerly CenturyLink Fiber) is symmetrical. Upload should be close to download — if it isn't, the limit is on your side of the ONT.",
         faqs=[("What speeds should Quantum Fiber show?", "Common tiers are around 500 Mbps and 940 Mbps symmetrical, with multi-gig tiers in some areas. A 940 Mbps plan tests at about 900–940 Mbps wired."),
               ("Can I use my own router with Quantum Fiber?", "Yes. Most Quantum Fiber installs hand off plain Ethernet from the ONT, so your own router works. Some older CenturyLink lines need VLAN 201 tagging."),
               ("Is this affiliated with Quantum Fiber or Lumen?", "No. gbps.run is independent.")]),
    dict(slug="bufferbloat-test", nav="Bufferbloat", plan=0,
         title="Bufferbloat Test – Does Your Connection Lag When It's Busy? | gbps.run",
         desc="Free bufferbloat test. Measures ping while your connection is loaded and grades it A+ to F. Find out why video calls freeze and games lag even on fast plans.",
         h1="Bufferbloat test",
         intro="Fast download speed doesn't stop lag. Bufferbloat is the ping spike that happens when someone in the house downloads something — and it ruins calls and games. This test loads your line and measures exactly that.",
         faqs=[("What is bufferbloat?", "When your connection is saturated, routers and modems queue packets instead of dropping them, so everything waits in line. Ping that's 15 ms when idle can hit 300 ms+ under load. That's bufferbloat."),
               ("How is the grade calculated?", "We measure idle ping, then keep pinging during the download and upload phases. The increase is graded: A+ under 5 ms, A under 30, B under 60, C under 200, D under 400, F above that."),
               ("How do I fix bufferbloat?", "Turn on SQM, Smart Queue Management, fq_codel or CAKE on your router (OpenWrt, many ASUS, Ubiquiti, Firewalla, eero and others have it). Set the limits to ~90% of your real speeds. Grades typically jump from D/F to A."),
               ("Does a faster plan fix it?", "Not by itself. Bufferbloat is a queue-management problem, so a 1 Gbps plan can grade F while a well-managed 100 Mbps line grades A.")]),
    dict(slug="ping-test", nav="Ping", plan=0,
         title="Ping Test – Check Latency & Jitter for Gaming | gbps.run",
         desc="Free ping test for gamers. Measures latency, jitter, packet loss and ping under load (bufferbloat) in your browser — no app needed.",
         h1="Ping test for gaming",
         intro="For gaming, ping and jitter matter more than download speed. This test measures idle ping, jitter, packet loss and — the one most tests miss — ping while the line is busy.",
         faqs=[("What is a good ping for gaming?", "Under 20 ms is excellent, 20–50 ms is great, 50–100 ms is playable, over 100 ms is noticeable. Jitter under 10 ms keeps movement smooth."),
               ("Why does my game lag when someone else is streaming?", "That's bufferbloat — ping spikes under load. Check the bufferbloat grade; if it's C or worse, enable SQM/QoS on your router."),
               ("Why is Wi‑Fi ping higher than Ethernet?", "Wi‑Fi adds a few milliseconds and, more importantly, jitter from interference and retransmits. Serious gaming is best on a cable."),
               ("Is this ping to the game server?", "No — it's to the nearest Cloudflare data centre, which is a good proxy for your connection's baseline. Game servers add distance on top.")]),
    dict(slug="upload-speed-test", nav="Upload", plan=0,
         title="Upload Speed Test – Video Calls, Streaming & Backups | gbps.run",
         desc="Test your upload speed accurately. Multi-stream upload test with ping-under-load grading, plus what upload speed you need for Zoom, Twitch and cloud backups.",
         h1="Upload speed test",
         intro="Upload is the number providers don't advertise and the one that decides whether your video looks sharp on calls and how long backups take. This test measures it properly, with several parallel streams.",
         faqs=[("What upload speed do I need?", "Video calls: 3–5 Mbps per call for HD. Streaming to Twitch/YouTube: 6–10 Mbps for 1080p. Cloud backups and photo libraries: the more the better — 20 Mbps uploads 5 GB in about 35 minutes; 200 Mbps does it in under 4."),
               ("Why is my upload so much lower than download?", "Cable and many 5G home services are asymmetric by design. Fibre plans are symmetrical. If upload matters to you, that's the main reason to switch to fibre."),
               ("Why does upload read low on Wi‑Fi?", "Phones and laptops transmit with less power than the router, so uplink is often the weaker direction over Wi‑Fi. Test wired for the true number.")]),
    dict(slug="zoom-speed-test", nav="Video calls", plan=0,
         title="Zoom & Teams Speed Test – Is Your Internet Good Enough for Video Calls? | gbps.run",
         desc="Check whether your connection can handle Zoom, Teams, Google Meet and FaceTime. Tests upload, ping, jitter and bufferbloat — the four things that make calls freeze.",
         h1="Video call readiness test",
         intro="Calls don't freeze because of download speed. They freeze because of upload, jitter and ping spikes when the line is busy. This test checks all four and gives you a straight answer.",
         faqs=[("What internet speed does Zoom need?", "Zoom recommends about 3–4 Mbps up and down for HD group calls; Teams and Meet are similar. Almost any plan has that. What breaks calls is jitter over ~30 ms, packet loss, and bufferbloat when someone else downloads."),
               ("Why does my video freeze while audio continues?", "Video is dropped first when bandwidth or ping degrades. Check the jitter and bufferbloat grade; if they're poor, move closer to the router, use Ethernet, or enable QoS/SQM."),
               ("Should I use Ethernet for important calls?", "Yes. A cable removes Wi‑Fi jitter and is the single biggest reliability upgrade for work-from-home calls.")]),
    dict(slug="gaming-speed-test", nav="Gaming", plan=0,
         title="Gaming Speed Test – Ping, Jitter & Lag Check for PS5, Xbox, PC | gbps.run",
         desc="Is your internet good enough for online gaming? Test ping, jitter, packet loss, bufferbloat and download speed for PS5, Xbox, Switch and PC.",
         h1="Gaming internet test",
         intro="Lag isn't about download speed. It's ping, jitter, packet loss and what happens to your ping when someone else in the house starts a download. This test grades all of it.",
         faqs=[("What internet speed do I need for gaming?", "Most online games use under 1 Mbps. What you need is low ping (under 50 ms), low jitter (under 15 ms), zero packet loss and a bufferbloat grade of B or better. Download speed only matters for installing games."),
               ("Why do I lag when my speed test is fast?", "Bufferbloat: your ping spikes under load. Enable SQM or QoS on your router and put your console on Ethernet."),
               ("Is 5G home internet okay for gaming?", "Playable, but ping and jitter are higher and less stable than cable or fibre. Competitive players should prefer wired broadband.")]),
    dict(slug="4k-streaming-speed-test", nav="4K streaming", plan=0,
         title="4K Streaming Speed Test – Netflix, YouTube, Disney+ | gbps.run",
         desc="Check if your internet can stream 4K without buffering. See how many simultaneous 4K streams your connection supports.",
         h1="4K streaming speed test",
         intro="4K needs about 25 Mbps per stream, steady. This test shows your real download speed and consistency and tells you how many 4K streams your home can run at once.",
         faqs=[("How much speed does 4K need?", "Netflix recommends 15 Mbps for 4K, YouTube about 20 Mbps, and 25 Mbps is a safe figure that covers high-bitrate content. Multiply by the number of TVs streaming at once."),
               ("Why does Netflix buffer when my speed is fine?", "Consistency matters more than peak speed. If the consistency score here is low, Wi‑Fi interference or congestion is likely. Try 5 GHz, move the router, or wire the TV."),
               ("Does the TV's Wi‑Fi matter?", "Yes — many TVs have slow 2.4 GHz-only Wi‑Fi. A cheap Ethernet cable to the TV or a streaming stick on 5 GHz fixes most buffering.")]),
    dict(slug="ethernet-vs-wifi-speed-test", nav="Wired vs Wi‑Fi", plan=0,
         title="Ethernet vs Wi‑Fi Speed Test – Find Where Your Speed Goes | gbps.run",
         desc="Run the test on Wi‑Fi, then on Ethernet, and see exactly how much speed your Wi‑Fi is losing. History on this page keeps both results side by side.",
         h1="Ethernet vs Wi‑Fi speed test",
         intro="Run this twice: once on Wi‑Fi, once with a cable. Your history below keeps both. If wired is near your plan and Wi‑Fi isn't, the fix is your router or its placement — not your provider.",
         faqs=[("How much faster is Ethernet?", "On a gigabit plan a cable gives ~940 Mbps with ~1 ms added latency; good Wi‑Fi 6/6E/7 gives 600–900 Mbps nearby and far less through walls, plus more jitter."),
               ("My laptop has no Ethernet port — what now?", "A USB‑C to 2.5 GbE adapter costs about $20–30 and gives you the true wired number."),
               ("Wired is slow too — now what?", "Try another cable (Cat 5e or better) and port, restart modem then router, and test at a quiet time. If still low, the provider needs to look at the line.")]),
    dict(slug="5g-speed-test", nav="5G / mobile", plan=0,
         title="5G Speed Test – Mobile Data Speed on iPhone & Android | gbps.run",
         desc="Test your 5G or LTE speed in the browser, no app required. See download, upload, ping and jitter on your phone's cellular connection.",
         h1="5G mobile speed test",
         intro="Turn off Wi‑Fi, then run the test to measure your phone's 5G or LTE connection. No app, no permissions, nothing installed.",
         faqs=[("What 5G speeds are normal?", "Low-band 5G is often 50–150 Mbps; mid-band (such as T‑Mobile Ultra Capacity or Verizon Ultra Wideband) commonly delivers 300–1,000+ Mbps. Upload is usually 10–50 Mbps."),
               ("How much data does this test use?", "Typically 100–400 MB on a fast connection; the test adapts to your speed. Use the Quick setting in Settings if you're on a limited plan."),
               ("Why is my 5G ping higher than home internet?", "Cellular adds 20–40 ms by nature. It's fine for most uses but not ideal for competitive gaming.")]),
    dict(slug="gigabit-speed-test", nav="Gigabit", plan=1000,
         title="Gigabit Speed Test – Is Your 1 Gbps Plan Delivering? | gbps.run",
         desc="Accurate speed test for gigabit and multi-gig plans. Multi-stream testing that reads correctly at 1 Gbps+, with plan comparison and the hardware limits explained.",
         h1="Gigabit speed test",
         intro="Most tests read low on gigabit plans. This one opens up to eight parallel streams and ignores ramp-up, so it reads correctly at 1 Gbps and beyond. Your plan is pre-set to 1,000 Mbps below.",
         faqs=[("Why does my gigabit plan test at 940 Mbps?", "That's the usable ceiling of a gigabit Ethernet port after protocol overhead. It means your plan is delivering fully. Providers often provision 1.1–1.2 Gbps so that single-port users still see ~940."),
               ("What Wi‑Fi do I need for gigabit?", "A Wi‑Fi 6, 6E or 7 router with 160 MHz channels enabled, and a device that supports them (most 2021+ phones and laptops). Expect 700–900+ Mbps in the same room."),
               ("How do I test above 1 Gbps?", "A 2.5 GbE or 10 GbE port, a multi-gig router port, and a recent computer. Browsers cap around 2–3 Gbps; beyond that use a command-line tool like iperf3.")]),
]

NAV = "".join(f'<a href="/{p["slug"]}/">{p["nav"]}</a>' if p["slug"] else '<a href="/">Speed test</a>' for p in PAGES)

def render(p):
    url = f"{ROOT}/{p['slug']}/" if p["slug"] else f"{ROOT}/"
    out = TEMPLATE
    for k, v in {
        "{{TITLE}}": html.escape(p["title"]), "{{DESC}}": html.escape(p["desc"]), "{{URL}}": url,
        "{{H1}}": p["h1"], "{{INTRO}}": p["intro"], "{{FAQ_HEADING}}": "Understanding your results" if not p["slug"] else "Questions about this test",
        "{{FAQ_HTML}}": faq_html(p["faqs"]), "{{FAQ_JSON}}": faq_json(p["faqs"]), "{{NAV}}": NAV,
        "{{PLAN_PRESET}}": str(p["plan"] or 0), "{{ANALYTICS}}": ANALYTICS,
    }.items():
        out = out.replace(k, v)
    assert "{{" not in out, [l for l in out.split("\n") if "{{" in l][:3]
    return out

STATIC_PAGE = """<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title><meta name="description" content="{desc}"><link rel="canonical" href="{url}"><link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Ccircle cx='32' cy='32' r='30' fill='%230b0f17'/%3E%3Cpath d='M14 40a20 20 0 0 1 36 0' stroke='%233ee6a5' stroke-width='6' fill='none' stroke-linecap='round'/%3E%3Cpath d='M32 40 44 24' stroke='%23fff' stroke-width='5' stroke-linecap='round'/%3E%3C/svg%3E"><style>body{{font-family:Inter,system-ui,sans-serif;background:#0b0f17;color:#e8edf5;margin:0;line-height:1.6}}main{{max-width:720px;margin:0 auto;padding:24px 16px 60px}}a{{color:#5aa9ff}}h1{{letter-spacing:-.02em}}.btn{{display:inline-block;background:#3ee6a5;color:#06130d;font-weight:800;padding:12px 24px;border-radius:999px;text-decoration:none;margin-top:12px}}p,li{{color:#b8c2d3}}</style></head><body><main><a href="/" style="font-weight:800;color:#e8edf5;text-decoration:none">gbps.run</a>{body}</main></body></html>"""

ABOUT = """<h1>About gbps.run</h1><p>gbps.run is a free, ad-free internet speed test built to answer the question people actually have: <em>is my internet good enough for what I do?</em></p><p>It measures download, upload, ping, jitter and packet loss, and — unlike most tests — ping <strong>under load</strong>, which is graded as bufferbloat. It then gives plain-English verdicts for 4K streaming, video calls, gaming, working from home and more.</p><ul><li>Runs entirely in your browser; nothing to install.</li><li>Test data is exchanged with Cloudflare's nearest data centre, which has hundreds of locations worldwide.</li><li>No ads, no accounts, no tracking. Results are stored only on your own device.</li><li>Free to embed on any website.</li></ul><p>gbps.run is independent and not affiliated with any internet provider.</p><a class="btn" href="/">Run the test</a>"""
PRIVACY = """<h1>Privacy</h1><p>gbps.run does not use advertising, tracking cookies or user accounts.</p><ul><li><strong>Test traffic:</strong> the test downloads and uploads random bytes to Cloudflare's speed-test endpoints (speed.cloudflare.com). Cloudflare sees your IP address as part of serving that traffic, as any website does.</li><li><strong>Connection info:</strong> your IP, ISP name and nearest server are fetched from Cloudflare to display on the page. They're shown to you only and not stored by gbps.run.</li><li><strong>History:</strong> your past results are saved in your browser's local storage on your device. Clear them any time with the Clear history button.</li><li><strong>Analytics:</strong> if enabled, the site uses privacy-friendly, cookie-free page-view counting only.</li></ul><a class="btn" href="/">Back to the test</a>"""
NOT_FOUND = """<h1>Page not found</h1><p>That page doesn't exist — but the speed test does.</p><a class="btn" href="/">Run a speed test</a>"""

EMBED = TEMPLATE  # embed uses the same page; we strip SEO sections for a compact widget via CSS
def render_embed():
    p = dict(PAGES[0]); p = {**p, "title": "gbps.run speed test (embed)", "h1": "Internet speed test", "intro": "Powered by <a href='https://gbps.run' target='_blank' rel='noopener'>gbps.run</a>"}
    out = render(p)
    out = out.replace("</style>", "#faq,#more,#embed,#historyCard,header .row,footer{display:none !important}.wrap{padding:8px}</style>")
    out = out.replace('<link rel="canonical" href="https://gbps.run/">', '<link rel="canonical" href="https://gbps.run/"><meta name="robots" content="noindex">')
    return out

def og_image(path):
    from PIL import Image, ImageDraw, ImageFont
    W, H = 1200, 630
    im = Image.new("RGB", (W, H), (11, 15, 23)); d = ImageDraw.Draw(im)
    def font(sz, bold=True):
        for f in ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf"]:
            if os.path.exists(f): return ImageFont.truetype(f, sz)
        return ImageFont.load_default()
    # gauge arc
    d.arc([760, 120, 1120, 480], 180, 360, fill=(36, 48, 65), width=28)
    d.arc([760, 120, 1120, 480], 180, 330, fill=(62, 230, 165), width=28)
    d.text((940, 300), "940", fill=(232, 237, 245), font=font(96), anchor="mm")
    d.text((940, 365), "Mbps", fill=(141, 154, 176), font=font(28, False), anchor="mm")
    d.text((80, 150), "gbps.run", fill=(62, 230, 165), font=font(72))
    d.text((80, 250), "Free internet speed test", fill=(232, 237, 245), font=font(44))
    for i, line in enumerate(["Download · Upload · Ping · Jitter", "Bufferbloat grade (A+ to F)", "Plain-English verdicts: 4K, Zoom, gaming", "No ads · No sign-up · 25 seconds"]):
        d.text((80, 330 + i * 52), "•  " + line, fill=(184, 194, 211), font=font(28, False))
    im.save(path, optimize=True)

def main():
    if os.path.exists(OUT): shutil.rmtree(OUT)
    os.makedirs(OUT)
    urls = []
    for p in PAGES:
        d = os.path.join(OUT, p["slug"]) if p["slug"] else OUT
        os.makedirs(d, exist_ok=True)
        open(os.path.join(d, "index.html"), "w", encoding="utf-8").write(render(p))
        urls.append((f"{ROOT}/{p['slug']}/" if p["slug"] else f"{ROOT}/", "1.0" if not p["slug"] else "0.8"))
    os.makedirs(os.path.join(OUT, "embed"), exist_ok=True)
    open(os.path.join(OUT, "embed", "index.html"), "w", encoding="utf-8").write(render_embed())
    for slug, title, desc, body in [("about", "About gbps.run – free, independent speed test", "What gbps.run measures, how it works and why it's free.", ABOUT), ("privacy", "Privacy – gbps.run", "gbps.run privacy: no ads, no tracking, results stay on your device.", PRIVACY)]:
        os.makedirs(os.path.join(OUT, slug), exist_ok=True)
        open(os.path.join(OUT, slug, "index.html"), "w", encoding="utf-8").write(STATIC_PAGE.format(title=title, desc=desc, url=f"{ROOT}/{slug}/", body=body))
        urls.append((f"{ROOT}/{slug}/", "0.3"))
    open(os.path.join(OUT, "404.html"), "w", encoding="utf-8").write(STATIC_PAGE.format(title="Not found – gbps.run", desc="", url=f"{ROOT}/", body=NOT_FOUND))
    today = datetime.date.today().isoformat()
    sm = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "".join(f"  <url><loc>{u}</loc><lastmod>{today}</lastmod><priority>{pr}</priority></url>\n" for u, pr in urls) + "</urlset>\n"
    open(os.path.join(OUT, "sitemap.xml"), "w").write(sm)
    open(os.path.join(OUT, "robots.txt"), "w").write(f"User-agent: *\nAllow: /\nDisallow: /embed/\nSitemap: {ROOT}/sitemap.xml\n")
    open(os.path.join(OUT, ".htaccess"), "w").write("""# gbps.run – Hostinger/Apache config
RewriteEngine On
# Force HTTPS + no-www
RewriteCond %{HTTPS} off [OR]
RewriteCond %{HTTP_HOST} ^www\\. [NC]
RewriteRule ^ https://gbps.run%{REQUEST_URI} [L,R=301]
ErrorDocument 404 /404.html
# Source files live in _src/ (git) – never serve them
RedirectMatch 404 ^/_src(/|$)
RedirectMatch 404 ^/[.]git(/|$)
# Compression
<IfModule mod_deflate.c>
AddOutputFilterByType DEFLATE text/html text/css application/javascript application/json image/svg+xml text/xml
</IfModule>
# Caching: HTML short, assets long
<IfModule mod_headers.c>
<FilesMatch "\\.(html)$">
Header set Cache-Control "public, max-age=600"
</FilesMatch>
<FilesMatch "\\.(png|svg|ico|webp)$">
Header set Cache-Control "public, max-age=2592000"
</FilesMatch>
Header set X-Content-Type-Options "nosniff"
Header set Referrer-Policy "strict-origin-when-cross-origin"
Header set Permissions-Policy "camera=(), microphone=(), geolocation=()"
</IfModule>
""")
    og_image(os.path.join(OUT, "og.png"))
    print(f"built {len(urls)} pages → {OUT}/")

if __name__ == "__main__":
    main()
