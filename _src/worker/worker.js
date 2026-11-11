// gbps.run speed-test backend — a Cloudflare Worker that speaks the same protocol the page already uses:
//   GET  /__down?bytes=N   → N bytes of incompressible-looking data, streamed (N capped at 200 MB)
//   POST /__up             → reads and discards the body, returns "ok"
//   GET  /meta             → where the request landed: data centre (colo), city, ISP, HTTP version, client IP
//   GET  /                 → plain-text status
// Runs on the Workers free plan: 100,000 requests/day, 10 ms CPU per request. Streaming a response costs almost no CPU
// (the chunk below is built once at startup), and reading an upload body is I/O, not CPU.
// If the daily quota is exhausted Cloudflare answers with error 1027 and the page falls back to speed.cloudflare.com.

const CHUNK_BYTES = 64 * 1024;
const MAX_DOWN = 200e6;
const CHUNK = (() => { const b = new Uint8Array(CHUNK_BYTES); crypto.getRandomValues(b); return b; })();

const CORS = {
  "access-control-allow-origin": "*",
  "access-control-allow-methods": "GET, POST, OPTIONS",
  "access-control-allow-headers": "*",
  "access-control-expose-headers": "server-timing, cf-meta-colo",
  "access-control-max-age": "86400",
};

function withCors(headers = {}) { return { ...CORS, ...headers }; }

function noStore(extra = {}) {
  return withCors({ "cache-control": "no-store, no-cache, must-revalidate", "pragma": "no-cache", ...extra });
}

export default {
  async fetch(request) {
    const url = new URL(request.url);
    const path = url.pathname.replace(/\/+$/, "") || "/";
    const t0 = Date.now();

    if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: withCors() });

    if (path === "/__down") {
      let n = parseInt(url.searchParams.get("bytes") || "0", 10);
      if (!Number.isFinite(n) || n < 0) n = 0;
      n = Math.min(n, MAX_DOWN);
      const colo = (request.cf && request.cf.colo) || "";
      if (n === 0) {
        // ping probe: empty body, server processing time exposed so the page can subtract it
        return new Response(null, { status: 200, headers: noStore({ "server-timing": `cfRequestDuration;dur=${Date.now() - t0}`, "cf-meta-colo": colo, "content-length": "0" }) });
      }
      let sent = 0;
      const body = new ReadableStream({
        pull(controller) {
          if (sent >= n) { controller.close(); return; }
          const take = Math.min(CHUNK_BYTES, n - sent);
          controller.enqueue(take === CHUNK_BYTES ? CHUNK : CHUNK.subarray(0, take));
          sent += take;
        },
      });
      return new Response(body, {
        status: 200,
        headers: noStore({ "content-type": "application/octet-stream", "content-length": String(n), "content-encoding": "identity", "server-timing": `cfRequestDuration;dur=${Date.now() - t0}`, "cf-meta-colo": colo }),
      });
    }

    if (path === "/__up") {
      if (request.method !== "POST") return new Response("POST only", { status: 405, headers: noStore() });
      // consume the body without buffering it
      let bytes = 0;
      if (request.body) {
        const reader = request.body.getReader();
        for (;;) { const { done, value } = await reader.read(); if (done) break; bytes += value.byteLength; }
      }
      return new Response("ok", { status: 200, headers: noStore({ "content-type": "text/plain", "server-timing": `cfRequestDuration;dur=${Date.now() - t0}`, "x-bytes-received": String(bytes) }) });
    }

    if (path === "/meta") {
      const cf = request.cf || {};
      const meta = {
        clientIp: request.headers.get("cf-connecting-ip") || "",
        asn: cf.asn || null,
        asOrganization: cf.asOrganization || "",
        colo: cf.colo || "",
        city: cf.city || "",
        region: cf.region || "",
        country: cf.country || "",
        httpProtocol: cf.httpProtocol || "",
        tlsVersion: cf.tlsVersion || "",
        backend: "gbps.run worker",
      };
      return new Response(JSON.stringify(meta), { status: 200, headers: noStore({ "content-type": "application/json" }) });
    }

    if (path === "/") {
      return new Response("gbps.run speed-test backend: /__down?bytes=N, POST /__up, /meta\n", { status: 200, headers: noStore({ "content-type": "text/plain" }) });
    }

    return new Response("not found", { status: 404, headers: noStore() });
  },
};
