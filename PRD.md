# Product Requirements Document
## Predictive Road-Risk & Golden-Hour Crash Response

| Field | Value |
|---|---|
| **Document version** | 1.1 — §7.1, §6.1.2, §12.3 updated 2026-08-17 to match the implemented model (see `ml/MODELS.md`) |
| **Date** | 2026-08-14 |
| **Status** | Draft — for review |
| **Source** | Derived from `SRMIST SIH2026-IDEA-Presentation-Format.pptx` (Smart India Hackathon idea submission) |
| **PS Category** | Software |
| **Codename** | `rrx` (Road Risk eXchange) — used as the internal prefix for repos, DB schema, and SMS protocol |

> **Note on source inconsistency:** The submitted deck's title slide reads "SMART INDIA HACKATHON 2025" while the template filename says SIH2026. This PRD assumes **SIH 2026**. Confirm before the deck is finalised.

---

## 1. Executive Summary

Three pieces of road-safety infrastructure already exist in India and do not talk to each other:

1. **On-device crash sensing** — exists, but only on iPhone 14+, Apple Watch Series 8+, and Google Pixel. Effectively absent from the Android install base that the overwhelming majority of Indian users own.
2. **PM RAHAT** — the Government of India's cashless treatment scheme for road accident victims (₹1.5 lakh / 7 days), launched February 2026, dispatch-integrated with ERSS-112.
3. **Blackspot / risk data** — MoRTH's iRAD/e-DAR black-spot methodology and SaveLIFE Foundation's Zero Fatality Corridor work, both of which are *retrospective*: a stretch becomes a "blackspot" only after 5+ fatal/grievous accidents or 10+ deaths in 3 years.

**This product is the connective layer between those three, not a replacement for any of them.**

It does two things:

- **Reactive (Golden Hour):** Detects a crash on *any* Android phone using sensor fusion + an on-device ML model, confirms it through a 10-second cancel window, and pushes a structured, enriched alert into the PM RAHAT / ERSS-112 dispatch pipeline — with **no bystander call, no language barrier, no flagship-device dependency**, and an **SMS fallback that works at zero data connectivity**.
- **Proactive (Predictive Risk):** Scores road segments live against current conditions — rain, fog, low light, traffic state, time of day — and warns drivers *before* they enter a dangerous stretch, replacing a static, years-old blackspot list with a real-time risk surface.

A secondary output is a by-product with independent policy value: a continuously-growing, fine-grained risk and near-miss dataset that MoRTH/NHAI could use to move blackspot identification from reactive to proactive.

---

## 2. Problem Statement

### 2.1 The measurable gap

| Fact | Source (from deck's reference table) |
|---|---|
| Road crashes cost India ~3–3.14% of GDP annually | MoRTH / DIMTS–TRIPP IIT Delhi study; restated by Union Minister Nitin Gadkari, Mar 2025 |
| India accounts for ~10% of global crash deaths with ~1% of the world's vehicles | World Bank, Nov 2022 |
| India needs ~$109B in road-safety investment over a decade | World Bank, Feb 2020 |
| ~50% of road-accident deaths are considered avertable with hospitalisation inside the first hour | Golden-hour clinical consensus, as cited in deck |
| Device-native crash detection is limited to iPhone 14+, Apple Watch S8+, Pixel | Apple Newsroom / ZDNet; Android Police, Dec 2024 |
| Consequently **>99% of Indian Android users have zero device-native crash detection** | Derived in deck from the above |
| Blackspot definition is a 500m stretch with 5+ fatal/grievous accidents or 10+ deaths in 3 years | MoRTH iRAD / e-DAR criteria |
| PM RAHAT provides cashless treatment up to ₹1.5 lakh for 7 days, ERSS-112 dispatch-integrated | PIB, 14 Feb 2026 |

### 2.2 The failure chain today

```
Crash occurs
  → nobody detects it automatically (no crash detection on the phone)
  → victim is unconscious or unable to dial
  → a bystander must decide to call 112
       ↳ may not stop (Good Samaritan hesitancy)
       ↳ may not speak the operator's language
       ↳ may not know the location on a highway
       ↳ may be absent entirely on a rural road at night
  → call is placed late, location is vague
  → dispatch is slow, hospital is chosen badly
  → golden hour is lost
```

Every link in that chain is a place where software can intervene, and none of them require new hardware.

### 2.3 Why this hasn't been solved

- OEM crash detection is a **hardware differentiation feature**, so it is deliberately restricted to flagship tiers.
- PM RAHAT is a **payments and treatment-assurance scheme**; it assumes an incident has already been reported.
- Blackspot programmes are **infrastructure-engineering programmes**; they operate on multi-year data cycles, not on tonight's fog.

Nobody owns the seam between them. That seam is this product.

---

## 3. Goals and Non-Goals

### 3.1 Goals

| ID | Goal | Measure of success |
|---|---|---|
| G1 | Detect a crash on a commodity Android phone without OEM support | ≥90% recall on the simulated/collected crash test set at ≤1 false positive per 100 driving hours *post*-cancel-window |
| G2 | Cut time-to-first-alert from crash to dispatch system | Median crash→gateway-ack ≤ 20s on mobile data; ≤ 90s on SMS fallback |
| G3 | Work where connectivity fails | 100% of confirmed crashes produce either an HTTP alert or an SMS alert; zero silent drops |
| G4 | Remove the language barrier | Full driver-facing UX in ≥5 languages at demo (EN, HI, TA, TE, BN); alert payload is structured data, not free text |
| G5 | Warn before the crash, not only after | Live risk score served for any road segment in the coverage area in ≤300ms p95 |
| G6 | Be plug-in, not parallel infrastructure | Government-facing interface is a single, swappable adapter with a documented contract |
| G7 | Generate policy-grade risk data | Every alert and every risk evaluation persisted with geometry, timestamp, and conditions |

### 3.2 Non-Goals (explicitly out of scope for v1)

- **We are not building an ambulance dispatch system.** We hand off to PM RAHAT/ERSS-112.
- **We are not building a hospital / bed-availability network.**
- **We are not doing insurance claim processing** (PM RAHAT already covers the treatment-payment path).
- **We are not doing driver behaviour scoring, telematics-for-insurance, or gamified safe-driving.**
- **We are not building an iOS app in v1.** iPhone 14+ already has native crash detection; the gap is Android. (Backlogged as P2 — see §17.)
- **We are not integrating with real ERSS-112 in v1.** No public API exists to us. See §11.
- **We are not doing dashcam / computer-vision crash detection.** Sensor-only.

---

## 4. Users and Personas

| # | Persona | Context | Primary need | Product surface |
|---|---|---|---|---|
| P1 | **Ravi — highway commuter** | Drives NH-48 daily on a ₹12,000 Android phone | Help arrives even if he's unconscious and alone | Android app (background) |
| P2 | **Meena — night-shift cab driver** | Rural stretches, patchy 4G, speaks Tamil | Warning before a bad stretch; alert that works with no data | Android app (foreground risk UI + SMS fallback) |
| P3 | **ERSS-112 dispatch operator** | Handles voice calls under load | Structured incident with precise location and severity, not a panicked call | Gateway adapter → their CAD system (simulated in v1) |
| P4 | **First responder / ambulance crew** | Needs to find the vehicle | Exact coordinates, severity band, access route | Dispatch payload (via P3) |
| P5 | **NHAI / MoRTH road-safety analyst** | Plans interventions | Live, fine-grained risk surface instead of a 3-year-lagging blackspot list | Web dashboard, data export |
| P6 | **Emergency contact / family** | Off-system | To be told, in their language | SMS/notification fan-out |
| P7 | **Ops/demo operator (SIH jury demo)** | Evaluating the system live | Visible, honest, end-to-end flow with the simulation clearly labelled | Web dashboard + simulator console |

### 4.1 Core user stories

- **US-1** — As Ravi, when I crash and am unresponsive, I want the phone to alert emergency services automatically, so that help is dispatched inside the golden hour.
- **US-2** — As Ravi, when I brake hard or drop my phone, I want a 10-second window to cancel, so that I don't waste an ambulance.
- **US-3** — As Meena with no mobile data, I want the alert to still leave my phone, so that a dead zone isn't a death sentence.
- **US-4** — As Meena, I want the app to speak Tamil, so that I understand the countdown before it expires.
- **US-5** — As Meena approaching a foggy curve at 11pm, I want a warning that *this* stretch is dangerous *right now*, so I slow down.
- **US-6** — As a dispatch operator, I want location, severity, impact vector, and occupant-count estimate as structured fields, so I dispatch the right unit the first time.
- **US-7** — As an NHAI analyst, I want a live heatmap and exportable risk history, so I can prioritise interventions against current conditions, not 2023 data.
- **US-8** — As a jury member, I want the simulated component clearly labelled, so I can tell what's real and what's mocked.

---

## 5. Solution Overview

### 5.1 The six-stage pipeline

The system is a **linear, fault-tolerant pipeline**. Each stage depends only on the previous one, which is what makes it demonstrable and independently testable.

```
① Phone Sensors    → ② Cancel Window → ③ Data/SMS Channel → ④ Crash + Risk Backend
                                                                      ↑
                                                    ⑦ Live Data (Weather + Traffic)
                                                                      ↓
                          ⑤ PM RAHAT / ERSS-112 (simulated gateway) → ⑥ Live Dashboard
```

| Stage | Component | Responsibility | Output |
|---|---|---|---|
| ① | Phone Sensors | Continuously monitor accelerometer + gyroscope + GPS; on-device crash inference | Crash Detected |
| ② | Cancel Window | 10-second high-salience countdown (audio + haptic + full-screen) | Alert Confirmed / Cancelled |
| ③ | Data/SMS Channel | Deliver alert over whichever channel exists | Alert Sent (with delivery receipt) |
| ④ | Backend | Validate, enrich with weather/traffic/road context, compute risk, persist, route | Enriched Alert + Risk Level |
| ⑤ | Gov Gateway | Create incident ticket, assign nearest responder, acknowledge | Dispatch Acknowledged *(simulated in v1)* |
| ⑥ | Dashboard | Live risk heatmap, alert log, response metrics | Real-time situational awareness |
| ⑦ | Live Data | Weather + traffic feeds consumed by ④ | Condition features for the risk model |

### 5.2 Design principles

1. **Graceful degradation over feature richness.** Every path has a lower-fidelity fallback: data → SMS; live model → cached score; cached score → static historical prior; server confirm → local siren + emergency-contact SMS.
2. **On-device first.** Crash detection never depends on the network. A crash in a dead zone is still *detected*; only delivery degrades.
3. **Honest simulation.** The one component we cannot make real is drawn in a dashed red box, labelled in the UI, and logged as `SIMULATED` in every record. We never let a jury believe we're wired into a live government system.
4. **Structured data, not free text.** A dispatch payload is fields, so it is language-neutral by construction.
5. **Battery is a feature.** Detection must survive a full day on a mid-tier phone or nobody keeps it installed (§13.2).
6. **Public data only.** No proprietary datasets, no paid APIs above free tiers — so the project is reproducible and cheap to pilot.

---

## 6. Detailed Component Specifications

### 6.1 ① Client — Android App

**Stack:** Kotlin, Jetpack Compose, Foreground Service, TensorFlow Lite, Room, WorkManager, Retrofit/OkHttp, SmsManager.

#### 6.1.1 Sensing subsystem

| Sensor | Rate | Purpose |
|---|---|---|
| `TYPE_LINEAR_ACCELERATION` | 50 Hz (`SENSOR_DELAY_GAME`) | Impact magnitude, gravity-removed |
| `TYPE_ACCELEROMETER` | 50 Hz | Raw fallback if linear-accel is unavailable |
| `TYPE_GYROSCOPE` | 50 Hz | Rollover / spin detection |
| `FusedLocationProvider` | 1 Hz while moving, 0.1 Hz while stationary | Position, speed, heading, accuracy |
| `TYPE_ROTATION_VECTOR` | 10 Hz | Device orientation, to correct for phone mounting |

A **circular ring buffer** holds the last **12 seconds** at 50 Hz (600 samples × 6 axes ≈ 14 KB) so that pre-impact context is available for the payload.

#### 6.1.2 Two-stage detection (critical for battery)

**Stage A — cheap gate (always on, pure arithmetic, no ML):**
- Trip condition: `|a_linear| > 4g` **AND** `speed_before > 20 km/h` within the last 3s.
- This gate is <0.1% CPU and prevents the model from ever running during normal driving.
- The speed pre-condition alone eliminates the dominant false-positive class: phone drops while stationary/walking.

**Stage B — TFLite classifier (runs only when Stage A trips):** see §7.1 and `ml/MODELS.md` for the built, verified specification. Summary: a four-branch fusion network (IMU + on-device-computed audio spectrogram + GPS + handcrafted scalars), 76,814 params, **299.5 KB** float16 `.tflite` with the mel frontend and all input normalisation baked into the graph. Output: `p_crash ∈ [0,1]` plus a 5-class severity head (`MINOR`/`MODERATE`/`SEVERE`/`CRITICAL`/`NONE`). Threshold is calibrated on validation to hold a fixed FP/100h budget and is remotely tunable via config so it can be retuned without a Play Store release.

**Derived features included in the payload** (computed on-device, cheap, and useful to responders):
- **Peak observed (clipped) `g`** — not true peak `g`, which a consumer accelerometer cannot measure past its ±8–16 g rail in a real crash; the saturation duration and how many axes clip simultaneously carry the signal that peak magnitude loses. Also: impulse (∫|a|dt over the impact, a lower bound on true delta-V even when the signal is clipped), impact direction vector (front/side/rear), rollover flag (gyro integral > 90° about the roll axis), **GPS-measured delta-V** (the quantity the railed accelerometer cannot supply — this is why GPS is a model input, not just a location source), post-impact motion (is the vehicle still moving? → possible secondary collision risk), speed at impact.

#### 6.1.3 Foreground service & lifecycle

- `ForegroundService` with `FOREGROUND_SERVICE_TYPE_LOCATION|CONNECTED_DEVICE`, persistent low-priority notification (required by Android 14+ policy and by user trust).
- Auto-start on `BOOT_COMPLETED`; auto-detect drive start via Activity Recognition API (`IN_VEHICLE` with confidence >75%) to avoid sensing while the user walks.
- **Drive-session model:** sensing at full rate only inside a drive session. Outside it, the service idles on Activity Recognition alone.
- OEM battery-optimisation whitelisting prompt on first run (Xiaomi/Oppo/Vivo aggressively kill services — this is a real deployment blocker in India and must be handled in onboarding).

#### 6.1.4 ② Cancel window

- **10 seconds.** Full-screen `Activity` over the lock screen (`setShowWhenLocked`, `setTurnScreenOn`).
- Escalating siren at max volume (overrides ring mode), continuous haptics, and TTS in the user's language: *"Crash detected. Sending alert in 10, 9, 8…"*
- One large **CANCEL** button; requires a deliberate press (no accidental-touch dismissal — button is enabled after 800ms).
- **Fail-forward:** if the user does nothing, the alert **sends**. Silence means unconsciousness.
- If severity is `CRITICAL` **and** post-impact motion is zero **and** the phone is not picked up, the window shortens to **5 seconds** (configurable).
- Cancellations are logged locally and (when online) uploaded as **hard negatives** for model retraining — this is the primary source of real-world training data.

#### 6.1.5 Risk display (proactive side)

- Foreground map with a colour-banded route ahead; risk fetched for the next ~5 km along heading.
- Warning modes: silent map colouring (Low/Moderate) → TTS voice warning (High) → voice + haptic (Severe).
- Anti-nag: at most one voice warning per segment per 15 minutes; suppressed entirely below 25 km/h.
- **Offline risk:** last-known risk tiles for the current district cached in Room, refreshed opportunistically; the app degrades to a *static historical* risk score with no live weather/traffic when offline, clearly indicated with a "cached" badge.

#### 6.1.6 Localisation

- String resources in **English, Hindi, Tamil, Telugu, Bengali** at demo; architecture supports all 22 scheduled languages.
- TTS via Android `TextToSpeech` with per-locale voice; falls back to on-screen text + icons if the voice pack is missing.
- **Language never gates safety:** the outbound alert is structured JSON/binary. Language affects only what the *user* hears.

### 6.2 ③ Connectivity Layer

Three channels, tried in strict order, with a hard deadline on each:

| Priority | Channel | Deadline | Notes |
|---|---|---|---|
| 1 | **HTTPS** over mobile data / Wi-Fi (Retrofit + OkHttp) | 6s connect+write | Full payload incl. 12s sensor trace |
| 2 | **SMS** via `SmsManager` to a shortcode/long-code | 15s to `SENT` broadcast | Compact payload, works at 0 data |
| 3 | **Local escalation** | immediate | Max-volume siren + SMS to emergency contacts + on-screen "call 112" with one tap |

Additional rules:
- Channels 1 and 2 are **not exclusive** — for `CRITICAL` severity, SMS fires in parallel with HTTP rather than after it. Backend deduplicates on `alert_uuid`.
- `WorkManager` with exponential backoff retries the full payload upload for up to 24h so the sensor trace eventually lands even if only the SMS got through in the moment.
- Delivery receipts (`SENT`, `DELIVERED` `PendingIntent`s) are surfaced in the UI so the user knows the alert left the phone.

#### 6.2.1 SMS wire protocol (`RRX1`)

Must fit in a single 160-char GSM-7 message. Pipe-delimited, positional:

```
RRX1|<alert_uuid_b32_13>|<lat_e5>|<lon_e5>|<epoch_s>|<sev>|<spd_kmh>|<hdg_deg>|<gps_acc_m>|<peak_g_x10>|<flags>|<crc8>
```

Example (98 chars):
```
RRX1|K7Q2M9XZ4A8BF|1291845|8022456|1786412355|3|68|142|8|91|RM|3C
```

| Field | Encoding | Bytes |
|---|---|---|
| `alert_uuid_b32_13` | first 65 bits of the UUID, Crockford base32 | 13 |
| `lat_e5` / `lon_e5` | degrees × 10⁵ (≈1.1m resolution) | ≤8 each |
| `epoch_s` | Unix seconds | 10 |
| `sev` | 1=MINOR 2=MODERATE 3=SEVERE 4=CRITICAL | 1 |
| `flags` | `R`=rollover, `M`=still moving, `U`=unresponsive, `C`=cancel-window expired (vs. manual SOS) | ≤4 |
| `crc8` | CRC-8/ATM over the preceding bytes, hex | 2 |

The backend ingests SMS through an **SMS gateway webhook** (see §12.3) and reconstructs a partial `Alert` record with `channel=SMS`, `has_trace=false`.

### 6.3 ④ Backend — Crash + Risk Service

**Stack:** Python 3.12, FastAPI, Uvicorn/Gunicorn, PostgreSQL 16 + PostGIS 3.4, Redis 7, SQLAlchemy 2.0, Alembic, Pydantic v2, Celery (or ARQ) for background jobs.

Four internal layers, matching the deck's architecture diagram:

#### 6.3.1 API layer (FastAPI)
- RESTful endpoints (§12), OpenAPI 3.1 auto-generated.
- Auth: device-registration JWT (short-lived access + rotating refresh); dashboard uses OIDC-style login with RBAC (`viewer`, `analyst`, `operator`, `admin`).
- Rate limiting: `slowapi`/Redis token bucket — **but crash-alert endpoints have a much higher ceiling and never hard-drop**; excess is queued, not rejected. A rate limiter must never be the reason an emergency alert fails.
- Idempotency on `alert_uuid` (client-generated) so retries and dual-channel sends collapse to one incident.

#### 6.3.2 Processing engine
1. **Validate** — schema, CRC (SMS), timestamp sanity, geometry inside coverage bbox, device known.
2. **Deduplicate** — Redis `SETNX rrx:alert:{uuid}` with 1h TTL; plus spatio-temporal dedup (same device or two devices within 50m/30s → same incident, multi-vehicle).
3. **Enrich** —
   - map-match the coordinate to the nearest road segment (PostGIS `ST_ClosestPoint` over the segment index),
   - fetch current weather for the cell (Redis cache, 10-min TTL),
   - fetch current traffic speed for the segment (Redis cache, 5-min TTL),
   - attach the segment's historical risk profile and blackspot status,
   - reverse-geocode to a human-readable landmark (Nominatim) for the responder.
4. **Score** — run the risk model to attach the *contextual* risk of the location at the time of crash (feeds analytics; does not gate dispatch).
5. **Persist** — write `alerts`, `alert_events`, `sensor_traces`.
6. **Route** — build the dispatch payload, find the nearest responder units, call the gateway adapter.
7. **Broadcast** — publish to Redis Pub/Sub → WebSocket fan-out to dashboards.

**Latency budget (server-side, alert ingest → gateway call): 400ms p95.** Enrichment calls are all cache-first with hard timeouts (weather 300ms, traffic 300ms, geocode 500ms); **any external timeout degrades the payload, never blocks the dispatch.**

#### 6.3.3 Database layer
PostgreSQL 16 + PostGIS 3.4 (see §9 for the schema), with TimescaleDB **optional** for `risk_evaluations` hypertable if evaluation volume warrants it.

#### 6.3.4 Cache layer (Redis 7)
| Key pattern | Contents | TTL |
|---|---|---|
| `rrx:risk:seg:{segment_id}:{hour_bucket}` | computed risk score + band | 10 min |
| `rrx:wx:{h3_res5}` | weather observation | 10 min |
| `rrx:traffic:{segment_id}` | current speed / free-flow ratio | 5 min |
| `rrx:alert:{uuid}` | dedup sentinel | 1 h |
| `rrx:tiles:{z}/{x}/{y}` | serialised risk vector tile | 5 min |
| Pub/Sub `rrx:events` | live alert + risk events → WebSocket | — |

### 6.4 ⑦ Live Data Ingestion

| Feed | Provider | Free-tier reality | Cadence | Failure behaviour |
|---|---|---|---|---|
| Weather (current) | **OpenWeatherMap** (Current Weather + One Call) | 1,000 calls/day, 60/min | Poll per active H3-res5 cell, 10 min | Fall back to last cached obs; if >2h stale, drop weather features and use the model's weather-agnostic path |
| Weather (official IN) | **IMD** public data / API | Rate-unspecified, best-effort | 30 min | Advisory overlay only; never a hard dependency |
| Traffic | **TomTom Traffic Flow API** | 2,500 calls/day free | Poll per priority corridor, 5 min | Fall back to historical speed profile for that segment × hour |
| Road network | **OpenStreetMap** via Geofabrik India extract | Free, bulk | One-time + monthly refresh | Static, cached in DB |
| Historical crashes | **MoRTH annual reports**, open state datasets, iRAD-derived blackspot lists where published | Free, manual ETL | One-time for v1 | Static |
| Geocoding | **Nominatim** (self-hosted or public, rate-limited) | 1 req/s public | On demand | Alert proceeds without landmark text |

**Quota discipline is a hard design constraint.** With ~1,000 weather calls/day, we cannot poll per-request. Instead:
- Space is bucketed into **H3 resolution-5 cells** (~250 km² each). One weather call serves an entire cell.
- Only **active cells** (a cell with ≥1 device reporting in the last 30 min, or on a priority corridor) are polled.
- A nightly job pre-computes **baseline risk** for every segment × hour-of-week from static features, so live calls only supply the *delta*.

### 6.5 ⑤ Government Integration — Simulated Gateway

See §11. This is the one deliberately simulated component.

### 6.6 ⑥ Dashboard

**Stack:** React 18 + TypeScript + Vite, Leaflet (with `react-leaflet`) for the map, `deck.gl` heatmap layer for density, Chart.js for metrics, TanStack Query for server state, Zustand for local state, Tailwind CSS + shadcn/ui, native WebSocket.

Views:

| View | Contents |
|---|---|
| **Live Risk Map** | Segment-coloured risk overlay (4 bands), weather layer toggle, traffic layer toggle, blackspot overlay for comparison, time-scrubber to replay the last 24h |
| **Alert Log** | Real-time list, severity chip, channel badge (DATA/SMS), status timeline (Detected → Confirmed → Sent → Received → Dispatched → Acknowledged), map fly-to |
| **Incident Detail** | Full payload, sensor trace chart (accel magnitude over the 12s window), conditions at the time, responder assignment, **prominent `SIMULATED DISPATCH` banner** |
| **Live Metrics** | Alerts/hour, median crash→ack latency, channel mix, cancel rate (false-positive proxy), risk-band distribution, top-10 riskiest segments right now |
| **Analytics / Export** | Risk history per segment, CSV/GeoJSON export for MoRTH/NHAI use case |
| **Simulator Console** *(demo-only)* | Inject a synthetic crash at a map point with chosen severity/channel; forces the SMS path; toggles gateway failure modes. This is what makes the SIH demo reproducible on stage. |

Accessibility: WCAG 2.1 AA; risk bands are distinguishable by **pattern and label**, not colour alone (colour-blind safety matters for a safety product).

---

## 7. Machine Learning Specifications

### 7.1 Model A — On-device crash detection

> **This section was updated 2026-08-17 to match the implemented model.** The original spec below described a single-modality 200×6 IMU-only network. Build work (`ml/crash_detection/`) found that a phone accelerometer saturates at ±8–16 g in a real crash — peak acceleration is unmeasurable — and moved to a multi-modal design where GPS supplies the delta-V the IMU loses and audio supplies an independent physical channel. **`ml/MODELS.md` is the authoritative source for this model**; this table is kept in sync with it, not the reverse.

| Aspect | Specification |
|---|---|
| Task | Binary classification (crash / not-crash) + 5-class severity head (4 delta-V bands + explicit `NONE`) |
| Inputs | **Four branches, late fusion:** IMU `200×9` (accel + gyro + per-axis clip mask, 4s @ 50Hz) → 1D-CNN · raw audio `64000` samples (4s @ 16kHz) → on-device log-mel frontend → 2D-CNN · GPS `12×1` (1Hz speed trace) → MLP · 26 handcrafted saturation/kinematic/acoustic scalars → MLP |
| Architecture | 4 branches → `ModalityDropout(p=0.15)` per branch (trains the network to survive any single sensor being unavailable) → concat → dense-64 → dense-32 → two heads. **76,814 params** |
| On-device mel frontend | STFT + librosa-matched mel filterbank baked directly into the TFLite graph (`ml/crash_detection/mel_frontend.py`), so the phone computes the spectrogram from a raw waveform rather than needing a separate DSP implementation. Verified to convert without the Flex delegate and to reproduce librosa's output (mean divergence ~0.007 dB) |
| Normalisation | Baked into the graph as constant weights for all four inputs — the deployed contract is "feed raw sensor values in physical units," with no client-side normalisation logic to get wrong |
| Size / latency | **299.5 KB** float16 `.tflite` (deployable artifact, includes the mel frontend + baked normalisation) — above the original ~180 KB target; see `ml/MODELS.md` for the breakdown |
| Training data | **Real:** UCI-HAR raw smartphone accelerometer/gyroscope (30 subjects, physical units) as IMU backgrounds; 46 genuine crash-audio clips (38 CC-BY videos) + ESC-50 (1,000 clips, 50 classes) for the acoustic channel. **Synthesised:** crash pulses (haversine-shaped, scaled so their integral equals the target delta-V) and eight hard-negative event types (`EMERGENCY_STOP`, `HARD_BRAKE`, `POTHOLE`, `SPEED_BUMP`, `PHONE_DROP`, `DOOR_SLAM`, `ROUGH_ROAD`, `NORMAL_DRIVE`) composited onto the real backgrounds through a modelled device-saturation response |
| Class imbalance | Event mix weighted toward hard negatives (crash is ~26% of generated events) because the operative metric is false positives per driving hour, not balanced accuracy; focal loss (γ=2); **threshold calibrated on validation to hold a fixed FP/100h budget**, not on accuracy |
| Metrics | Recall (primary), FP/100 driving-hours (secondary), severity macro-F1, plus a per-event-type fire-rate table (does `EMERGENCY_STOP` — a panic stop losing *more* speed than the average crash — correctly not fire?) |
| Targets | Recall ≥0.90 on the held-out crash set; **≤1 pre-cancel FP per 100 driving hours**, which the 10s window then reduces to near-zero *dispatched* FPs |
| **Honest limitation — read `ml/MODELS.md` §0 and §2.6 before quoting any accuracy number from this model.** | There is no public corpus of real vehicle-crash smartphone telemetry, so positives are entirely simulated and the same team wrote both the generator and the detector — near-perfect separation is the *default* outcome under those conditions, not evidence of real-world accuracy. Four rounds of leak-hunting each found and fixed a genuine artifact (GPS-trace shape, audio clip reuse across the train/test split, IMU ring-down energy) and the headline metric barely moved. What the results DO support: the pipeline runs end to end on real Hugging Face data, degrades gracefully with any modality removed, and correctly rejects hard negatives with crash-sized kinematics. What they do not support: real-world recall or false-positive rate. **Model A must not be connected to any live dispatch path — including the simulated gateway in a public demo — until real crash telemetry exists.** |

### 7.2 Model B — Server-side road-risk prediction

| Aspect | Specification |
|---|---|
| Task | Predict probability of a severe crash on segment *s* during hour-bucket *t* under conditions *c* |
| Algorithm | **LightGBM** (primary) with **XGBoost** as a benchmark; gradient-boosted trees chosen for tabular data, small-data efficiency, native categorical handling, and — critically — **explainability via SHAP**, which matters when telling a government stakeholder *why* a stretch is risky |
| Unit of prediction | **500m road segment** (matched deliberately to MoRTH's iRAD blackspot definition) × 1-hour bucket |
| Label | Historical severe/fatal crash occurrence on that segment-hour (rare-event; addressed with class weighting + a Poisson-rate framing as an alternative head) |

**Feature groups:**

| Group | Features |
|---|---|
| **Static road geometry** | Segment length, curvature (max deflection angle), gradient, lane count, road class (OSM `highway=*`), surface, junction density within 500m, presence of a median, speed limit, urban/rural flag |
| **Historical** | Crash count (3y), fatal count (3y), official blackspot flag, KDE crash density, distance to nearest blackspot |
| **Temporal** | Hour of day, day of week, is-weekend, is-holiday, month, is-festival-period |
| **Light** | Solar elevation (computed, no API), civil-twilight flag, street-lighting presence from OSM |
| **Weather** | Precipitation rate, visibility (m), wind speed, temperature, humidity, weather condition code, **rain-onset-after-dry-spell flag** (first-rain slipperiness is a real and well-documented effect) |
| **Traffic** | Current speed, free-flow speed, **speed ratio (current/free-flow)** — the strongest live signal; congestion level; speed variance |
| **Derived interactions** | curvature × wet, visibility × speed-limit, night × unlit, speed-ratio × road-class |

| Aspect | Specification |
|---|---|
| Validation | **Spatio-temporal blocked CV** — hold out whole corridors *and* whole time periods. Random k-fold leaks badly on spatial data and would produce a flattering, meaningless number |
| Metrics | PR-AUC (primary; ROC-AUC is misleading under extreme imbalance), Brier score for calibration, **Precision@top-1%-segments** (the operationally meaningful metric: of the 1% we flag, how many actually see crashes) |
| Output | Calibrated probability → 4 bands via quantiles of the coverage-area distribution: **Low / Moderate / High / Severe** |
| Explainability | SHAP top-3 contributors returned with every risk score, so the driver-facing warning can say *"High risk: sharp curve + heavy rain + night"* rather than an opaque number |
| Serving | Baseline scores precomputed nightly for all segments × 168 hour-buckets; live inference only computes the weather/traffic delta. Model served in-process via `lightgbm.Booster`; **no separate model server** in v1 |
| Retraining | Monthly batch; new crash reports and confirmed alerts appended to the training set |

### 7.3 Model governance

- Models versioned as artifacts (`model_a_v1.3.tflite`, `model_b_v2.1.txt`) with a manifest recording training-data hash, metrics, and date. Every prediction persisted with its `model_version` so results are reproducible and regressions traceable.
- **Fairness check:** risk scores must not be systematically inflated for low-income/rural districts in a way that reflects reporting bias rather than actual danger. Under-reporting in rural areas is a known artefact of Indian crash data; we check score distributions across district-level socioeconomic strata and document the finding either way.

---

## 8. Functional Requirements

### 8.1 Crash detection & alerting

| ID | Requirement | Priority |
|---|---|---|
| FR-1.1 | The app SHALL sample accelerometer + gyroscope at ≥50 Hz during an active drive session | P0 |
| FR-1.2 | The app SHALL run on-device inference without any network dependency | P0 |
| FR-1.3 | The app SHALL gate ML inference behind a cheap threshold+speed pre-check | P0 |
| FR-1.4 | On detection, the app SHALL present a full-screen cancel prompt over the lock screen for 10s with audio, haptic, and TTS in the user's language | P0 |
| FR-1.5 | If the cancel window expires with no interaction, the app SHALL send the alert | P0 |
| FR-1.6 | The app SHALL log every cancellation locally and upload it as a hard negative when connectivity allows | P1 |
| FR-1.7 | The app SHALL offer a **manual SOS** button that bypasses detection entirely (for witnessing someone else's crash) | P0 |
| FR-1.8 | The alert payload SHALL include location, accuracy, timestamp, severity, speed at impact, heading, impact direction, rollover flag, post-impact motion, device+app version | P0 |
| FR-1.9 | The app SHALL attach the 12s sensor trace when sent over data | P1 |
| FR-1.10 | The app SHALL shorten the window to 5s when severity=CRITICAL and post-impact motion is zero | P2 |

### 8.2 Connectivity

| ID | Requirement | Priority |
|---|---|---|
| FR-2.1 | The app SHALL attempt HTTPS first with a 6s deadline | P0 |
| FR-2.2 | On HTTPS failure/timeout, the app SHALL send the compact `RRX1` SMS payload | P0 |
| FR-2.3 | For severity=CRITICAL, the app SHALL send SMS **in parallel** with HTTPS | P1 |
| FR-2.4 | The backend SHALL deduplicate multi-channel deliveries on `alert_uuid` | P0 |
| FR-2.5 | The app SHALL surface delivery status (Sent / Delivered / Acknowledged) to the user | P1 |
| FR-2.6 | The app SHALL retry the full payload upload via WorkManager for up to 24h | P1 |
| FR-2.7 | If all channels fail, the app SHALL sound a local siren and SMS the user's emergency contacts | P0 |

### 8.3 Backend

| ID | Requirement | Priority |
|---|---|---|
| FR-3.1 | The backend SHALL accept an alert and return `202 Accepted` within 400ms p95 | P0 |
| FR-3.2 | The backend SHALL map-match every alert to a road segment | P0 |
| FR-3.3 | The backend SHALL enrich with weather and traffic, degrading gracefully on any external timeout | P0 |
| FR-3.4 | The backend SHALL never let an enrichment failure block dispatch routing | P0 |
| FR-3.5 | The backend SHALL persist every alert, event transition, and risk evaluation immutably | P0 |
| FR-3.6 | The backend SHALL expose risk scores for a bbox / route / point | P0 |
| FR-3.7 | The backend SHALL serve risk as vector tiles for map rendering | P1 |
| FR-3.8 | The backend SHALL broadcast alert and status events over WebSocket | P0 |
| FR-3.9 | The backend SHALL identify the N nearest responder units to an incident | P1 |
| FR-3.10 | The backend SHALL export risk and incident history as CSV/GeoJSON | P2 |

### 8.4 Risk warnings

| ID | Requirement | Priority |
|---|---|---|
| FR-4.1 | The app SHALL fetch risk for the next 5 km along the current heading | P0 |
| FR-4.2 | The app SHALL warn by voice at risk band High and above | P0 |
| FR-4.3 | The app SHALL cache district-level risk tiles for offline use, badged as "cached" | P1 |
| FR-4.4 | The app SHALL suppress repeat warnings for the same segment within 15 min | P1 |
| FR-4.5 | The app SHALL suppress all voice warnings below 25 km/h | P1 |
| FR-4.6 | The warning SHALL state the top contributing reason (from SHAP) | P2 |

### 8.5 Gateway & dashboard

| ID | Requirement | Priority |
|---|---|---|
| FR-5.1 | The gateway adapter SHALL be a swappable interface with one simulated and one (future) real implementation | P0 |
| FR-5.2 | Every simulated dispatch SHALL be marked `SIMULATED` in the DB, the API response, and the UI | P0 |
| FR-5.3 | The gateway SHALL log every request/response for audit and demo replay | P0 |
| FR-6.1 | The dashboard SHALL render a live risk heatmap with 4 bands | P0 |
| FR-6.2 | The dashboard SHALL show a real-time alert log updating without refresh | P0 |
| FR-6.3 | The dashboard SHALL display the incident's status timeline and sensor trace | P1 |
| FR-6.4 | The dashboard SHALL display live metrics (latency, channel mix, cancel rate) | P1 |
| FR-6.5 | The dashboard SHALL provide a demo simulator console to inject synthetic crashes | P1 |

### 8.6 Account, privacy, and consent

| ID | Requirement | Priority |
|---|---|---|
| FR-7.1 | The app SHALL obtain explicit, granular consent for location, sensors, and SMS at onboarding with a plain-language explanation | P0 |
| FR-7.2 | The app SHALL allow the user to add up to 5 emergency contacts and medical info (blood group, allergies, conditions) | P1 |
| FR-7.3 | The app SHALL provide a hard "pause detection" toggle | P0 |
| FR-7.4 | The app SHALL allow full data deletion (DPDP Act right to erasure) | P0 |
| FR-7.5 | Continuous location SHALL NOT be uploaded — only crash-time location and coarse H3 cell for weather bucketing | P0 |

---

## 9. Data Model

PostgreSQL 16 + PostGIS 3.4. Abridged DDL:

```sql
-- ============ Devices & users ============
CREATE TABLE devices (
    device_id        UUID PRIMARY KEY,
    device_hash      TEXT NOT NULL UNIQUE,        -- salted hash of ANDROID_ID; no raw identifiers
    model            TEXT,
    android_version  TEXT,
    app_version      TEXT,
    locale           TEXT NOT NULL DEFAULT 'en-IN',
    msisdn_hash      TEXT,                        -- for SMS-channel attribution only
    registered_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen_at     TIMESTAMPTZ,
    consent_flags    JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE emergency_contacts (
    id           BIGSERIAL PRIMARY KEY,
    device_id    UUID NOT NULL REFERENCES devices ON DELETE CASCADE,
    name         TEXT NOT NULL,
    msisdn_enc   BYTEA NOT NULL,                  -- envelope-encrypted at rest
    relation     TEXT,
    priority     SMALLINT NOT NULL DEFAULT 1
);

-- ============ Road network ============
CREATE TABLE road_segments (
    segment_id      BIGSERIAL PRIMARY KEY,
    osm_way_id      BIGINT,
    geom            GEOMETRY(LineString, 4326) NOT NULL,
    length_m        REAL NOT NULL,                -- ~500m target, matching iRAD blackspot unit
    road_class      TEXT,                         -- motorway/trunk/primary/...
    lanes           SMALLINT,
    speed_limit_kmh SMALLINT,
    curvature_deg   REAL,
    gradient_pct    REAL,
    is_lit          BOOLEAN,
    is_urban        BOOLEAN,
    junction_count  SMALLINT,
    h3_r5           TEXT NOT NULL,                -- weather bucketing cell
    district        TEXT,
    state           TEXT
);
CREATE INDEX road_segments_geom_gix ON road_segments USING GIST (geom);
CREATE INDEX road_segments_h3_idx  ON road_segments (h3_r5);

CREATE TABLE historical_crashes (
    id           BIGSERIAL PRIMARY KEY,
    geom         GEOMETRY(Point, 4326) NOT NULL,
    segment_id   BIGINT REFERENCES road_segments,
    occurred_at  TIMESTAMPTZ,
    severity     TEXT,                            -- fatal/grievous/minor
    source       TEXT NOT NULL,                   -- 'MoRTH-2023' | 'state-open-data' | ...
    raw          JSONB
);
CREATE INDEX historical_crashes_geom_gix ON historical_crashes USING GIST (geom);

CREATE TABLE blackspots (
    id            BIGSERIAL PRIMARY KEY,
    geom          GEOMETRY(LineString, 4326) NOT NULL,
    source        TEXT NOT NULL,                  -- 'MoRTH-iRAD' | 'SaveLIFE-ZFC'
    designated_on DATE,
    fatal_count   SMALLINT,
    notes         TEXT
);

-- ============ Alerts ============
CREATE TYPE alert_channel  AS ENUM ('DATA','SMS','MANUAL_SOS');
CREATE TYPE alert_severity AS ENUM ('MINOR','MODERATE','SEVERE','CRITICAL');
CREATE TYPE alert_status   AS ENUM (
    'DETECTED','CONFIRMED','CANCELLED','SENT','RECEIVED',
    'ENRICHED','DISPATCHED','ACKNOWLEDGED','CLOSED','FAILED'
);

CREATE TABLE alerts (
    alert_uuid        UUID PRIMARY KEY,           -- client-generated; the idempotency key
    device_id         UUID REFERENCES devices,
    channel           alert_channel NOT NULL,
    status            alert_status  NOT NULL,
    severity          alert_severity NOT NULL,
    geom              GEOMETRY(Point, 4326) NOT NULL,
    gps_accuracy_m    REAL,
    occurred_at       TIMESTAMPTZ NOT NULL,       -- device clock, at impact
    received_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    speed_kmh         REAL,
    heading_deg       REAL,
    peak_g            REAL,
    delta_v_kmh       REAL,
    impact_direction  TEXT,                       -- front/rear/left/right/rollover
    rollover          BOOLEAN NOT NULL DEFAULT false,
    still_moving      BOOLEAN,
    segment_id        BIGINT REFERENCES road_segments,
    landmark          TEXT,
    conditions        JSONB,                      -- weather+traffic snapshot at receipt
    risk_score        REAL,
    risk_band         TEXT,
    model_a_version   TEXT,
    model_b_version   TEXT,
    is_simulated      BOOLEAN NOT NULL DEFAULT false,
    has_trace         BOOLEAN NOT NULL DEFAULT false
);
CREATE INDEX alerts_geom_gix     ON alerts USING GIST (geom);
CREATE INDEX alerts_received_idx ON alerts (received_at DESC);

CREATE TABLE alert_events (            -- immutable audit trail
    id          BIGSERIAL PRIMARY KEY,
    alert_uuid  UUID NOT NULL REFERENCES alerts ON DELETE CASCADE,
    status      alert_status NOT NULL,
    at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    actor       TEXT,                              -- 'device' | 'backend' | 'gateway-sim' | operator id
    detail      JSONB
);

CREATE TABLE sensor_traces (
    alert_uuid  UUID PRIMARY KEY REFERENCES alerts ON DELETE CASCADE,
    sample_hz   SMALLINT NOT NULL,
    payload     BYTEA NOT NULL,                    -- zstd-compressed float16 array
    label       TEXT                               -- 'crash' | 'cancelled_fp' -> training feedback
);

-- ============ Dispatch (simulated in v1) ============
CREATE TABLE dispatches (
    id                 BIGSERIAL PRIMARY KEY,
    alert_uuid         UUID NOT NULL REFERENCES alerts,
    gateway            TEXT NOT NULL,              -- 'SIMULATED_PM_RAHAT' | 'ERSS112_LIVE'
    is_simulated       BOOLEAN NOT NULL DEFAULT true,
    external_ticket_id TEXT,
    responder_unit_id  BIGINT,
    request_payload    JSONB NOT NULL,
    response_payload   JSONB,
    latency_ms         INTEGER,
    requested_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    acknowledged_at    TIMESTAMPTZ
);

CREATE TABLE responder_units (          -- seeded from public hospital/ambulance location data
    id          BIGSERIAL PRIMARY KEY,
    name        TEXT NOT NULL,
    kind        TEXT NOT NULL,                     -- ambulance | hospital | police | trauma_centre
    geom        GEOMETRY(Point, 4326) NOT NULL,
    capacity    SMALLINT,
    is_seeded   BOOLEAN NOT NULL DEFAULT true
);
CREATE INDEX responder_units_geom_gix ON responder_units USING GIST (geom);

-- ============ Risk ============
CREATE TABLE risk_evaluations (
    id             BIGSERIAL PRIMARY KEY,
    segment_id     BIGINT NOT NULL REFERENCES road_segments,
    evaluated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    hour_bucket    SMALLINT NOT NULL,              -- 0..167 hour-of-week
    risk_score     REAL NOT NULL,
    risk_band      TEXT NOT NULL,
    features       JSONB NOT NULL,
    top_factors    JSONB,                          -- SHAP top-3
    model_version  TEXT NOT NULL
);
CREATE INDEX risk_eval_seg_time_idx ON risk_evaluations (segment_id, evaluated_at DESC);

CREATE TABLE risk_baseline (            -- nightly precompute: segment × hour-of-week
    segment_id    BIGINT NOT NULL REFERENCES road_segments,
    hour_bucket   SMALLINT NOT NULL,
    base_score    REAL NOT NULL,
    model_version TEXT NOT NULL,
    computed_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (segment_id, hour_bucket)
);

CREATE TABLE weather_observations (
    h3_r5       TEXT NOT NULL,
    observed_at TIMESTAMPTZ NOT NULL,
    source      TEXT NOT NULL,                     -- 'OWM' | 'IMD'
    temp_c      REAL, precip_mm_h REAL, visibility_m INTEGER,
    wind_kmh    REAL, humidity_pct REAL, condition_code TEXT,
    PRIMARY KEY (h3_r5, observed_at, source)
);

CREATE TABLE traffic_observations (
    segment_id    BIGINT NOT NULL REFERENCES road_segments,
    observed_at   TIMESTAMPTZ NOT NULL,
    current_kmh   REAL, freeflow_kmh REAL, confidence REAL,
    PRIMARY KEY (segment_id, observed_at)
);
```

**Retention:** `risk_evaluations` and `*_observations` are partitioned monthly and pruned at 13 months (keeping one full seasonal cycle). `alerts`, `alert_events`, and `dispatches` are retained indefinitely as safety records but pseudonymised at 12 months (device linkage dropped).

---

## 10. API Specification

Base: `https://api.rrx.example/v1` · OpenAPI 3.1 at `/openapi.json` · Auth: `Authorization: Bearer <jwt>`

### 10.1 Device & alerts

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/devices/register` | Register device, receive `device_id` + token pair |
| `POST` | `/devices/{id}/heartbeat` | Liveness + config pull (thresholds, model version, feature flags) |
| `POST` | `/alerts` | **Primary crash-alert ingest.** Idempotent on `alert_uuid` |
| `POST` | `/alerts/{uuid}/trace` | Upload the compressed 12s sensor trace (deferred, retryable) |
| `POST` | `/alerts/{uuid}/cancel` | Post-hoc cancellation (user regained ability to act) |
| `GET` | `/alerts/{uuid}` | Status + dispatch state |
| `POST` | `/feedback/false-positive` | Upload a cancelled-window trace as a hard negative |
| `POST` | `/ingest/sms` | **Webhook** — SMS gateway posts inbound `RRX1` messages here |

**`POST /alerts` request:**
```json
{
  "alert_uuid": "9c1f7d3e-5b2a-4f18-9e77-2a4b6c8d0e11",
  "device_id": "3f2504e0-4f89-11d3-9a0c-0305e82c3301",
  "occurred_at": "2026-08-14T18:32:11.482+05:30",
  "location": { "lat": 12.91845, "lon": 80.22456, "accuracy_m": 8.0, "altitude_m": 14.2 },
  "motion": {
    "speed_kmh": 68.4, "heading_deg": 142.0, "peak_g": 9.1,
    "delta_v_kmh": 41.2, "impact_direction": "front",
    "rollover": false, "still_moving": false
  },
  "detection": { "p_crash": 0.93, "severity": "SEVERE", "model_version": "model_a_v1.3" },
  "window": { "duration_s": 10, "outcome": "EXPIRED" },
  "device_context": { "battery_pct": 43, "locale": "ta-IN", "app_version": "1.0.0" },
  "occupant_hint": 1,
  "is_simulated": false
}
```

**Response `202 Accepted`:**
```json
{
  "alert_uuid": "9c1f7d3e-5b2a-4f18-9e77-2a4b6c8d0e11",
  "status": "RECEIVED",
  "segment_id": 884213,
  "landmark": "NH-45, near Guduvancheri toll, Chengalpattu",
  "risk_context": { "score": 0.78, "band": "High",
                    "top_factors": ["night", "heavy_rain", "curvature"] },
  "dispatch": { "gateway": "SIMULATED_PM_RAHAT", "is_simulated": true,
                "ticket_id": "SIM-2026-0814-004417", "eta_note": "simulated" },
  "nearest_units": [
    { "id": 41, "name": "Chengalpattu GH Trauma", "kind": "trauma_centre", "distance_km": 6.2 }
  ]
}
```

### 10.2 Risk

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/risk/point?lat=&lon=&at=` | Risk for the nearest segment |
| `GET` | `/risk/route?polyline=&at=` | Banded risk along an encoded polyline (the app's main call) |
| `GET` | `/risk/bbox?minlat=&minlon=&maxlat=&maxlon=` | Segments + scores in a viewport |
| `GET` | `/risk/tiles/{z}/{x}/{y}.mvt` | Mapbox Vector Tile for the dashboard overlay |
| `GET` | `/risk/segments/{id}/history?from=&to=` | Time series for analytics |
| `GET` | `/risk/top?district=&limit=` | Currently riskiest segments |

### 10.3 Dashboard / ops

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/dashboard/alerts?status=&since=&bbox=` | Paginated alert log |
| `GET` | `/dashboard/metrics?window=24h` | Latency, channel mix, cancel rate, band distribution |
| `WS` | `/ws/events` | Live stream: `alert.created`, `alert.status_changed`, `risk.updated` |
| `POST` | `/sim/crash` | **Demo-only.** Inject a synthetic crash (guarded by role + env flag) |
| `POST` | `/sim/gateway/mode` | **Demo-only.** Set gateway to `ok` / `slow` / `fail` to demo resilience |
| `GET` | `/export/incidents.geojson` | MoRTH/NHAI export |

### 10.4 Error semantics

`4xx` for client faults, `503` with `Retry-After` for downstream saturation. **`/alerts` never returns a non-retryable error for a well-formed payload** — if persistence is degraded, it writes to a durable local queue and still returns `202`. An emergency ingest endpoint that can say "no" is a design bug.

---

## 11. The Simulated Government Gateway

### 11.1 Why it is simulated

ERSS-112 and PM RAHAT dispatch have no public API available to a hackathon team. Fabricating an integration would be dishonest and, in a safety product, actively dangerous. So:

> **Stage ⑤ is built as a clearly labelled simulation, and every artifact says so** — dashed red box in the architecture diagram, `SIMULATED` banner in the UI, `is_simulated=true` in the DB, `"gateway": "SIMULATED_PM_RAHAT"` in every API response, and a note on the slide itself.

### 11.2 What the simulation actually does

The simulator is not a stub that returns `200 OK`. It is a faithful mock of the dispatch workflow so that the *interface* is real even though the *counterparty* isn't:

1. Receives the enriched alert over the adapter contract.
2. Validates it against a dispatch-payload schema.
3. Creates an incident ticket with a realistic ID format and state machine.
4. Selects the nearest available `responder_unit` by PostGIS distance and marks it assigned.
5. Returns a synthetic acknowledgement with a plausible ETA and ticket reference.
6. Logs the full request/response pair for audit and demo replay.
7. Supports injectable failure modes (`slow`, `timeout`, `reject`) so we can demo that the system degrades correctly when the government endpoint misbehaves.

### 11.3 The swap path (this is the point)

```python
class DispatchGateway(Protocol):
    async def submit(self, incident: DispatchPayload) -> DispatchAck: ...
    async def status(self, ticket_id: str) -> DispatchStatus: ...
    async def cancel(self, ticket_id: str, reason: str) -> None: ...

# v1
class SimulatedPmRahatGateway(DispatchGateway): ...
# v2 — the only file that changes when access is granted
class Erss112Gateway(DispatchGateway): ...
```

Selected by config (`RRX_GATEWAY=simulated|erss112`). **Going live is a configuration change plus one adapter implementation — not a re-architecture.** That is the single most important thing this design buys.

### 11.4 The dispatch payload contract

```json
{
  "source_system": "RRX",
  "incident_type": "ROAD_ACCIDENT",
  "reported_at": "2026-08-14T18:32:11+05:30",
  "detection_method": "AUTOMATIC_ONDEVICE",
  "confidence": 0.93,
  "location": { "lat": 12.91845, "lon": 80.22456, "accuracy_m": 8.0,
                "landmark": "NH-45, near Guduvancheri toll", "district": "Chengalpattu", "state": "TN" },
  "severity": "SEVERE",
  "evidence": { "peak_g": 9.1, "delta_v_kmh": 41.2, "rollover": false, "post_impact_motion": false },
  "victim_hint": { "occupants_est": 1, "blood_group": "O+", "known_conditions": ["asthma"] },
  "conditions": { "weather": "heavy_rain", "visibility_m": 400, "light": "night", "traffic": "moderate" },
  "contact": { "msisdn_ref": "dev:3f2504e0", "language": "ta-IN" },
  "pm_rahat_eligible": true,
  "simulated": true
}
```

Note that this payload is **language-neutral structured data** — that is precisely how the language barrier is removed. The operator's system renders it in whatever language the operator reads.

---

## 12. Detailed Tech Stack

### 12.1 Android client

| Layer | Technology | Version | Why this choice |
|---|---|---|---|
| Language | **Kotlin** | 2.0.x | Official Android language; coroutines are the right model for concurrent sensor + network work |
| Min / target SDK | API 26 (Android 8.0) / API 35 (Android 15) | — | API 26 covers the low-end install base that is the entire point of this project |
| UI | **Jetpack Compose** + Material 3 | BOM 2024.09+ | Declarative UI; far less code for the alert overlay and countdown |
| Architecture | MVVM + Clean layering, Hilt DI | Hilt 2.52 | Testable sensor/detection layers, mockable for CI |
| Background | **Foreground Service** + `WorkManager` | WorkManager 2.9 | Only reliable way to run continuous sensing on modern Android |
| Activity detection | Play Services **Activity Recognition** | 21.0 | Gates sensing to actual driving — the single biggest battery win |
| Location | **FusedLocationProviderClient** | Play Services Location 21.3 | Battery-efficient fused GPS/network/sensor positioning |
| On-device ML | **TensorFlow Lite** (+ NNAPI/GPU delegate) | 2.16 | Mature Android runtime, tiny footprint, delegate fallback to CPU on old chips |
| Local DB | **Room** | 2.6.x | Offline queue, cached risk tiles, cancellation log |
| Networking | **Retrofit 2** + **OkHttp 4** + `kotlinx.serialization` | 2.11 / 4.12 | Standard, well-understood, easy timeout/retry control |
| SMS | **`SmsManager`** (`android.telephony`) | platform | Zero-data delivery path |
| Maps | **MapLibre GL Android** (or Google Maps SDK) | 11.x | MapLibre avoids Maps API billing and works with OSM tiles |
| TTS | Android `TextToSpeech` | platform | Multilingual voice countdown and warnings |
| Crypto | Android Keystore + EncryptedSharedPreferences | Security-crypto 1.1 | Token and medical-info storage |
| Testing | JUnit5, MockK, Turbine, Robolectric, Espresso | — | Sensor pipeline unit-tested with recorded traces |
| Build | Gradle 8.x, KSP, R8 | — | — |

**Key permissions:** `ACCESS_FINE_LOCATION`, `ACCESS_BACKGROUND_LOCATION`, `ACTIVITY_RECOGNITION`, `SEND_SMS`, `FOREGROUND_SERVICE`, `FOREGROUND_SERVICE_LOCATION`, `POST_NOTIFICATIONS`, `RECEIVE_BOOT_COMPLETED`, `USE_FULL_SCREEN_INTENT`, `WAKE_LOCK`.

> `SEND_SMS` and `ACCESS_BACKGROUND_LOCATION` both require a Play Store **permissions declaration** with a demo video. Budget for this — it is a real, weeks-long gate for public release (not for the hackathon demo, which side-loads).

### 12.2 Backend

| Layer | Technology | Version | Why this choice |
|---|---|---|---|
| Language | **Python** | 3.12 | Same language as the ML stack — no model-serving translation layer |
| Framework | **FastAPI** | 0.115+ | Async, Pydantic-native validation, free OpenAPI, WebSocket support built in |
| ASGI server | **Uvicorn** workers under **Gunicorn** | 0.30 / 22.0 | Standard production combo |
| Validation | **Pydantic v2** | 2.9+ | Rust-backed; validation is on the hot ingest path |
| ORM / migrations | **SQLAlchemy 2.0** + **Alembic** + **GeoAlchemy2** | 2.0 / 1.13 / 0.15 | Async ORM with first-class PostGIS types |
| Primary DB | **PostgreSQL** | 16 | — |
| Spatial | **PostGIS** | 3.4 | `ST_DWithin`, `ST_ClosestPoint`, GIST indexes — map-matching and nearest-responder are single queries |
| Cache / pubsub | **Redis** | 7.2 | Risk cache, dedup sentinel, WebSocket fan-out |
| Background jobs | **Celery** + Redis broker (or **ARQ** for a lighter footprint) | 5.4 | Nightly baseline recompute, feed polling, retraining triggers |
| Scheduling | **APScheduler** / Celery Beat | 3.10 | Weather/traffic poll cadence |
| Spatial indexing | **H3-py** | 4.1 | Weather-cell bucketing that keeps API quota tractable |
| Geometry | **Shapely 2**, **GeoPandas**, **pyproj** | 2.0 / 1.0 | ETL of the OSM network into 500m segments |
| Vector tiles | `pg_tileserv` or in-app **`ST_AsMVT`** | — | Risk overlay without a separate tile stack |
| HTTP client | **httpx** (async) with `tenacity` retries | 0.27 | Concurrent enrichment calls with hard timeouts |
| Auth | **python-jose** / `PyJWT` + `passlib[argon2]` | — | Device JWTs, dashboard sessions |
| Rate limiting | `slowapi` + Redis | — | With the emergency-path exemption from §6.3.1 |
| Testing | **pytest**, `pytest-asyncio`, **testcontainers**, `httpx.AsyncClient`, `factory_boy` | — | Real Postgres+PostGIS in CI via testcontainers |
| Quality | **Ruff**, **mypy**, **black** | — | — |
| Observability | **structlog** (JSON logs), **Prometheus** client, **OpenTelemetry**, **Sentry** | — | Latency budget in §6.3.2 needs real instrumentation |

### 12.3 ML / data

| Purpose | Technology | Version | Why |
|---|---|---|---|
| Risk model | **LightGBM** 4.7.0 (implemented) | pinned in `ml/requirements.txt` | Fast, accurate on tabular data, handles categoricals, small memory |
| Benchmark model | XGBoost — **named, not implemented** | — | Cross-check; the deck names both, but only LightGBM exists in `ml/risk_model/train.py`. Flagged in `ml/requirements.txt` rather than silently omitted |
| On-device model training | **TensorFlow 2.21.0 / Keras 3** → **TFLite converter** | pinned | Four-branch fusion network (IMU + on-device mel frontend + GPS + tabular), not the single-modality 1D-CNN this table originally described — see §7.1 |
| Numerics | NumPy 2.5.1, pandas 3.0.3, SciPy 1.16.3 | pinned | — |
| Baselines / metrics | scikit-learn 1.9.0 | pinned | Calibration, PR-AUC, blocked CV splitters |
| Explainability | **SHAP** 0.52.0 | pinned | Required for the "why is this risky" driver warning and for government trust |
| Imbalance | `imbalanced-learn` 0.12 | — | Sampling strategies for rare-event labels |
| Experiment tracking | **MLflow** 2.16 | — | Model registry, metrics, artifact versioning |
| Notebooks | JupyterLab | — | Feature exploration only; production code lives in modules |
| Feature store (v2) | — | — | Deliberately deferred; a table + Redis is sufficient at v1 scale |

### 12.4 Frontend dashboard

| Layer | Technology | Version | Why |
|---|---|---|---|
| Framework | **React 18** + **TypeScript 5.6** | — | — |
| Build | **Vite 5** | — | Fast HMR; a live demo benefits from quick iteration |
| Map | **Leaflet 1.9** + **react-leaflet 4** | — | Named in the deck; lightweight, OSM-native |
| Heavy overlays | **deck.gl 9** (optional) | — | GPU heatmap when segment count gets large |
| Basemap | OSM raster tiles / **MapLibre GL JS** | 4.x | No API-key dependency |
| Charts | **Chart.js 4** + `react-chartjs-2` | — | Named in the deck; sufficient for the metric panels |
| Server state | **TanStack Query 5** | — | Cache + refetch semantics for polling endpoints |
| Client state | **Zustand 4** | — | Minimal; avoids Redux boilerplate |
| Realtime | Native **WebSocket** + auto-reconnect | — | — |
| Styling | **Tailwind CSS 3.4** + **shadcn/ui** | — | Fast, consistent, accessible primitives |
| Forms/validation | react-hook-form + zod | — | — |
| Testing | Vitest, React Testing Library, Playwright | — | Playwright drives the end-to-end demo flow |

### 12.5 Infrastructure & DevOps

| Concern | Technology | Notes |
|---|---|---|
| Containers | **Docker** + **Docker Compose** | One-command local bring-up: api, worker, postgres+postgis, redis, web, sms-mock |
| Orchestration (pilot) | Docker Compose → **Kubernetes** at scale | K8s is not justified at hackathon scale; the Dockerfiles make the path available |
| CI/CD | **GitHub Actions** | Lint → typecheck → unit → integration (testcontainers) → build images → deploy |
| Hosting (demo) | **Railway / Render / Fly.io** for API+worker; **Vercel/Netlify** for the dashboard; **Supabase or Neon** for managed Postgres+PostGIS | Free/cheap tiers; zero-ops for a hackathon |
| Hosting (pilot) | **NIC Cloud / MeghRaj** or an Indian AWS/Azure region | **Data localisation is mandatory** — DPDP Act + government-data policy. Design for in-country hosting from day one |
| Object storage | S3-compatible (MinIO locally) | Sensor traces, model artifacts, exports |
| SMS gateway | **Gupshup / MSG91 / Kaleyra / Twilio** (dev) → **NIC SMS gateway** (gov pilot) | Inbound long-code webhook → `POST /ingest/sms` |
| Secrets | Doppler / SOPS + age; K8s Secrets in pilot | Never in the repo |
| Monitoring | Prometheus + Grafana; Sentry for errors; Uptime Kuma for endpoint liveness | Alert on ingest p95 breaching 400ms |
| Load testing | **k6** | Prove the ingest path holds under a mass-casualty burst |
| API mocking | WireMock / `respx` | Deterministic weather/traffic fixtures in CI |

### 12.6 Repository layout

```
rrx/
├─ android/                  # Kotlin app (Gradle multi-module)
│  ├─ app/                   # UI, onboarding, alert overlay, risk map
│  ├─ core-sensing/          # ring buffer, Stage-A gate, sensor abstraction
│  ├─ core-detection/        # TFLite runner, feature extraction, severity
│  ├─ core-transport/        # HTTP + SMS channel strategy, retry/queue
│  └─ core-data/             # Room, prefs, keystore
├─ backend/
│  ├─ app/
│  │  ├─ api/                # FastAPI routers
│  │  ├─ services/           # enrichment, dedup, routing, dispatch
│  │  ├─ gateways/           # DispatchGateway protocol + simulated + (future) erss112
│  │  ├─ models/             # SQLAlchemy
│  │  ├─ schemas/            # Pydantic
│  │  ├─ ml/                 # risk model loading + inference
│  │  └─ workers/            # Celery tasks: feeds, baseline recompute
│  ├─ alembic/
│  └─ tests/
├─ ml/
│  ├─ crash-detection/       # dataset build, training, TFLite export
│  ├─ risk-model/            # feature engineering, LightGBM training, SHAP
│  └─ notebooks/
├─ etl/                      # OSM → 500m segments; MoRTH crash ingestion
├─ web/                      # React dashboard
├─ sms-mock/                 # local inbound-SMS simulator
├─ infra/                    # docker-compose, k8s manifests, CI
└─ docs/                     # this PRD, ADRs, API docs, demo script
```

---

## 13. Non-Functional Requirements

### 13.1 Performance

| ID | Requirement |
|---|---|
| NFR-P1 | On-device inference ≤50ms on a Snapdragon 680-class SoC |
| NFR-P2 | Crash → HTTP alert dispatched from the device ≤2s after the window expires |
| NFR-P3 | Backend ingest → gateway call ≤400ms p95, ≤900ms p99 |
| NFR-P4 | End-to-end crash → gateway ack: **≤20s median on data, ≤90s on SMS** |
| NFR-P5 | Risk query (point/route) ≤300ms p95 |
| NFR-P6 | Dashboard event latency (backend → rendered) ≤1s |
| NFR-P7 | System sustains 100 alerts/minute burst (mass-casualty scenario) with no drops |

### 13.2 Battery (a first-class requirement)

| ID | Requirement |
|---|---|
| NFR-B1 | ≤4% battery per hour of active drive-session sensing on a 4,000 mAh mid-tier device |
| NFR-B2 | ≤1% per hour when idle (not driving) — Activity Recognition only |
| NFR-B3 | Sensor sampling automatically reduced to 25 Hz below 15% battery, with the user told |
| NFR-B4 | Verified with Battery Historian on at least three device tiers before demo |

Battery is where well-meaning safety apps die. If it costs 15%/hour, users uninstall it, and a system nobody runs saves nobody.

### 13.3 Reliability & availability

| ID | Requirement |
|---|---|
| NFR-R1 | Backend availability ≥99.5% (pilot target ≥99.9%) |
| NFR-R2 | No single external API failure may block dispatch (all enrichment is optional) |
| NFR-R3 | Client-side durable queue survives process death and reboot |
| NFR-R4 | Database backed up daily with PITR; RPO ≤15 min, RTO ≤1h |
| NFR-R5 | Graceful degradation ladder is explicit and tested for every stage (§5.2) |

### 13.4 Security

| ID | Requirement |
|---|---|
| NFR-S1 | TLS 1.3 everywhere; certificate pinning in the Android client |
| NFR-S2 | Emergency contacts and medical info encrypted at rest (envelope encryption, per-record DEK) |
| NFR-S3 | Device auth via short-lived JWT (15 min) + rotating refresh token |
| NFR-S4 | RBAC on all dashboard and export endpoints; every export audit-logged |
| NFR-S5 | No PII in logs; structlog processors redact `msisdn`, precise coordinates, and names |
| NFR-S6 | Dependency scanning (Dependabot, `pip-audit`, `npm audit`) blocking in CI |
| NFR-S7 | SMS ingest webhook authenticated via HMAC signature + source-IP allowlist — **inbound SMS is a spoofable channel and must be treated as untrusted input** |
| NFR-S8 | Anti-abuse: swarm detection on implausible alert volume per device/area, rate-limited to protect responders from a malicious flood |

### 13.5 Privacy & compliance

| ID | Requirement |
|---|---|
| NFR-PR1 | **Digital Personal Data Protection Act, 2023 (DPDP)** compliance: purpose limitation, explicit consent, right to erasure, breach notification |
| NFR-PR2 | **Data minimisation:** continuous location is never uploaded. Only (a) crash-time position, (b) coarse H3-res5 cell for weather bucketing, (c) segment-level risk queries |
| NFR-PR3 | Data localisation — all storage in Indian regions |
| NFR-PR4 | Device identifiers stored only as salted hashes |
| NFR-PR5 | One-tap account + data deletion, honoured within 30 days |
| NFR-PR6 | A published, plain-language privacy policy in all supported languages |
| NFR-PR7 | Emergency-override disclosure: users are told, before consent, that a confirmed crash transmits location and medical info to emergency services |

### 13.6 Accessibility & localisation

| ID | Requirement |
|---|---|
| NFR-A1 | WCAG 2.1 AA on the dashboard |
| NFR-A2 | App usable one-handed; cancel button ≥64dp touch target |
| NFR-A3 | Risk bands distinguishable without colour |
| NFR-A4 | Full TalkBack support on the alert screen |
| NFR-A5 | 5 languages at demo; string architecture supports all 22 scheduled languages |
| NFR-A6 | Audio alerts audible over road noise (≥85 dB at max, overriding silent mode) |

---

## 14. Feasibility and Viability

### 14.1 Why this is buildable

- **Entirely public data.** MoRTH reports, OSM, OpenWeatherMap/IMD, TomTom free tier. No procurement, no NDAs, no paid datasets.
- **Conventional, boring stack.** FastAPI, PostGIS, tree-based ML, React — every piece is mature, documented, and known to the team. Nothing here is a research project.
- **No new hardware.** Runs on phones people already own. This is the difference between a pilot and a procurement programme.
- **Plugs into an existing scheme.** PM RAHAT launched February 2026; we make an already-funded national programme perform closer to its intent rather than proposing a parallel system.
- **Existing legal precedent.** The ₹25,000 Good Samaritan reward already establishes that the state pays to accelerate crash reporting. This automates the same intent.
- **Proven analogue.** SaveLIFE Foundation's Zero Fatality Corridor showed >50% fatality reduction on the Mumbai–Pune Expressway with a data-driven approach — evidence the underlying thesis works; we make it real-time and scalable.

### 14.2 Risks and mitigations

| # | Risk | Severity | Mitigation |
|---|---|---|---|
| R1 | **False crash detections** waste emergency resources and destroy credibility | High | Two-stage detection with a speed pre-condition; **10-second cancel window**; conservative threshold tuned for FP rate not accuracy; hard-negative feedback loop; per-device swarm limits |
| R2 | **No real ERSS-112 API access** | High | Clearly labelled simulated gateway behind a swappable `DispatchGateway` interface; going live is a config change. Honesty about this is a strength in judging, not a weakness |
| R3 | **Rural/highway signal gaps** — exactly where crashes are worst | High | **SMS fallback** requiring zero data; parallel-send on CRITICAL; local siren + emergency-contact SMS as the last rung |
| R4 | **Battery drain** causes uninstalls | High | Activity-Recognition gating; Stage-A arithmetic gate before ML; adaptive sampling; explicit budget in NFR-B1; Battery Historian verification |
| R5 | **Sparse / biased accident data** for the risk model | Medium | Blend historical crashes with road-geometry priors so unsampled segments still get a sensible score; spatio-temporal blocked CV to avoid fooling ourselves; document under-reporting bias; treat the model as *decision support*, never automation |
| R6 | **Privacy backlash** over continuous location | High | Never upload continuous location (NFR-PR2); coarse H3 bucketing; on-device-first design; DPDP compliance; transparent, translated policy |
| R7 | **API quota exhaustion** on free tiers | Medium | H3 cell bucketing, active-cell-only polling, aggressive Redis caching, nightly baseline precompute, stale-cache degradation |
| R8 | **OEM background-kill** (Xiaomi/Oppo/Vivo) silently disables detection | High | Battery-optimisation whitelist prompt in onboarding; periodic self-check with a user-visible "protection active/inactive" indicator; `dontkillmyapp.com`-style per-OEM guidance |
| R9 | **Play Store rejection** of `SEND_SMS` / background location | Medium | Prepare the permissions declaration + demo video early; SMS is core-functionality-justified; have a side-load/APK distribution path for the pilot |
| R10 | **Model can't be validated on real Indian crash telemetry** in time | Medium | Be explicit about this limitation in the deck; validate on public + synthetic data; design the hard-negative pipeline so real-world validation begins the day the pilot starts |
| R11 | **Malicious mass false alerts** (DoS on responders) | Medium | Device attestation (Play Integrity API), per-device and per-area rate anomaly detection, operator-side confirmation for implausible clusters |
| R12 | **Clock skew** on the device corrupts timestamps | Low | Server records `received_at` independently; device time treated as a hint, reconciled and flagged when skew >60s |

---

## 15. Impact and Benefits

### 15.1 Social

- Removes the **"which phone, which language"** lottery that currently determines whether a crash victim gets timely help.
- Highest marginal value exactly where help is thinnest: highways and rural roads, where bystander density and connectivity are both lowest and where crashes are more likely to be fatal.
- Removes the bystander's decision entirely — no Good Samaritan hesitancy, no language barrier with the operator, no "where exactly are you?"

### 15.2 Economic

- Faster golden-hour response directly attacks the productivity and long-term-disability costs behind India's **~3% of GDP** annual road-accident loss.
- **Zero incremental hardware cost.** Marginal cost per protected user ≈ app install + a fraction of a server. This is a software-only intervention against a hardware-scale problem.
- Preventing disability is worth far more than preventing an ambulance trip: the cost tail of a survivable crash handled badly is decades long.

### 15.3 Governance

- Feeds directly into **PM RAHAT's own dispatch pipeline**, helping a live national scheme perform closer to its intended purpose.
- Generates a **live, fine-grained risk dataset** that lets MoRTH/NHAI shift blackspot identification from a reactive, 3-year-lagging exercise to a proactive, real-time one — the same shift SaveLIFE demonstrated on one corridor, made available everywhere.
- Provides an evidence base for targeted enforcement and infrastructure spend: *which* 500m stretches, under *which* conditions, at *which* hours.

### 15.4 Measurable success criteria

| Horizon | Metric | Target |
|---|---|---|
| Demo (SIH) | End-to-end crash→simulated-ack latency | <20s on data, <90s on SMS |
| Demo | Detection recall on the test set | ≥90% |
| Demo | Post-cancel false dispatches during the live demo | 0 |
| Pilot (3 mo, 1 corridor, 500 users) | Confirmed crashes auto-reported | ≥80% of crashes in the cohort |
| Pilot | Median time-to-dispatch vs. baseline call | ≥50% reduction |
| Pilot | Cancel rate (false-positive proxy) | <2 per 100 drive-hours |
| Pilot | 30-day app retention | ≥60% (the battery test, in practice) |
| Scale (12 mo) | Risk-model Precision@top-1% segments | ≥3× the random baseline |
| Scale | Segments covered | ≥50,000 km of NH/SH network |

---

## 16. Development Plan

### 16.1 Hackathon build (6 sprints × 1 week)

| Sprint | Focus | Exit criteria |
|---|---|---|
| **S0** | Foundations | Repo scaffolded, Docker Compose brings up api+db+redis+web, CI green, OSM→500m segment ETL run for one district |
| **S1** | Detection core | Ring buffer + Stage-A gate + TFLite stub running on a real phone; recorded sensor traces from controlled drops/hard-brakes |
| **S2** | Alert path | Cancel window UI, HTTP channel, `POST /alerts` ingest, alerts persisted, dashboard alert log live over WebSocket |
| **S3** | SMS + resilience | `RRX1` protocol, `SmsManager` send, SMS webhook ingest, dedup, retry queue; failure-mode demo works |
| **S4** | Risk model | Feature pipeline, LightGBM trained + evaluated with blocked CV, baseline precompute, `/risk/*` endpoints, dashboard heatmap |
| **S5** | Gateway + polish | Simulated gateway with responder assignment, incident detail view, 5-language localisation, simulator console |
| **S6** | Harden + demo | Battery profiling, k6 load test, end-to-end Playwright demo script, rehearsed jury walkthrough, deck rebuilt against the working system |

### 16.2 Demo script (what the jury actually sees)

1. Phone on stage, app running, drive session active. Show the risk map colouring a stretch **High** because of live rain.
2. Trigger a crash via a controlled shake rig (or the simulator, labelled as such) → full-screen countdown, Tamil TTS, siren.
3. Let it expire. Alert appears on the dashboard **in under 20 seconds**, with location, severity, sensor trace, and conditions.
4. Show the simulated dispatch ticket with its `SIMULATED` banner. State plainly that this is the one mocked component and show the one-line config that swaps it for a real gateway.
5. **Put the phone in airplane mode.** Trigger again. The SMS path fires, the alert still lands. This is the moment that wins the room.
6. Show the metrics panel: latency distribution, channel mix, cancel rate.
7. Show the analyst view: today's riskiest segments vs. the official static blackspot list, side by side.

### 16.3 Post-hackathon roadmap

| Phase | Scope |
|---|---|
| **P1 (0–3 mo)** | Pilot on one corridor with a partner (SaveLIFE / state road-safety cell); real hard-negative collection; battery hardening across OEMs |
| **P2 (3–6 mo)** | iOS companion (risk warnings + manual SOS; defer to native crash detection); formal ERSS-112 / PM RAHAT integration approach; Play Store permissions clearance |
| **P3 (6–12 mo)** | Model retraining on pilot data; multi-vehicle incident correlation; hospital bed-availability integration; MoRTH data-sharing pipeline |
| **P4 (12 mo+)** | Two-wheeler-specific detection models (India's dominant crash category, and a genuinely different signal profile); fleet/commercial-operator tier; state-level analyst tooling |

---

## 17. Open Questions

| # | Question | Owner | Needed by |
|---|---|---|---|
| Q1 | Which corridor/district is the v1 coverage area? (Determines ETL scope and demo geography) | Team | S0 |
| Q2 | Which SMS gateway for the demo — a paid dev account (Twilio/MSG91) or a local mock? Inbound long-codes take days to provision | Team | S3 |
| Q3 | Can we obtain any real crash-telemetry corpus, or is synthetic + public the honest answer for v1? | ML lead | S1 |
| Q4 | Do we have a controlled way to generate real impact signatures (shake rig, low-speed test) for validation? | Team | S1 |
| Q5 | Is there a faculty/industry-mentor route to a conversation with a state ERSS-112 cell? Even a "no" documented is worth having | Mentors | S5 |
| Q6 | Are published iRAD blackspot lists machine-readable for our corridor, or is it manual transcription? | Data lead | S4 |
| Q7 | Two-wheelers are the majority of Indian road fatalities and have a very different sensor profile. Do we scope v1 to four-wheelers explicitly, or attempt both? | Product | S1 |
| Q8 | Deck says SIH **2025** on the title slide; filename says **2026**. Which is correct? | Team | Immediately |

---

## 18. Appendix A — Glossary

| Term | Meaning |
|---|---|
| **PM RAHAT** | Road Accident Victims' Hospitalisation and Assured Treatment scheme; cashless treatment up to ₹1.5 lakh for 7 days, ERSS-112 dispatch-integrated (PIB, 14 Feb 2026) |
| **ERSS-112** | Emergency Response Support System — India's single emergency number |
| **iRAD / e-DAR** | Integrated Road Accident Database / electronic Detailed Accident Report (MoRTH + NIC, World Bank funded) |
| **Blackspot** | Per MoRTH: a 500m stretch with 5+ fatal/grievous accidents **or** 10+ deaths in 3 years |
| **ZFC** | Zero Fatality Corridor — SaveLIFE Foundation's model, >50% fatality reduction on the Mumbai–Pune Expressway |
| **Golden Hour** | The first hour post-trauma, within which hospitalisation is most survival-determining |
| **H3** | Uber's hexagonal hierarchical geospatial index; res-5 ≈ 250 km² per cell |
| **MVT** | Mapbox Vector Tile |
| **Delta-V** | Change in velocity across an impact — the standard crash-severity proxy |
| **Hard negative** | A near-miss sample the model got wrong, used to retrain against false positives |

## 19. Appendix B — References

| # | Title | Source | Date |
|---|---|---|---|
| 1 | PM-RAHAT Scheme — Launch Notification | Press Information Bureau, GoI | 14 Feb 2026 |
| 2 | Socio-Economic Cost of Road Accidents in India (~3.14% of GDP) | MoRTH, citing DIMTS / TRIPP–IIT Delhi | ongoing |
| 3 | "Road Accidents Cost Nation 3% of GDP Annually" — Nitin Gadkari | All India Radio / News on AIR | 25 Mar 2025 |
| 4 | Zero Fatality Corridor (ZFC) Model | SaveLIFE Foundation | est. 2016, ongoing |
| 5 | "A New Model for Reducing Global Traffic Deaths: India's Zero Fatality Corridors" | Stanford Social Innovation Review | 2023 |
| 6 | "Delivering Road Safety in India" | The World Bank | 20 Feb 2020 |
| 7 | "Making India's Roads Safer" | The World Bank | 28 Nov 2022 |
| 8 | iRAD / e-DAR — Black Spot Identification Criteria | MoRTH + NIC, World Bank funded | 2021–22, ongoing |
| 9 | Crash Detection (Apple) — Technical Overview | Apple Newsroom / ZDNet | 7 Sep 2022 |
| 10 | "Samsung Galaxy S25 Ultra May Finally Come With This Life-Saving Pixel Feature" | Android Police | 30 Dec 2024 |

---

*End of document.*
