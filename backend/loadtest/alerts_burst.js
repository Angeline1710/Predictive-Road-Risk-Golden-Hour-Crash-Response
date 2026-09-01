// MVP-PLAN.md §3.5 "k6 load test — 100 alerts/min burst (NFR-P7)".
// PRD.md §NFR table:
//   NFR-P3  Backend ingest -> gateway call <=400ms p95, <=900ms p99
//   NFR-P4  End-to-end crash -> gateway ack <=20s median on data
//   NFR-P7  System sustains 100 alerts/minute burst with no drops
//
// http_req_duration below is the full POST /v1/alerts round trip as k6's
// HTTP client sees it -- request send, server processing (dedup, persist,
// enrich, score, THEN gateway.submit(), all synchronous within the one
// request per app/services/alerts.py), response receive. gateway.submit()
// is the dominant cost inside that span in "ok" mode (no injected
// artificial delay -- see app/gateways/simulated.py), so this is an
// honest, if same-Docker-host, proxy for NFR-P3/P4's ingest->gateway->ack
// latency. It is NOT a measurement of real phone-to-server network
// conditions -- that variable doesn't exist in this test.
//
// Run (from backend/):
//   docker run --rm -i -e BASE_URL=http://host.docker.internal:8000 \
//     grafana/k6 run - < loadtest/alerts_burst.js
// (host.docker.internal, not localhost, because the backend is a sibling
// container on Docker Desktop for Windows/Mac, not reachable via
// --network host the way it would be on Linux.)

import http from "k6/http";
import { check } from "k6";

const BASE_URL = __ENV.BASE_URL || "http://localhost:8000";

// PRD §6.4/6.3.1's own worked-example location -- NH-45 near Guduvancheri
// toll, Chengalpattu, the frozen demo corridor. Every request is marked
// is_simulated: true; this is a load test, not a fabricated real crash.
const DEMO_LAT = 12.91845;
const DEMO_LON = 80.22456;

function uuidv4() {
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

function alertPayload() {
  return JSON.stringify({
    alert_uuid: uuidv4(),
    occurred_at: new Date().toISOString(),
    location: { lat: DEMO_LAT + (Math.random() - 0.5) * 0.05, lon: DEMO_LON + (Math.random() - 0.5) * 0.05, accuracy_m: 8.0 },
    motion: {
      speed_kmh: 40 + Math.random() * 60, heading_deg: Math.random() * 360, peak_g: 8 + Math.random() * 4,
      delta_v_kmh: 20 + Math.random() * 40, impact_direction: "front", rollover: false, still_moving: false,
    },
    detection: { p_crash: 0.9 + Math.random() * 0.09, severity: "SEVERE", model_version: "loadtest" },
    window: { duration_s: 10, outcome: "EXPIRED" },
    is_simulated: true,
  });
}

export const options = {
  scenarios: {
    // constant-arrival-rate is the right executor for "sustains N events
    // per time unit" -- it fixes the request RATE and lets k6 add VUs as
    // needed to hit it, rather than fixing VU count and letting rate
    // drift with response time (the more common ramping-vus executor).
    alerts_burst: {
      executor: "constant-arrival-rate",
      rate: 100,
      timeUnit: "1m",
      duration: "2m",
      preAllocatedVUs: 20,
      maxVUs: 60,
    },
  },
  thresholds: {
    http_req_duration: ["p(95)<400", "p(99)<900"],   // NFR-P3
    http_req_failed: ["rate<0.01"],                   // NFR-P7 "no drops"
    checks: ["rate>0.99"],
  },
};

export default function () {
  const res = http.post(`${BASE_URL}/v1/alerts`, alertPayload(), {
    headers: { "Content-Type": "application/json" },
  });
  check(res, {
    "status is 202": (r) => r.status === 202,
    "response has dispatch or degrades honestly": (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.status === "RECEIVED";
      } catch {
        return false;
      }
    },
  });
}
