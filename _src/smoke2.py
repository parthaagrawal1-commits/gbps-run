import asyncio, re, os, sys
from playwright.async_api import async_playwright
BIG = b"x" * 2_000_000
async def main():
    errors = []
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
        ctx = await b.new_context(viewport={"width": 430, "height": 932}, device_scale_factor=2)
        page = await ctx.new_page()
        page.on("pageerror", lambda e: errors.append("PAGEERROR " + str(e)))
        page.on("console", lambda m: errors.append("CONSOLE " + m.text) if m.type == "error" else None)
        async def handler(route):
            url = route.request.url
            if "/__down" in url:
                m = re.search(r"bytes=(\d+)", url); n = int(m.group(1)) if m else 0
                await route.fulfill(status=200, body=b"" if n == 0 else BIG, headers={"access-control-allow-origin": "*", "server-timing": "cfRequestDuration;dur=0.4", "access-control-expose-headers": "server-timing"})
            elif "/__up" in url: await route.fulfill(status=200, body="ok", headers={"access-control-allow-origin": "*"})
            elif "/meta" in url: await route.fulfill(status=200, body='{"clientIp":"203.0.113.9","asOrganization":"Cloudflare London, LLC","colo":{"code":"DEN"},"city":"Denver","httpProtocol":"HTTP/1.1"}', headers={"access-control-allow-origin": "*", "content-type": "application/json"})
            else: await route.fulfill(status=404, body="")
        await page.route("**/speed.cloudflare.com/**", handler)
        await page.route("**/fonts.googleapis.com/**", lambda r: r.fulfill(status=200, body="", headers={"content-type": "text/css"}))
        base = "file://" + os.path.abspath("site")
        # 1. English home, full run
        await page.goto(base + "/index.html"); await page.click("#settingsBtn"); await page.select_option("#durSel", "6"); await page.click("#startBtn")
        await page.wait_for_function("document.getElementById('phase').textContent.startsWith('Done')", timeout=40000)
        res = await page.evaluate("""() => ({down: document.getElementById('tDown').textContent, up: document.getElementById('tUp').textContent, ping: document.getElementById('tPing').textContent, jit: document.getElementById('tJit').textContent,
            bloatS: document.getElementById('tBloatS').textContent, relay: !!document.querySelector('.notice'), server: document.getElementById('meta').textContent.includes('DEN'), verdicts: document.querySelectorAll('#verdicts .verdict').length,
            advice: document.getElementById('advice').textContent.slice(0,80), share: document.getElementById('shareText').textContent.split('\\n').pop()})""")
        print("EN:", res)
        await page.screenshot(path="s_en.png", full_page=False)
        # 2. shared link
        await page.goto(base + "/index.html#r=280,37.9,62,11,C"); await page.wait_for_timeout(300)
        print("SHARED:", await page.evaluate("document.getElementById('sharedBox').className + ' | ' + document.getElementById('sharedBox').textContent.slice(0,90)"))
        # 3. Spanish page quick run
        await page.goto(base + "/es/index.html"); await page.click("#settingsBtn"); await page.select_option("#durSel", "6"); await page.click("#startBtn")
        await page.wait_for_function("document.getElementById('phase').textContent.startsWith('Listo')", timeout=40000)
        print("ES:", await page.evaluate("document.getElementById('phase').textContent + ' | ' + document.querySelector('#verdicts .verdict .t').textContent + ' | ' + document.getElementById('planText').textContent"))
        await page.screenshot(path="s_es.png", full_page=False)
        # 4. outage page: auto check
        await page.goto(base + "/is-xfinity-down/index.html"); await page.wait_for_function("!document.getElementById('outageStatus').textContent.startsWith('Checking')", timeout=20000)
        print("OUTAGE:", await page.evaluate("document.getElementById('outageStatus').className + ' | ' + document.getElementById('outageStatus').textContent.slice(0,80)"))
        await page.screenshot(path="s_out.png", full_page=False)
        # 5. fallback: Cloudflare dead → jsdelivr fallback
        await page.unroute("**/speed.cloudflare.com/**"); await page.route("**/speed.cloudflare.com/**", lambda r: r.abort())
        await page.route("**/cdn.jsdelivr.net/**", lambda r: r.fulfill(status=200, body=BIG if "wasm" in r.request.url else b"{}", headers={"access-control-allow-origin": "*"}))
        await page.goto(base + "/index.html"); await page.click("#settingsBtn"); await page.select_option("#durSel", "6"); await page.click("#startBtn")
        await page.wait_for_function("/Done|failed/.test(document.getElementById('phase').textContent)", timeout=60000)
        print("FALLBACK:", await page.evaluate("document.getElementById('phase').textContent + ' | down=' + document.getElementById('tDown').textContent + ' up=' + document.getElementById('tUpS').textContent"))
        await b.close()
    print("ERRORS:", errors)
asyncio.run(main())
