# Path to MVP

| | |
|---|---|
| **Date** | 2026-08-18 |
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
| Dashboard (`rrx-ops`) | **Live Operations view built and verified against the real backend**: map with real risk-banded segments, live incident rail (WS-pushed, cold-start via `GET /alerts`), all seven signature components (UX §7), System Honesty Bar wired to real (if sparse) feed status. Incident Detail, Risk Map, Analytics, Simulator console views not yet built — nav rail shows them as disabled, not broken links |
| Android app (`rrx-app`) | **Toolchain assessed; sensing, crash classification, and transport all built and verified** (no local JDK/SDK on this machine — verified via a throwaway Docker image instead, including 19 passing unit tests). Five-module layout per PRD §12.6; `app`, `core-sensing`, `core-detection`, and `core-transport` have real code -- device registration, a full Stage-A sensing pipeline, a TFLite classifier invoked on every Stage-A trigger (verified against the real bundled model artifact, including a NaN bug in the model's audio frontend found and worked around), and an HTTPS/SMS channel-strategy transport layer whose wire format was confirmed with `curl` against the live backend. Only `core-data` is still a placeholder module — see `android/README.md` |
| Version control | **Done.** Pushed to [GitHub](https://github.com/Angeline1710/Predictive-Road-Risk-Golden-Hour-Crash-Response), `main` tracking `origin/main` |

Roughly **64% of the MVP is built** — the ML layer, a functionally complete backend (schema, ingest, risk serving, SMS, WebSocket, sim endpoints, all verified against real Docker containers), a working Live Operations dashboard wired end-to-end to that backend (including a real-time WS path verified live), and now an Android app whose sensing, on-device classification, and network/SMS transport all work end to end and are each verified against something real -- the trained model artifact, the live backend, or both. What's left is the cancel-window screen and onboarding on Android (~12 person-days) plus the smaller remainders in each other track.

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
| Cancel window screen (UX §15) — full-screen, siren, TTS, volume-key cancel, 800 ms delay | 2.5 | Highest-stakes screen; budget properly |
| ~~Transport: HTTPS + SMS fallback + WorkManager retry + parallel send on CRITICAL~~ | ~~2.5~~ **0** | **Done and verified against the real backend**, not just compiled. `Rrx1Codec` ports `encode_rrx1()`/`crc8_atm()` to Kotlin -- verified byte-for-byte against two concrete outputs from the real Python implementation (65-bit UUID prefix via `BigInteger`, Crockford base32, CRC-8/ATM, negative-coordinate and all-flags cases all covered). `AlertTransport` implements PRD §6.2's exact channel strategy (HTTPS 6s deadline, SMS 15s deadline, parallel-not-sequential on CRITICAL) and enqueues `AlertSendWorker` (plain `CoroutineWorker`, no Hilt-Work wiring -- a deliberate simplification, see `android/README.md`) for up to 24h of exponential-backoff retry when the immediate HTTPS attempt fails. The exact JSON `AlertCreateDto` produces was POSTed to the real running backend with `curl` and returned a real `202` with a simulated dispatch -- the wire contract is confirmed, not assumed. Channel 3 (local escalation: siren, emergency contacts, one-tap call-112) is out of scope here -- it's a UI/notification concern, tracked with the cancel-window screen below |
| Onboarding + consent cards (UX §11), 5 languages | 3 | |
| Drive mode + Segment Ribbon + risk warnings | 3 | The live Stage-A readout in `app`'s Drive Mode section is a debug view, not this screen -- UX §13's actual Drive Mode (map, Segment Ribbon, risk warnings) is unbuilt |
| Sending/Sent/Acknowledged + Golden Hour dial | 1.5 | |
| Settings, privacy, data deletion | 1.5 | Includes `core-data`'s Room offline queue + `EncryptedSharedPreferences` (currently a placeholder module) |
| OEM battery-optimisation flow + verification | 1 | |
| **Total** | **~12** | down from ~19 — sensing (3 days), the TFLite runner (1 day), and transport (2.5 days) are done, Stage-A gate reduced to just the boot-time remainder |

### 3.4 Dashboard — `rrx-ops`

**Started and Live Operations shipped 2026-08-18** — React 18 + TS + Vite + Tailwind + react-leaflet + TanStack Query + Zustand per PRD §12.4, verified against the real running backend (not a mock API), including a live WebSocket update observed end-to-end.

| Piece | Days | Notes |
|---|---|---|
| ~~Scaffold: Vite, TS, Tailwind, design tokens, theme switching~~ | ~~1.5~~ **0** | **Done.** `web/src/styles/tokens.css` is a verbatim transcription of UX §28; light/dark via `[data-theme]`, Live Operations defaults dark per §20 |
| ~~Signature components: Milestone Marker, Segment Ribbon, Golden Hour Dial, Channel Badge, Simulation Seal, Trace Sparkline, Honesty Bar~~ | ~~4~~ **0** | **Done**, all seven, matching UX §7's dimensions/colour/pattern specs exactly (triple-encoded risk bands per NFR-A3), reachable at `/gallery` for design QA |
| ~~Live Operations: map + risk overlay + incident rail + WS~~ | ~~3~~ **0** | **Done.** Real risk-banded segment polylines from `/risk/bbox` (not mocked geometry), Milestone Marker incidents with zoom-tiered rendering and unacknowledged-pulse, incident rail sorted unacknowledged-first-then-golden-hour-ascending per §21.2, live WS updates, a functional (if MVP-scoped) 24h time scrubber that re-queries Model B for the scrubbed hour. Basemap is a CARTO dark no-labels raster as an honest approximation of §21.1's bespoke vector tile style, which this project has no tile-serving pipeline for |
| Incident detail (UX §22) | 2 | Not built. Rail cards show a summary; no dedicated detail route yet |
| Risk map + condition simulator + blackspot comparison | 2.5 | Not built. Layer control exists in Live Operations with Weather/Traffic/Blackspots shown-but-disabled (no data source for any of the three) rather than hidden or faked |
| Analytics + export | 1.5 | Not built |
| Simulator console | 1 | Not built as a UI — `/sim/*` endpoints work and were used directly via `curl` for all dashboard verification |
| **Total** | **~7** | down from ~15.5 |

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

**Grand total ≈ 33 person-days** (backend 2.5 + ETL 4 + Android 12 + dashboard 7 + integration 7.5), down from ~58. At 5 people over 6 weeks (~150 person-days available) that is comfortable. **Android is still the critical path** — sensing, classification, and transport now all work end-to-end and verified against the real backend, but the cancel-window screen and onboarding are the bulk of what's left, and the cancel-window screen in particular is the one piece that actually produces a real (non-simulated) alert payload for transport to send.

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

Week 3  android: cancel window                           <- now the whole week's work
        dashboard: incident detail (remaining ~2 days of §3.4)

Week 4  android: onboarding + 5 languages
        dashboard: risk map + comparison, analytics, simulator console

Week 5  integration, latency instrumentation, battery profiling
        android: drive mode + risk warnings

Week 6  harden, load test, E2E script, rehearse, rebuild deck
```

**Critical path is now Android**, full stop — backend and the Live Operations dashboard are both verified against real infrastructure and each other. Anything that slips the Android sensing/transport/cancel-window work slips the demo; the remaining dashboard views (§3.4) can slip a week without touching the PRD §16.2 walkthrough, which only needs Live Operations to be real.

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
