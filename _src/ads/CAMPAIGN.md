# gbps.run — $3/day India test campaign (Meta: Instagram Reels + Facebook)

Why Meta, not Google: at ₹250/day, Google exact-match "speed test" clicks in India cost ₹8–20
and you'd get ~15 clicks/day. Meta Reels traffic in India runs ~₹2–6 per link click → 40–120
clicks/day. Same money, 4–6× the visits. Add Google later if Meta clicks convert into repeat visits.

What to expect (honest): 1,200–3,500 visits/month from the ad alone. It will not get you to
100k by itself; its job is to (a) prove Indian users run the test and share results, (b) seed
Cloudflare Analytics with real behaviour data, (c) give you screenshots/social proof for outreach.
Kill it after 14 days if cost per link click is above ₹8 or average time on site is under 20 s.

## Landing pages (use these exact URLs so Cloudflare Analytics can separate ad traffic)
- Jio / general Hindi ad   → https://gbps.run/hi/?utm_source=meta&utm_campaign=in1
- BGMI ad                  → https://gbps.run/hi/bgmi-ping-test/?utm_source=meta&utm_campaign=in1
- WiFi-vs-internet Hindi   → https://gbps.run/hi/wifi-speed-test/?utm_source=meta&utm_campaign=in1
- English ad               → https://gbps.run/?utm_source=meta&utm_campaign=in1

## Setup in Meta Ads Manager (≈10 minutes, business.facebook.com → Ads Manager → Create)
1. Objective: **Traffic**. Campaign name: `gbps IN test`. Leave Advantage+ campaign budget OFF.
2. Ad set: Conversion location **Website**. Performance goal: **Maximise number of link clicks**.
   Budget: **Daily, $3** (or ₹250 if your account is INR). Schedule: run continuously.
3. Audience: Location **India** (people living in). Age **18–40**. Languages: **Hindi, English**.
   Detailed targeting (interests): Reliance Jio, JioFiber, Airtel, Broadband, Battlegrounds Mobile
   India, Online games, Netflix. Leave Advantage+ audience ON (it's cheap and fine at this budget).
4. Placements: **Manual** → untick everything except **Instagram Reels, Facebook Reels, Instagram Stories,
   Facebook Feed, Instagram Feed**. Devices: Mobile only. OS: Android first (that's India).
5. Ads: create **4 ads** in the same ad set (Meta will shift spend to the winner automatically):
   - Reel/Story placements: upload `reel_*.png` (1080×1920). Feed placements: `square_*.png`.
   - Use the copy below. Call-to-action button: **Learn more**. Website URL: the matching landing page.
6. Payment: add your card (only you can do this). Publish. Approval usually takes under an hour.

## Ad copy (paste as-is)

### Ad 1 — Jio (Hindi)  → image reel_hi_jio / square_hi_jio
Primary text:
Jio 300 Mbps का प्लान है लेकिन YouTube अटकता है? 15 सेकंड में असली स्पीड जानें — बिना ऐप, बिना विज्ञापन, बिना साइन-अप। gbps.run पिंग, जिटर और Bufferbloat भी बताता है, जिससे पता चलता है कि दिक्कत Jio की है या आपके राउटर की।
Headline: असली इंटरनेट स्पीड जानें
Description: मुफ़्त • हिंदी में • 15 सेकंड

### Ad 2 — BGMI (Hindi)  → reel_hi_bgmi / square_hi_bgmi
Primary text:
BGMI में लैग 300 Mbps प्लान से नहीं जाता — पिंग से जाता है। gbps.run गेम जैसे लोड में आपका पिंग मापता है और राउटर को A+ से F तक ग्रेड देता है। अगर ग्रेड C से नीचे है, तो नया प्लान नहीं, राउटर की सेटिंग बदलनी है। मुफ़्त टेस्ट, कोई ऐप नहीं।
Headline: BGMI लैग का असली कारण
Description: पिंग • जिटर • Bufferbloat ग्रेड

### Ad 3 — WiFi vs internet (Hindi)  → reel_hi_wifi / square_hi_wifi
Primary text:
इंटरनेट धीमा है या सिर्फ WiFi? एक मुफ़्त टेस्ट बताता है। gbps.run हर नतीजे के साथ साफ़ जवाब देता है: 4K चलेगा? वीडियो कॉल ठीक रहेगी? गेमिंग के लिए ठीक है? कोई ऐप नहीं, कोई विज्ञापन नहीं।
Headline: WiFi धीमा है या इंटरनेट?
Description: 15 सेकंड में जवाब

### Ad 4 — English  → reel_en_pay / square_en_pay
Primary text:
Paying for 300 Mbps and getting 94? Find out in 15 seconds. gbps.run is a free speed test with no ads, no app and no sign-up — and it's the only one that grades your router's bufferbloat, the thing that actually makes calls and games stutter.
Headline: Free speed test, no ads
Description: Download • Upload • Ping • Bufferbloat

## Reading results (check on day 3, 7 and 14)
- Ads Manager columns: **Link clicks, CPC (cost per link click), CTR (link)**. Good: CPC under ₹6, CTR over 1%.
- Cloudflare Web Analytics → gbps.run → filter path contains `utm_source=meta`: visits, and
  whether people reach a result (time on page over 25 s means the test ran).
- Pause any ad whose CPC is 2× the best ad after 300+ impressions each. Keep the top 2.

## Scale rule
If the winning ad holds CPC under ₹5 for a week, raise the budget 20% every 3 days (not more —
Meta resets learning on big jumps). Stop at $10/day unless AdSense revenue is covering it.
