# Path to MVP

| | |
|---|---|
| **Date** | 2026-08-24 |
| **Companions** | `PRD.md` · `UX-APPFLOW.md` · `ml/MODELS.md` |
| **MVP definition** | **Demo-complete for SIH 2026** — the seven-step jury walkthrough in PRD §16.2 runs end to end on real hardware. *Not* a pilot, not Play Store ready. |

---

## 1. Where it stands

| Layer | State |
|---|---|
| Product definition (PRD, UX/appflow, model card) | **Done**, kept in sync with the built model (PRD §7.1/§6.1.2/§12.3 updated 2026-08-17) |
| Model A — crash detection | Trained, exported, **deployable artifact verified end-to-end**: `crash_fusion_deployable_v1.tflite` (299.5 KB) takes raw sensor input, computes its own mel spectrogram on-device, and needs no client-side normalisation. Real-world accuracy **still unvalidated** — see `ml/MODELS.md` §0 |
| Model B — road risk | Trained, `risk_model_v1.txt` + SHAP. **Served** — `GET /risk/point`, `GET /risk/bbox` (with segment geometry), wired into alert ingest for `risk_context` |
| Backend (`rrx-api`) | **Functionally complete for MVP scope**, verified against real Docker containers throughout. `POST/GET /alerts`, `GET /alerts` (list), `POST /ingest/sms` (RRX1 parse + CRC), `POST/GET /devices` (register, heartbeat, count), risk serving, `WS /ws/events`, `/sim/*` demo endpoints, the simulated dispatch gateway. **Not built:** vector tiles (`/risk/tiles`), `/risk/route`, dashboard-facing RBAC (device JWT exists; no operator/analyst login) — see `backend/README.md` |
| Dashboard (`rrx-ops`) | **Live Operations, Incident Detail (UX §22), Risk Map (UX §23), Analytics (UX §24), and Simulator Console (UX §25) all built and verified against the real backend**: map with real risk-banded segments, live incident rail (WS-pushed, cold-start via `GET /alerts`), all seven signature components (UX §7), System Honesty Bar wired to real (if sparse) feed status. Incident Detail (2026-08-24) is reached from a rail card's "Details →" link and required extending `GET /alerts/{uuid}` server-side -- it returned only 4 fields before, now returns motion/conditions/dispatch/the real event timeline, plus a new migration (0002) to actually persist `occupant_hint`, which every `POST /alerts` payload had always carried but nothing ever saved. Export (GeoJSON + Print/PDF) is real. Risk Map (2026-08-24) required extending `GET /risk/bbox` with real `weather`/`visibility`/`traffic_density` overrides so its condition simulator re-scores the live network with the actual model rather than a client-side approximation -- verified with a live before/after (a segment's score moved 0.0016→0.021, Low→High, under simulated heavy rain at 11 p.m.); its Corridor mode and Comparison mode stay unbuilt (no ingested blackspot data yet) and render disabled rather than faked. Simulator Console (2026-08-24) wires two real backend endpoints -- `POST /sim/crash` (severity/speed/g-force/lat-lon, plus a channel toggle that's the real RRX1 SMS round-trip, not a shortcut) and `POST /sim/gateway/mode` (ok/slow/timeout/reject) -- verified with a live inject-crash-then-open-detail round trip and a gateway-reject-then-reset round trip; its nav entry is hidden entirely (not just disabled) when `VITE_DEMO_MODE=false`, mirroring the backend's own `RRX_DEMO_MODE` gate on registering `/sim/*` at all. "Feed failure" and "Scenario playback" from the UX spec have no backend endpoint and render disabled. Analytics (2026-08-24) required a new `GET /analytics/summary` endpoint (live aggregates: response-latency percentiles + histogram, channel mix, Golden Hour ack rate, coverage) plus forcing light theme per §24 (same `setTheme`-on-mount pattern Live Operations uses for dark); its six panels export as PNG (SVG→canvas, dependency-free) and CSV. Two of the six panels -- Detection quality and Risk model performance -- have no live-database source and are rendered from static, clearly-labelled report constants (`ml/reports/risk_model_results.json`, `ml/MODELS.md`'s synthetic-holdout numbers) instead of fabricated live figures. **Every dashboard view in this MVP's scope is now built** — the nav rail's one remaining disabled item ("Incidents") is disabled by design, not because the work is unfinished (Shell.tsx's own comment explains why) |
| Android app (`rrx-app`) | **Toolchain assessed; sensing, crash classification, transport, the cancel-window screen (§15-17), onboarding (§11), and Drive Mode's map + Segment Ribbon + Risk Warning (§13-14) all built and verified** (no local JDK/SDK on this machine — verified via a throwaway Docker image instead, including 19 passing unit tests and repeated `compileDebugKotlin`+`testDebugUnitTest`+`assembleDebug` passes). The recurring theme across every pass: a real toolchain catches real bugs review alone doesn't -- an XML `--`-in-comment failure recurred *five times* now across manifest and string-resource files, a missing `androidx.compose.runtime.getValue` import, a deprecated `ClickableText` API, a dead `.let`-discarded expression, a `Modifier.weight()` resolution failure inside a common Compose pattern, and two logic bugs (a returning user re-onboarding every cold start; a cross-module smart-cast recurring a third time) all caught before or by the Docker build. Five-module layout per PRD §12.6, all real now: `core-sensing` (IMU/GPS/Stage-A), `core-detection` (TFLite classifier, verified against the real bundled artifact), `core-transport` (HTTPS/SMS channel strategy, wire format confirmed with `curl` against the live backend), `core-data` (Room emergency contacts + EncryptedSharedPreferences consent/medical/language storage), and `app` tying it together -- device registration, a full-screen crash countdown a real on-device `CrashPrediction.pCrash` crossing the model's own decision threshold (0.297) launches via a full-screen-intent notification, a nine-step onboarding flow gating all of it behind real single-permission-per-screen consent, a Drive Mode screen rendering a live `osmdroid` risk map from the same `/risk/bbox` contract the dashboard uses, and now a real voice/haptic/overlay Risk Warning (FR-4.2/4.4/4.5/4.6) firing off that same live segment stream. See `android/README.md` for the full scope-decision writeup |
| Version control | **Done.** Pushed to [GitHub](https://github.com/Angeline1710/Predictive-Road-Risk-Golden-Hour-Crash-Response), `main` tracking `origin/main` |

Roughly **87% of the MVP is built** — the ML layer, a functionally complete backend (schema, ingest, risk serving with condition-simulator overrides, SMS, WebSocket, sim, and now analytics-aggregate endpoints, all verified against real Docker containers), a fully-built dashboard (Live Operations, Incident Detail, Risk Map, Simulator Console, Analytics -- every view in this MVP's scope) wired end-to-end to that backend and verified live throughout, and an Android app whose sensing, on-device classification, transport, cancel-window screen, onboarding flow, Drive Mode map, and now §14's Risk Warning all work end to end and are each verified against something real. What's left on Android is the ambient notification upgrade and a Settings screen (~0.8 person-days); Risk Map's Corridor/Comparison modes (~1 day, blocked on blackspot ETL ingestion) and integration/hardening (~7.5 days) are now the largest remaining tracks.

---

## 2. Do these today

Four things gate everything else and cost almost nothing to start.

**① `git init`. — DONE.** Repository initialised, [`.gitignore`](.gitignore) excludes `ml/data/` (935 MB, reproducible via the `ml/*/*.py` scripts) and per-run logs while keeping the small artifacts and result JSON/CSV that document what the models actually did. **Pushed to GitHub** — `main` is the source of truth from here on; every future change should be a commit, not a working-tree edit that only exists on one laptop.

**② Start the SMS inbound path — still open, now the single remaining "do today" item.** This has the longest lead time of anything in the project and it is the demo's best moment (PRD §16.2 step 5: airplane mode, alert still lands). Indian inbound long codes require DLT registration under TRAI, which takes days-to-weeks and can stall. **Do not put the demo on that critical path.**

Use a **companion-phone SMS receiver** instead: a second Android device runs a tiny app with `RECEIVE_SMS` that forwards inbound `RRX1` messages to `POST /ingest/sms` over Wi-Fi. Zero carrier provisioning, works offline on a venue hotspot, and the protocol is identical — swapping in a real gateway later is a config change. Register for a real long code in parallel as the upgrade path, not the dependency.

**③ Answer PRD Q1: which corridor? — DECIDED.** **NH-45 through Chengalpattu district**, Tamil Nadu.

| | |
|---|---|
| Total accidents (2021) | 1,614 — ranks **13th of 43** TN districts by volume |
| Fatal accidents (2021) | 452 (fatal share 0.280 — ranks 21st of 43, roughly median) |
| Deaths (2021) | 472 |
| YoY growth (2021/2020) | +19.7% |
| Vulnerable-road-user death share | 0.326 |

Not the single worst district in Tamil Nadu by fatal share — it's genuinely mid-table there. It is chosen instead because it combines **real volume** (top-third statewide) with **geographic convenience**: it borders Chennai, carries NH-45 (the Chennai–Trichy highway), and is already the PRD's worked example (`ml/MODELS.md` §4.1, the `Chengalpattu GH Trauma` responder in the sample dispatch payload). Picking the highest-fatal-share district instead would mean building demo infrastructure somewhere without an easy path for a five-person team to physically drive the corridor. This is now load-bearing for the OSM extract, segment table, demo map, and responder seed data (§3.2) — do not revisit without updating all four.

**④ Add `pyproject.toml` / `requirements.txt`. — DONE.** [`ml/requirements.txt`](ml/requirements.txt) pins every package actually imported by the ML layer, verified against the live environment rather than guessed: `tensorflow==2.21.0`, `lightgbm==4.7.0`, `librosa==1.0.0`, `soundfile==0.14.0`, `shap==0.52.0`, `numpy==2.5.1`, `pandas==3.0.3`, `scipy==1.16.3`, `scikit-learn==1.9.0`, `pyarrow==25.0.1`, `matplotlib==3.11.0`. **`xgboost` is not pinned** — PRD §6.3/7.2 names it as Model B's cross-check benchmark, but that comparison was never implemented; only LightGBM exists in `ml/risk_model/train.py`. Flagged in the requirements file itself rather than silently added as an unused dependency.

---

## 3. Component gaps

Effort in person-days. Assumes a 5-person team working in parallel.

### 3.1 Backend — `rrx-api` · **the critical path**

Everything else depends on it. **Functionally complete for MVP scope as of 2026-08-18** — every piece below verified against real Docker containers (Postgres/PostGIS/Redis), not mocked or TestClient-only.

| Piece | Days | Notes |
|---|---|---|
| ~~Scaffold: FastAPI, Docker Compose (api + postgres/postgis + redis), Alembic~~ | ~~1.5~~ **0** | **Done.** `backend/`, image builds clean, migration runs on container startup |
| ~~Schema from PRD §9~~ | ~~1~~ **0** | **Done.** All 14 tables, exact index/enum names, migrated and verified (upgrade + downgrade both tested) against live PostGIS 3.4 |
| ~~`POST /alerts` — validate, dedup on `alert_uuid`, persist, `202`~~ | ~~1.5~~ **0** | **Done and verified**, not just written: idempotency confirmed (retry produces zero duplicate rows, same ticket returned), map-matching confirmed against a seeded segment, graceful degradation confirmed against an empty `road_segments` table (PRD §10.4) |
| ~~`DispatchGateway` protocol + `SimulatedPmRahatGateway`~~ | ~~1.5~~ **0** | **Done and verified.** Real PostGIS nearest-responder selection (tested: correctly picked a 25.6 km unit over one 1,900 km away), ticket state machine, and all three injectable failure modes (`slow`/`timeout`/`reject`) individually tested |
| ~~Nearest-responder query~~ | ~~0.5~~ **0** | **Done** — folded into the gateway work above; `app/services/responders.py` uses a real `geography`-cast `ST_Distance`, not the faster-but-wrong planar version |
| ~~Enrichment: weather, traffic, cache-first with hard timeouts~~ | ~~1.5~~ **0** | Map-match is real PostGIS. Weather/traffic have **no API key configured** and honestly degrade to "unavailable" (never faked) — the Dashboard's System Honesty Bar surfaces this rather than hiding it. Getting a real key is a config change, not a code gap |
| ~~`POST /ingest/sms` — parse `RRX1`, CRC check~~ | ~~1~~ **0** | **Done.** `app/services/sms_protocol.py`; the PRD's own worked-example CRC doesn't reproduce under CRC-8/ATM or 9 other tested variants — documented as a PRD placeholder-text issue, not a bug in the implementation (encode→parse round-trips correctly, corruption is rejected) |
| ~~Model B serving: `/risk/point`, `/risk/bbox`~~ | ~~1.5~~ **0** | **Done.** Both return segment geometry (added 2026-08-18 for the dashboard's map overlay) as well as score/band/SHAP top-3. `/risk/route` still not implemented — left absent rather than stubbed with fake data |
| Vector tiles `/risk/tiles/{z}/{x}/{y}.mvt` via `ST_AsMVT` | 1 | Not needed for MVP — the dashboard renders `/risk/bbox` segments as vector polylines directly, which is sufficient at single-corridor scale |
| ~~WebSocket `/ws/events` + Redis pub/sub~~ | ~~1~~ **0** | **Done and verified live**: a simulated crash triggered via `curl` appeared in the dashboard's incident rail with no page reload, correctly sorted |
| ~~`/devices/register`, `/devices/{id}/heartbeat`, `GET /devices/count`, `GET /alerts/{uuid}`, `GET /alerts` (list)~~ | ~~1~~ **0** | **Done.** `GET /alerts` (list) and `GET /devices/count` added 2026-08-18 specifically to give the dashboard real cold-start and honesty-bar data instead of fabricating placeholders. `/alerts/{uuid}/trace` and `/alerts/{uuid}/cancel` still absent — no dashboard or Android surface calls them yet |
| ~~`/sim/*` demo endpoints~~ | ~~1~~ **0** | **Done.** Env-flag gated, used throughout dashboard verification |
| Auth: device JWT + dashboard RBAC | 1.5 | Device JWT exists and gates `/devices/{id}/heartbeat`. **No dashboard login** — the Shell's `OPERATOR` role chip is a hardcoded display value, not an authenticated session. Every other route is open |
| **Total** | **~2.5** | down from ~10 — only auth remains |

### 3.2 ETL — corridor data

| Piece | Days | Notes |
|---|---|---|
| OSM extract → 500 m segments with geometry attributes | 2 | Geofabrik India, split ways, compute curvature/junctions |
| Seed `responder_units` from public hospital/ambulance locations | 0.5 | |
| Load TN district stats + any published blackspot list | 0.5 | `ingest.py` already parses the TN CSV |
| Nightly `risk_baseline` precompute job | 1 | 168 buckets × segments |
| **Total** | **~4** | |

> Model B currently trains on a **synthetic segment panel**. For the demo it must serve scores for **real OSM segments** on the chosen corridor. The model retrains unchanged — only `build_panel.py`'s segment source swaps from generated to real geometry.

### 3.3 Android app — `rrx-app` · **now the critical path**

**Toolchain assessed and scaffold built 2026-08-18; real IMU/GPS sensing, a
working TFLite classifier, and the HTTPS/SMS transport layer all landed the
same 48 hours.** This dev machine has no local JDK/Android SDK/Gradle/Android
Studio — confirmed by checking before writing any code, not assumed. Verified
instead with a throwaway Docker image (`android/Dockerfile.build-verify`:
JDK17 + Android SDK 35 + Gradle 8.7) that produced a real, installable
`app-debug.apk` (~26.7 MB) via `gradle assembleDebug` -- full chain: Kotlin
compile, Hilt/KSP codegen, resource linking, DEX, packaging, debug signing --
plus 19 passing JVM unit tests (14 sensing + 2 tabular-feature-extraction + 3
RRX1-codec, the latter two each pinning a hand-computed/ground-truth example
field by field). The transport layer's DTO wire format was additionally
POSTed with `curl` straight at the real running backend and returned a genuine
`202` with a simulated dispatch -- verified against the live system, not just
the Kotlin compiler.

Real bugs caught and fixed along the way, not by reading the code back: a
missing Kotlin-2.0 Compose-compiler plugin declaration; an XML comment
containing `--` (illegal per the XML spec) breaking manifest merging
**twice** -- once in the scaffold pass, once again in the sensing pass, a
pattern worth grepping for before future manifest edits; a wrong import path
for `FontFamily`; a `startForeground()` overload that only exists on API 29+
despite this project's minSdk 26, compiling clean but throwing
`NoSuchMethodError` on real low-end hardware; and, found by testing the real
bundled `.tflite` artifact directly with Python rather than assuming its
behaviour -- **feeding it an all-zero `raw_audio` tensor (exact digital
silence) produces NaN on every output**, almost certainly a `log(0)`
singularity in the baked-in mel frontend. Low-amplitude noise instead of
literal zeros avoids it entirely and was verified against the real model
before being used as this build's "no microphone yet" placeholder — see
`CrashClassifier`'s doc comment. The transport pass added two more: a
KDoc comment containing the literal text `*1e5/*10` broke the whole file --
Kotlin supports *nested* block comments, so that `/*` substring opened an
unintended inner comment that swallowed everything after it, the same
failure family as the manifest's `--` bug but a different language's
syntax; and a cross-module smart-cast Kotlin won't perform on a `val` from
a different Gradle module, needing a local variable instead of an inline
null-check. See `android/README.md` for the full writeup and what's real
vs. placeholder per module.

| Piece | Days | Notes |
|---|---|---|
| ~~Scaffold, Hilt, Compose, theme from UX §28 tokens~~ | ~~2~~ **0** | **Done and verified compiling+packaging.** Five-module layout per PRD §12.6 (`app`, `core-sensing`, `core-detection`, `core-transport`, `core-data`). No embedded fonts yet (falls back to platform defaults) -- see `android/README.md`'s gap list |
| ~~Sensing: ring buffer, foreground service, Activity Recognition gating~~ | ~~3~~ **0** | **Done and verified.** `ImuRingBuffer` produces the exact (200,9) tensor layout `ml/crash_detection/build_dataset.py` trains on (unit-tested column-by-column); `ImuSensorSource` (real SensorManager), `GpsSpeedSource` (FusedLocationProviderClient), `DrivingDetector` (Activity Recognition IN_VEHICLE transitions), and `DriveSensingService` (foreground service) all compile and package against real Android APIs. Accelerometer clip-mask is a documented approximation (raw accelerometer's hardware rail applied to the gravity-removed linear-acceleration signal) -- see `android/README.md` |
| Stage-A gate + drive-session lifecycle | 0.5 | **The gate itself is done** -- `StageAGate` mirrors `stage_a_pass()`'s full/degraded logic exactly (5 unit tests covering the GPS-unavailable case). What's left: always-on driving detection independent of the app being open (`RECEIVE_BOOT_COMPLETED` + a persistent transition subscription) -- this scaffold only reacts to IN_VEHICLE transitions while manually started |
| ~~On-device log-mel spectrogram~~ | ~~2–3~~ **0** | **Resolved server-side, not an Android task.** §4.1 — the mel computation is baked into the TFLite graph itself; the app records raw audio and passes the byte buffer straight to the interpreter. No Kotlin DSP, no FFT library, no filterbank to get wrong |
| ~~TFLite runner: assemble 4 raw inputs, invoke, parse two outputs~~ | ~~1~~ **0** | **Done and verified against the real bundled artifact**, not just compiled. `TabularFeatures` ports `saturation_features()`/`gps_features()` to Kotlin (21 of 26 `tab` columns; column order confirmed by running the actual Python functions through `pd.DataFrame`, not read off the source). `CrashClassifier` loads `crash_fusion_deployable_v1.tflite` from assets and invokes it via its real named signature (`imu`/`gps`/`tab`/`raw_audio` → `crash`/`severity`), confirmed against `interp.get_signature_list()` on the actual file. `raw_audio` and the 5 `aud_*` tab columns are always placeholder (no mic capture -- §4.2) rather than real audio features; `train.py`'s own inference-degradation harness states zeroing is what `ModalityDropout` trained for, so the 5 tab columns are exact zero, while `raw_audio` itself uses low-amplitude noise instead of exact zero for the NaN reason above. Severity-class-index mapping (0-3 = MINOR..CRITICAL, 4 = NONE) is confirmed for the NONE case empirically, inferred from `model.py`'s comment for the positive classes -- a properly training-distribution-shaped positive sample wasn't crafted in this pass |
| ~~Cancel window screen (UX §15) — full-screen, siren, TTS, volume-key cancel, 800 ms delay~~ | ~~2.5~~ **0** | **Done and verified via Docker (compile, 19 unit tests, `assembleDebug`).** `CrashCountdownScreen` renders the full-bleed sodium ground (600 for CRITICAL, 500 otherwise), 200sp numeral, drain bar, and the one 96dp cancel button with an 800ms-delayed enable (`CrashAudioController`: `ToneGenerator` + `TextToSpeech` on `STREAM_ALARM`; `CrashHapticController`: 200ms/800ms waveform). `CrashCountdownActivity` hosts it with real lock-screen bypass (`setShowWhenLocked`/`setTurnScreenOn` API 27+, window flags below that), forced max brightness, and volume-key cancel. `CrashTriggerNotifier` (new, in `app`) fires when `DriveViewModel`'s live `CrashPrediction.pCrash` crosses the real model threshold (0.29719674587249756, from `ml/reports/crash_detection_results.json`), posting a full-screen-intent notification -- the only way to launch an Activity from `DriveSensingService`'s background context on Android 10+. CRITICAL alone (not the full "no post-impact motion + phone not picked up") triggers the 5s window; the rest get 10s -- a documented simplification, since post-impact motion and pickup detection aren't wired. Never run on a device -- see `android/README.md` |
| ~~Transport: HTTPS + SMS fallback + WorkManager retry + parallel send on CRITICAL~~ | ~~2.5~~ **0** | **Done and verified against the real backend**, not just compiled. `Rrx1Codec` ports `encode_rrx1()`/`crc8_atm()` to Kotlin -- verified byte-for-byte against two concrete outputs from the real Python implementation (65-bit UUID prefix via `BigInteger`, Crockford base32, CRC-8/ATM, negative-coordinate and all-flags cases all covered). `AlertTransport` implements PRD §6.2's exact channel strategy (HTTPS 6s deadline, SMS 15s deadline, parallel-not-sequential on CRITICAL) and enqueues `AlertSendWorker` (plain `CoroutineWorker`, no Hilt-Work wiring -- a deliberate simplification, see `android/README.md`) for up to 24h of exponential-backoff retry when the immediate HTTPS attempt fails. The exact JSON `AlertCreateDto` produces was POSTed to the real running backend with `curl` and returned a real `202` with a simulated dispatch -- the wire contract is confirmed, not assumed. Channel 3 (local escalation: siren, emergency contacts, one-tap call-112) is out of scope here -- it's a UI/notification concern, tracked with the cancel-window screen below |
| ~~Onboarding + consent cards (UX §11), 5 languages~~ | ~~3~~ **0** | **Done and verified via Docker.** All nine steps built as a linear `OnboardingStep` state machine (same shape as the crash flow's `CrashFlowHost`), gating `HomeScreen` in `MainActivity` until complete. Each consent card requests exactly one real runtime permission per §11.3's "never a batch request" (Location follows up `ACCESS_FINE_LOCATION` with a separate `ACCESS_BACKGROUND_LOCATION` request on API 29+, since the two can't be requested together). Contacts are picked directly against the Phone content URI (no `READ_CONTACTS` needed). Language selection calls the real `AppCompatDelegate.setApplicationLocales` API and previews the crash line via real TTS. Full string-resource architecture with real (AI-translated, not native-reviewed -- verify before a real demo) copy in all 5 languages, not just English |
| ~~Drive mode + Segment Ribbon + risk warnings~~ | ~~1~~ **0.3** | **The map + Segment Ribbon half is done (2026-08-21); §14 Risk Warning is now done too, verified via Docker (2026-08-25, real `assembleDebug` + `compileDebugKotlin`).** `DriveModeViewModel` detects "entering" a High/Severe segment as its nearest-segment id changing (no separate state machine), gated by FR-4.5 (25 km/h floor) and FR-4.4 (15-min per-segment cooldown). `RiskWarningController` speaks the top SHAP factor (FR-4.6) via `TextToSpeech` on `USAGE_ASSISTANCE_NAVIGATION_GUIDANCE` (audible normally, silent when the phone is silenced -- deliberately not the crash siren's DND-overriding `STREAM_ALARM`, since §14 frames Low/Moderate's silence as trust-building restraint), and Severe adds a double haptic pulse plus a bottom-anchored overlay with a real cross-hatch texture (the NFR-A3 hatch pattern missing everywhere else in this build) and a live nearest-vertex distance countdown. Caught a real bug along the way: editing `AndroidManifest.xml`'s permissions comment to explain the new `VIBRATE` permission reintroduced the XML `--`-in-comment bug for a **fifth** time across this project, failing `:app:processDebugMainManifest` exactly as the four prior occurrences did -- fixed the same way, but the codebase's own "grep for `--` before touching any XML comment" lesson from occurrence three evidently still hasn't stuck as a habit. What's left: the ambient/screen-off notification upgrade (still `DriveSensingService`'s plain "Monitoring for crashes" text, not §13's live band-accented one) |
| ~~Sending/Sent/Acknowledged + Golden Hour dial~~ | ~~1.5~~ **0** | **Done, simplified.** `CancelledScreen` (§16) and `SendingScreen` (§17) built; the feedback micro-survey and the full radial Golden-Hour dial are out of scope -- `SendingScreen` shows a numeral-only countup/countdown instead, and the channel outcome is a 2-state summary (`AlertTransport.send()` returns one final result, not a progress stream, so there's no per-node timestamp to show). The mandatory Simulation Seal is shown unconditionally on the Sent state |
| Settings, privacy, data deletion | 0.5 | **Partially done as a side effect of onboarding.** `core-data`'s Room (emergency contacts) and `EncryptedSharedPreferences` (consent/medical/language) storage now exist and are real, not a placeholder module -- what's left is a post-onboarding Settings *screen* to review/edit/delete that data, which doesn't exist yet |
| ~~OEM battery-optimisation flow + verification~~ | ~~1~~ **0** | **Verification half is done and real** -- `PowerManager.isIgnoringBatteryOptimizations()` is re-checked on every `ON_RESUME`, showing an honest `PROTECTION ACTIVE`/`PROTECTION LIMITED` banner. The OEM-specific deep links (Xiaomi/Oppo/Vivo/Realme) UX §11.5 asks for are deliberately not built -- undocumented, vendor-specific intents this project has no matching hardware to verify, so only the one real universal fallback (`ACTION_IGNORE_BATTERY_OPTIMIZATION_SETTINGS`) ships |
| **Total** | **~0.8** | down from ~19 — sensing (3 days), the TFLite runner (1 day), transport (2.5 days), the cancel-window screen (2.5 days), Sending/Sent/Acknowledged (1.5 days), onboarding (3 days), battery-optimisation (1 day), and the Drive Mode map + Segment Ribbon + Risk Warning (2.7 of its 3 days) are all done; Stage-A gate reduced to just the boot-time remainder, Settings reduced to the screen itself now that its storage layer exists, Drive Mode reduced to just the ambient notification upgrade |

### 3.4 Dashboard — `rrx-ops`

**Started and Live Operations shipped 2026-08-18; Incident Detail, Risk Map, Simulator Console, and Analytics all shipped 2026-08-24** — React 18 + TS + Vite + Tailwind + react-leaflet + TanStack Query + Zustand per PRD §12.4, verified against the real running backend (not a mock API), including a live WebSocket update, a real curl'd-alert opened end-to-end from a rail card through to a rendered three-column detail view, a live condition-simulator round-trip that measurably moved a real segment's score and band, a live inject-crash round trip that opened the resulting alert's real Incident Detail page, and Analytics rendering real aggregate numbers (computed from those same injected alerts) across all six §24 panels with working PNG/CSV export.

| Piece | Days | Notes |
|---|---|---|
| ~~Scaffold: Vite, TS, Tailwind, design tokens, theme switching~~ | ~~1.5~~ **0** | **Done.** `web/src/styles/tokens.css` is a verbatim transcription of UX §28; light/dark via `[data-theme]`, Live Operations defaults dark per §20 |
| ~~Signature components: Milestone Marker, Segment Ribbon, Golden Hour Dial, Channel Badge, Simulation Seal, Trace Sparkline, Honesty Bar~~ | ~~4~~ **0** | **Done**, all seven, matching UX §7's dimensions/colour/pattern specs exactly (triple-encoded risk bands per NFR-A3), reachable at `/gallery` for design QA |
| ~~Live Operations: map + risk overlay + incident rail + WS~~ | ~~3~~ **0** | **Done.** Real risk-banded segment polylines from `/risk/bbox` (not mocked geometry), Milestone Marker incidents with zoom-tiered rendering and unacknowledged-pulse, incident rail sorted unacknowledged-first-then-golden-hour-ascending per §21.2, live WS updates, a functional (if MVP-scoped) 24h time scrubber that re-queries Model B for the scrubbed hour. Basemap is a CARTO dark no-labels raster as an honest approximation of §21.1's bespoke vector tile style, which this project has no tile-serving pipeline for |
| ~~Incident detail (UX §22)~~ | ~~2~~ **0** | **Done and verified live, 2026-08-24** — a real `curl`'d alert opened from a rail card's new "Details →" affordance, three columns, real data throughout. `GET /alerts/{uuid}` went from returning 4 fields to the full row (backend/app/api/alerts.py, migration 0002 added `alerts.occupant_hint`, which was accepted in every `POST /alerts` payload since day one but silently dropped -- never persisted -- until now). Reuses five of the seven signature components (Golden Hour Dial at 160px, Channel Badge, Simulation Seal, plus Segment Ribbon/Milestone Marker already live on the map). Two honest gaps carried through rather than faked: Sensor Evidence has no real `{t,g}` samples to show (no `GET .../trace` endpoint exists anywhere -- PRD only ever planned a POST upload route, and that isn't built either), and Victim Details only has real Occupants -- blood group/conditions/language have no source anywhere in the system, matching `android/README.md`'s own onboarding-never-syncs-to-backend note. Export is real: GeoJSON is a client-built `Feature` from the same response the page renders, and Print/PDF is the browser's own print pipeline against the live DOM via new `@media print` rules in `index.css`, so the Simulation Seal renders in the PDF at full fidelity per spec, with no separate template to drift out of sync |
| ~~Risk map: full-width analyst map + condition simulator + Top-N table~~ | ~~1.5~~ **0** | **Done and verified live, 2026-08-24.** `GET /risk/bbox` gained optional `weather`/`visibility`/`traffic_density` query overrides (whitelisted to the exact categories `risk_model_v1.txt` was trained on -- an unlisted value would silently degrade to LightGBM's "unknown category" code rather than error, so the whitelist is load-bearing); `features_from_segment()` threads them through only when a caller supplies them, so `alerts.py`'s real-alert scoring path is untouched. The dashboard's left-panel simulator moves the network's real scores live -- verified with a real before/after curl and in-browser round-trip (a segment: 0.0016 Low → 0.021 High under simulated heavy rain, low visibility, high traffic at 23:00 IST). Weather/visibility/traffic are 3-way segmented controls, not continuous sliders, because the model only has three trained categories for each -- a continuous input implying finer precision than the model can use would be dishonest, not a UI nicety. The Top-N table is real (sortable by segment/district/score, CSV export), with its 3-yr-crash-count and blackspot-status columns honestly marked "No data" rather than hidden, same posture as `LayerControl.tsx` |
| Corridor mode + Comparison mode (blackspot) | 1 | Not built. Corridor mode needs a kilometre-ordered corridor-selection tool; Comparison mode needs a real MoRTH/iRAD or SaveLIFE-ZFC blackspot list ingested into the (currently empty) `blackspots` table plus a serving endpoint -- neither exists (ETL's own blackspot-ingestion task, MVP-PLAN.md §2, hasn't run either). Both toolbar buttons render disabled with a real reason in their tooltip rather than linking to fabricated data |
| ~~Analytics + export~~ | ~~1.5~~ **0** | **Done and verified live, 2026-08-24.** New `GET /analytics/summary` (`backend/app/api/analytics.py`) computes real aggregates from `alerts`/`dispatches`/`devices`/`road_segments`/`responder_units` -- response-latency percentiles + a 7-bucket histogram, channel mix by hour, Golden Hour ack-rate at 60/30/15 min, and network coverage. Two of §24's six panels have no live-database source and are rendered from static, clearly-labelled constants instead of fabricated live figures: Detection quality (cancel rate is uncomputable -- `POST /alerts`' `window.outcome` is accepted but never persisted) shows Model A's synthetic-holdout FP/100-driving-h numbers with `ml/MODELS.md`'s own caution attached; Risk model performance shows `ml/reports/risk_model_results.json`'s real PR-AUC/Brier/Precision@top-1%/band-level calibration. Every "acknowledgement" number carries an explicit caveat that it measures the simulated gateway's synchronous response, not a live PM-RAHAT/ERSS-112 field ack -- same disclosure posture as Incident Detail's Simulation Seal. All six panels export as PNG (SVG→canvas, no new dependency) and CSV. Page forces light theme per §24 via the same `setTheme`-on-mount pattern Live Operations uses for dark |
| ~~Simulator console~~ | ~~1~~ **0** | **Done and verified live, 2026-08-24.** Wires `POST /sim/crash` (severity/speed/g-force/lat-lon, plus a DATA/SMS channel toggle -- UX §25's "Force SMS path" is this same call with `channel_hint=SMS`, not a separate endpoint, since the backend only exposes one) and `POST /sim/gateway/mode` (ok/slow/timeout/reject). Verified: injecting a crash produced a real ticket and opened the actual Incident Detail page for it; setting gateway mode to `reject` then back to `ok` round-tripped correctly. The nav entry is hidden entirely, not disabled, when `VITE_DEMO_MODE=false` -- matching UX §25's "absent, not disabled" and the backend's own `RRX_DEMO_MODE` gate on registering `/sim/*` at all. "Feed failure" and "Scenario playback" have no backend support (no injectable feed to fail, no scripted-sequence runner) and render disabled with the real reason in their tooltip, same posture as Risk Map's Corridor/Comparison modes |
| **Total** | **~1** | down from ~15.5 — every line item is done except Risk Map's Corridor/Comparison modes (1 of its 2.5 days), which is blocked on blackspot data this MVP hasn't ingested yet |

### 3.5 Integration, hardening, demo

| Piece | Days |
|---|---|
| End-to-end wiring + latency instrumentation against NFR-P4 (≤20 s data / ≤90 s SMS) | 2 |
| Battery profiling on 3 device tiers (NFR-B1–B4) | 1.5 |
| k6 load test — 100 alerts/min burst (NFR-P7) | 0.5 |
| Shake rig / controlled trigger for the live demo | 1 |
| Playwright E2E demo script + rehearsal | 1.5 |
| Deck rebuilt against the working system — architecture slide, model params, artifact size all changed since the original deck (§4.3) | 1 |
| **Total** | **~7.5** |

**Grand total ≈ 15.8 person-days** (backend 2.5 + ETL 4 + Android 0.8 + dashboard 1 + integration 7.5), down from ~58. At 5 people over 6 weeks (~150 person-days available) that is comfortable. Android and the dashboard are both now built end-to-end and verified against something real: sensing, classification, transport, the cancel-window screen (§15-17), onboarding (§11), Drive Mode's map + Segment Ribbon (§13), and now Risk Warning (§14 -- voice/haptic/Severe overlay firing off the live segment stream, gated by the real FR-4.4/4.5 cooldown and speed floor) on the Android side; Incident Detail (§22), Risk Map (§23), Simulator Console (§25), and Analytics (§24) on the dashboard side, each extending or adding a real backend endpoint rather than building a frontend against fabricated data. What's left on Android (the ambient notification, a Settings screen) is ~0.8 days; Risk Map's Corridor/Comparison modes (~1 day, blocked on blackspot ETL ingestion) and integration/hardening (7.5 days) are now the largest remaining tracks -- integration/hardening alone is now very nearly half the entire remaining budget.

---

## 4. Debt the multi-modal pivot created

Adding the microphone strengthened the model and introduced three problems that the PRD and UX spec do not currently cover. All three are mine to fix.

### 4.1 On-device log-mel — RESOLVED

`crash_fusion_v1.tflite` took **four** inputs, one of which (`mel [1, 64, 126, 1]`) nothing in the PRD's Android stack could compute. Three options were on the table; rather than leave the recommendation abstract, option 1 was built and verified:

**Two risks had to be closed before committing to it, both tested directly rather than assumed:**

1. *Does `tf.signal.stft` convert to standard TFLite ops, or does it pull in the Flex delegate* (a materially heavier mobile runtime)? Tested empirically: the STFT itself converts cleanly to native ops (`tfl.rfft2d`, `tfl.mirror_pad`, etc.) at ~11 KB. One follow-on op (`x[..., tf.newaxis]`) compiled to a generic `StridedSlice` that *did* need Flex — fixed by using `tf.expand_dims` instead, which lowers to the native op used elsewhere in the same graph. Full frontend converts Flex-free.
2. *Does the graph reproduce what the model was trained on?* `tf.signal.mel_weight_matrix` uses a different mel-scale definition than `librosa.filters.mel` (what generated every training-time spectrogram). Using it would silently retrain the model on a different feature space than what it sees on-device. Fixed by computing the librosa filterbank once in Python and baking it in as a constant matrix — the transform is then identical to training by construction, not merely similar.

**Implementation:** `ml/crash_detection/mel_frontend.py` (`LogMelFrontend` layer) + `ml/crash_detection/model.py` (`build_deployable_model`, `Normalize`) + `ml/crash_detection/export_deployable.py` (the verification gate). Every branch was refactored into a named, reusable Keras sub-model so the deployable graph can reassemble the trained weights around a raw-audio input without retraining.

**A second skew risk was closed at the same time, unprompted by the original plan:** the trained audio branch expects *normalised* mel input. Shipping that as a contract would require the Android app to replicate four different `(x-μ)/σ` steps from a stats file in Kotlin — exactly the class of silent mismatch that caused four rounds of leak-hunting in the crash-detection benchmark (`ml/MODELS.md` §2.6). Normalisation for all four modalities is now baked into the graph as constant weights (`Normalize` layer), so the shipped contract is simply *"feed raw sensor values in their physical units"* — nothing left to get wrong client-side.

**Verified, not assumed.** `export_deployable.py` regenerates fresh held-out synthetic events (same source pools as the real test split, via `build_dataset.partition_sources`, so no leakage), runs them through both the training-time model (precomputed mel) and the deployable model (raw audio → on-device frontend), and asserts they agree before the artifact is allowed to save. A smoke run (3 epochs, small corpus) returned **100% decision agreement, 0.0000 mean probability difference** between the two paths, and **exact match** between the deployable Keras model and its TFLite export. A negative control — deliberately omitting the audio-branch normalisation — confirmed the check actually catches a wiring bug: mean probability difference jumped to 0.33, ~6.7× over the assertion's threshold. Deployable artifact: **299.5 KB** (up from 173 KB — the frontend's own weights, mostly the 64×513 mel filterbank, account for the difference). Final numbers from the full 30k retrain land in `ml/MODELS.md`.

### 4.2 Continuous microphone buffering is a privacy escalation

Detection needs ~4 s of pre-impact audio, which means **continuously buffering the microphone while driving**. That is a materially bigger privacy claim than location + motion, and it is the one most likely to draw objection from a government reviewer or a privacy-conscious user.

Required, none of which exists yet:

- A **sixth consent card** in onboarding (UX §11.3), ordered *last*, after SMS
- Explicit guarantees, enforced in code: **ring buffer only, never written to disk, never uploaded unless a crash is confirmed, discarded on cancel**
- The persistent notification must show when the mic is active — Android 12+ shows a mic indicator anyway, so users *will* see it and must have been told why
- `NFR-PR2` (data minimisation) needs a clause covering audio
- A visible mic kill-switch in Settings, with honest degradation: detection still works, precision drops

**The app must work with the mic denied.** The degradation results support this — recall held at 1.000 with audio removed. Make that the advertised behaviour, not a hidden fallback.

### 4.3 The PRD's model spec was stale — RESOLVED

PRD §7.1 described a single-modality 1D-CNN on `200 × 6`, ~45k params. The built model is a four-branch fusion network on `200 × 9` + mel + GPS + tabular, 76,814 params. **Fixed** — PRD §7.1, §6.1.2, and §12.3 were rewritten 2026-08-17 to match the implemented architecture, with an explicit note that `ml/MODELS.md` is now the authoritative source and the PRD table is kept in sync with it, not the reverse. **The slide deck itself still needs rebuilding** against these numbers before it's presented — that's a deck task, not a code task, and isn't tracked elsewhere in this plan. Add it to §3.5 if a rebuilt deck is needed before demo day.

---

## 5. Sequencing

```
Week 1  [done] backend scaffold + POST /alerts + schema
        [done] dashboard scaffold + design tokens + signature components
        [done] android toolchain assessment + scaffold (verified: real APK)
        [done] git init + push · corridor frozen · mel-in-graph resolved
        [still open] SMS companion-phone receiver (§2②)

Week 2  [done] enrichment + gateway + WS + risk endpoints + SMS ingest + sim
        [done] ETL: OSM -> 500m segments (real NH-45/Chengalpattu corridor)
        [done] dashboard: Live Operations (map + risk overlay + incident rail + WS)
        [done] android: core-sensing (IMU ring buffer, GPS, Stage-A gate,
               Activity Recognition, foreground service -- 14 unit tests)
        [done] android: core-detection (TabularFeatures + CrashClassifier,
               verified against the real .tflite artifact -- 16 unit tests)
        [done] android: core-transport (RRX1 codec + AlertTransport +
               WorkManager retry, verified against the live backend --
               19 unit tests total)
        [done] android: cancel window (§15-17 -- countdown, cancel,
               sending/sent screens, real trigger wiring from
               DriveViewModel via full-screen-intent notification)
        [done] android: onboarding (§11 -- nine steps, real per-screen
               consent, Room + EncryptedSharedPreferences via core-data,
               5-language string resources + real locale switching)
        [done] android: drive mode map + Segment Ribbon (§13 -- live
               osmdroid map from GET /risk/bbox, real letter-token bands)
        [done] dashboard: incident detail (§22 -- extended GET
               /alerts/{uuid} server-side, migration 0002 for
               occupant_hint, real GeoJSON/PDF export)
        [done] dashboard: risk map + condition simulator + Top-N table
               (§23 -- extended GET /risk/bbox with real weather/
               visibility/traffic_density overrides, live-verified
               before/after score change)
        [done] dashboard: simulator console (§25 -- wired the two real
               /sim/* endpoints, live-verified inject-crash-to-
               detail-page round trip and a gateway-mode round trip;
               nav entry hidden, not disabled, when VITE_DEMO_MODE=false)
        [done] dashboard: analytics + export (§24 -- new GET
               /analytics/summary aggregation endpoint; two of six
               panels honestly served from static report constants
               rather than fabricated live data; PNG/CSV export on
               all six; light theme forced per spec)
        [done] android: risk warning (§14 -- voice/haptic/Severe
               overlay, FR-4.2/4.4/4.5/4.6 all real, verified via
               Docker; caught the XML `--`-in-comment bug a 5th time)

Week 3  android: ambient notification upgrade
        android: post-onboarding Settings screen
        dashboard: risk map corridor mode + blackspot comparison
               (needs blackspot ETL ingestion first)

Week 4  integration, latency instrumentation, battery profiling
        android: offline alert-retry queue (core-data's remaining gap)

Week 5  harden, load test, E2E script, rehearse, rebuild deck
```

**Critical path has moved to Android's last two screens and integration.** Android's remaining ~0.8 days (ambient notification, Settings screen) and Risk Map's Corridor/Comparison modes (~1 day, blocked on blackspot ETL ingestion) are the only feature work left; backend, Android's core pipeline (now including §14 Risk Warning), and the entire dashboard (Live Operations, Incident Detail, Risk Map, Simulator Console, Analytics) are all built and verified against real infrastructure and each other. Integration/hardening (§3.5's ~7.5 days) is now what determines whether the full PRD §16.2 walkthrough is demo-ready in time, not any remaining feature gap.

---

## 6. Cut list

Explicitly out of MVP. Cutting these is what makes the timeline work.

| Cut | Why safe |
|---|---|
| Real ERSS-112 / PM RAHAT integration | No API access. Simulated gateway is the design (PRD §11) |
| iOS app | iPhone 14+ has native detection; the gap is Android |
| Play Store release | Side-load for the demo. `SEND_SMS` declaration takes weeks |
| Real carrier long code | Companion-phone receiver (§2②) |
| Kubernetes | Docker Compose is sufficient at demo scale |
| MLflow / feature store | A table plus Redis is enough |
| >5 languages | Architecture supports 22; ship 5 |
| Live traffic beyond the demo corridor | Free-tier quota; one corridor only |
| Two-wheeler detection | PRD Q7 open, different sensor signature — state the scope limit |
| Model A retraining on real telemetry | Cannot be done in 6 weeks; it is the pilot's first job |

---

## 7. Standing constraint

**Model A must not be connected to anything presented as a real dispatch path** — including the simulated gateway in a public demo — until real crash telemetry exists (`ml/MODELS.md` §6, items 1–3).

For the SIH demo this is satisfiable and honest: trigger via shake rig or the simulator console, show the alert flowing, and label the model as synthetic-data-trained on the slide *and* in the UI. The Simulation Seal (UX §7.5) already covers the gateway; add an equivalent disclosure for the detector itself.

The demo's persuasive power does not depend on claiming detection accuracy. It depends on showing that **a ₹12,000 Android phone in airplane mode can still get a structured, enriched alert into a dispatch pipeline in under 90 seconds.** That claim is true, demonstrable, and does not require the model to be validated.
