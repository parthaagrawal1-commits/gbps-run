import json, subprocess, sys, concurrent.futures as cf

ID = "https://rdap.identitydigital.services/rdap/domain/"
VS = "https://rdap.verisign.com/{tld}/v1/domain/"
VERISIGN = {"com", "net", "cc", "tv", "name"}

def get(url):
    try:
        out = subprocess.run(["curl", "-s", "--max-time", "15", "-w", "\n%{http_code}", url], capture_output=True, text=True, timeout=20).stdout
        body, code = out.rsplit("\n", 1)
        return int(code), body
    except Exception as e:
        return 0, ""

def status(domain):
    tld = domain.rsplit(".", 1)[1]
    if tld in VERISIGN:
        code, body = get(VS.format(tld=tld) + domain)
    else:
        code, body = get(ID + domain)
    if code == 200:
        try:
            j = json.loads(body); ev = {e["eventAction"]: e["eventDate"][:10] for e in j.get("events", [])}
            return "TAKEN", f"reg {ev.get('registration','?')} exp {ev.get('expiration','?')}"
        except Exception:
            return "TAKEN", ""
    if code == 404:
        return "AVAILABLE", ""
    return "UNKNOWN", f"http {code}"

tokens = sys.argv[1].split(",")
tlds = sys.argv[2].split(",")

# calibrate: does the registry serve this TLD? (nic.<tld> is always registered)
served = {}
for t in tlds:
    s, _ = status(f"nic.{t}")
    served[t] = (s == "TAKEN")
print("TLD coverage:", {t: ("ok" if v else "NO-RDAP") for t, v in served.items()}, file=sys.stderr)

domains = [f"{tok}.{t}" for t in tlds if served[t] for tok in tokens]
with cf.ThreadPoolExecutor(8) as ex:
    results = list(ex.map(lambda d: (d, *status(d)), domains))
avail = [r for r in results if r[1] == "AVAILABLE"]
print("\nAVAILABLE (%d):" % len(avail))
for d, s, n in sorted(avail): print("  ", d)
print("\nTAKEN (%d):" % len([r for r in results if r[1] == "TAKEN"]))
for d, s, n in sorted(results):
    if s == "TAKEN": print("  ", d, n)
unk = [r for r in results if r[1] == "UNKNOWN"]
if unk: print("\nUNKNOWN:", [r[0] for r in unk])
