# `rrx-app` — Android scaffold

## Toolchain assessment (task #18, 2026-08-18)

This dev machine has **no local JDK, no Android SDK, no Gradle, and no
Android Studio** — confirmed by checking `java`, `gradle`, `$ANDROID_HOME`,
and the usual install paths before writing any Kotlin. Docker is
available and already used throughout this project (backend, ETL), so
`Dockerfile.build-verify` builds a throwaway JDK17 + Android SDK 35 +
Gradle 8.7 image to prove this scaffold actually compiles, rather than
shipping code that only "looks right" on read-through. It is not part of
the shipped app — delete it once a real Android Studio install exists.

**What that verification did and didn't check:** it proves the Gradle
project resolves, the five modules compile, resources process, and the
DTOs/Retrofit interface satisfy the compiler. It does **not** prove the
app runs — there's no emulator or device here, so `HomeScreen`'s call to
`POST /v1/devices/register` has never actually executed against the
backend from a device. Do that first thing once real hardware/emulator is
available: run the backend (`docker compose up` in `backend/`), install
this app on an emulator with `10.0.2.2` reachable (or a physical device on
the same network, with `NetworkModule.BASE_URL` changed to the host's LAN
IP — same pattern MVP-PLAN.md §2② uses for the SMS companion phone), and
tap "Register device."

## What's real vs. scaffold-only

| Module | State |
|---|---|
| `app` | Real: Hilt DI, Compose + Material3 theme transcribed from UX-APPFLOW.md §28/§6, Retrofit client, device registration against the live backend, and a Drive Mode section (permission requests, start/stop, live Stage-A + classification readout) |
| `core-sensing` | **Real**, 2026-08-18: `ImuRingBuffer` + `StageAGate` (mirrors `ml/crash_detection/build_dataset.py`'s `stage_a_pass()` full/degraded logic exactly, 14 unit tests), `ImuSensorSource` (real SensorManager, TYPE_LINEAR_ACCELERATION + TYPE_GYROSCOPE), `GpsSpeedSource` (FusedLocationProviderClient), `DrivingDetector` (Activity Recognition IN_VEHICLE transitions), `DriveSensingService` (foreground service tying it together, publishing raw IMU/GPS window snapshots for core-detection to consume) |
| `core-detection` | **Real**, 2026-08-19: `TabularFeatures` ports `saturation_features()`/`gps_features()` to Kotlin (2 unit tests, one pinning a hand-computed 26-value example field by field). `CrashClassifier` loads the bundled `crash_fusion_deployable_v1.tflite` and runs it via its real named signature. `app`'s `DriveViewModel` wires the two together: on the rising edge of Stage-A's degraded arm, extracts features and classifies, off the main thread, guarded against concurrent invocation into the same (not thread-safe) `Interpreter` |
| `core-transport` | **Real**, 2026-08-19: `Rrx1Codec` ports `encode_rrx1()`/`crc8_atm()` to Kotlin, verified byte-for-byte against two concrete outputs from the real Python implementation (3 unit tests). `AlertApi`/DTOs mirror `AlertCreate` field-for-field -- the exact JSON they produce was POSTed with `curl` straight at the live backend and returned a real `202`. `AlertTransport` implements PRD §6.2's channel strategy (HTTPS 6s deadline, SMS 15s deadline, parallel-not-sequential on CRITICAL); `AlertSendWorker` is a plain `CoroutineWorker` (no Hilt-Work) retrying up to 24h on failure. `app`'s `TransportSection` exercises the whole path with an `is_simulated = true` test payload, the same "one real screen proves the contract" pattern as device registration |
| `core-data` | Placeholder only. Room offline queue, EncryptedSharedPreferences token/medical storage: not built |

`app`'s crash flow (§15-17), **real, 2026-08-19**: `CrashCountdownScreen`
renders the full-bleed sodium ground, 200sp countdown numeral, drain bar,
and the one delayed-enable cancel button; `CrashAudioController` (siren
tone + TTS on `STREAM_ALARM`) and `CrashHapticController` (200ms/800ms
waveform) run alongside it. `CrashCountdownActivity` hosts the whole
`CrashFlowState` state machine (Countdown -> Cancelled | Sending -> Sent),
with real lock-screen bypass, forced max brightness, and volume-key
cancel. `CrashTriggerNotifier` (new) is what actually starts it: when
`DriveViewModel`'s live `CrashPrediction.pCrash` crosses the model's own
threshold (`0.29719674587249756`, from
`ml/reports/crash_detection_results.json`), it posts a full-screen-intent
notification -- the sanctioned way to launch an Activity from
`DriveSensingService`'s background/foreground-service context, since
Android 10+ blocks `startActivity()` from there outright. On expiry (not
cancelled), `CrashCountdownViewModel` builds a real `AlertCreateDto`
(`isSimulated = false`) from the params captured at trigger time and
calls the real `AlertTransport.send()` -- this is the one path in the
app that produces a non-simulated alert.

Still missing: onboarding, drive-mode UI beyond the raw sensor/
classification readout, always-on driving detection, and `core-data`.
See MVP-PLAN.md §3.3 for what's left and its cost.

### Sensing scope notes (real limitations, not oversights)

- **Accelerometer clip-mask is an approximation.** `ImuSensorSource` reads
  TYPE_LINEAR_ACCELERATION (gravity removed, matching training data) but
  derives the clip-mask rail from the *raw* TYPE_ACCELEROMETER sensor's
  `getMaximumRange()`, since that's the sensor that genuinely saturates in
  hardware. `ml/crash_detection/sensors.py`'s synthetic model clips
  gravity-removed acceleration directly. These aren't the same signal;
  replicating Android's own gravity-removal fusion algorithm exactly is
  out of scope here.
- **No always-on driving detection.** `DrivingDetector` only reacts to
  IN_VEHICLE transitions while `DriveSensingService` is already running
  (manually started from the UI in this scaffold), auto-stopping on EXIT.
  True hands-off "phone detects driving and starts sensing with the app
  not even open" needs a `RECEIVE_BOOT_COMPLETED` receiver plus an
  always-on transition subscription independent of this service -- the
  remainder of MVP-PLAN.md §3.3's "Stage-A gate + drive-session lifecycle"
  line item.

### Detection scope notes (real limitations, not oversights)

- **No real microphone audio, anywhere, ever, in this build.** There is no
  consent flow for continuous mic capture (MVP-PLAN.md §4.2). `raw_audio`
  and the 5 `aud_*` tabular columns are always placeholders --
  `CrashClassifier`'s doc comment has the full reasoning, including a real
  bug this verification pass found: feeding the bundled model an *exact*
  all-zero `raw_audio` tensor produces **NaN on every output** (tested
  directly against the real artifact, almost certainly `log(0)` in the
  baked-in mel frontend). Low-amplitude noise avoids it. This means
  detection quality in this build is IMU/GPS-only -- the condition
  `ml/MODELS.md` already reports recall holding at 1.000 for.
- **Severity-class index mapping isn't fully empirically confirmed.**
  `CrashClassifier` assumes output index 4 of the 5-class severity softmax
  is the model's explicit NONE class and 0-3 are MINOR/MODERATE/SEVERE/
  CRITICAL in that order. Index 4 = NONE was confirmed empirically (every
  negative-class test against the real artifact put all mass there); the
  positive-class ordering is inferred from `model.py`'s comment and
  `ml/common/config.py`'s `SEVERITY` list order, not independently
  triggered, since crafting a properly training-distribution-shaped
  positive sample was out of scope for this pass.
- **Never actually run on a device or emulator.** Same caveat as the
  toolchain-assessment section above -- `gradle assembleDebug` proves the
  APK packages correctly with the TFLite native runtime and the bundled
  model asset; it does not prove a real Stage-A trigger on real hardware
  produces a sane `CrashPrediction`.

### Transport scope notes (real limitations, not oversights)

- **The SMS destination number is a placeholder** (`AppConfig.SMS_DESTINATION_PLACEHOLDER`).
  There's no decided SMS gateway or companion-phone number yet -- same open
  item as MVP-PLAN.md §2②'s companion-phone receiver, which is the other
  half of this same unresolved question (what number sends TO, this is
  what number sends FROM/receives).
- **`SmsSender` has never actually sent an SMS.** Verification for this
  module split cleanly into two kinds: `Rrx1Codec`'s bit-packing was
  checked against ground truth (real Python output) with JVM unit tests,
  and `AlertApi`'s JSON contract was checked against the real backend with
  `curl` -- both things a Docker container can verify without a phone.
  Actually invoking `SmsManager` needs a real radio/SIM, which this
  environment has neither; that path is compiled and structurally
  reviewed, not executed.
- **No Hilt-Work integration.** `AlertSendWorker` builds its own small
  Retrofit/OkHttp/Json stack from a `baseUrl` string passed via `Data`
  rather than sharing `app`'s Hilt-provided instance, so WorkManager's
  default reflection-based factory can construct it with no extra setup.
  A `HiltWorkerFactory` + `Configuration.Provider` wiring in
  `RrxApplication` would remove the duplication; not worth the app-wide
  structural change for one worker in this pass.
- **The `unresponsive` RRX1 flag has no real source.** `AlertCreateDto`'s
  HTTPS schema has no field distinguishing "the user was unresponsive
  during the cancel window" from "the window simply expired" -- only
  `window.outcome` (EXPIRED/CANCELLED). `AlertTransport` sets `unresponsive
  = false` unconditionally rather than guess. The cancel-window screen is
  built now, but it doesn't close this gap: `cancel()` short-circuits
  before `send()` is ever called, so `AlertTransport` only ever sees the
  EXPIRED case, and telling "expired because unresponsive" apart from
  "expired but conscious and just didn't reach for the phone" needs real
  post-impact motion/pickup sensing (UX-APPFLOW.md §15.4's full CRITICAL
  condition), which isn't wired -- see the crash-screen scope notes below.

### Crash-screen scope notes (real limitations, not oversights)

- **Never run on a device or emulator, same caveat as every other module.**
  `assembleDebug` proves the whole `app` module (Hilt DI, Compose, the
  full `CrashFlowState` machine, the manifest-declared Activity) packages
  correctly; it does not prove the countdown actually renders, the siren
  fires, or the notification launches the Activity over a real lock
  screen. That needs real hardware.
- **CRITICAL-alone triggers the 5s window**, not UX-APPFLOW.md §15.4's
  full "CRITICAL + no post-impact motion + phone not picked up" condition
  -- neither post-impact motion nor pickup detection is wired, so severity
  is the only signal this build has to go on.
- **The same 800ms cancel-delay guard applies to the volume keys**, even
  though §15.3 only spells it out for the button. The guard's own reason
  (an impact striking the phone shouldn't be able to cancel the alert)
  applies just as much to a volume key a flying phone could physically
  strike, so `CrashCountdownViewModel.cancel()` gates both the same way
  rather than trusting the spec's silence on volume keys as permission to
  skip it.
- **`SendingScreen` is a simplified 2-state summary, not §17's full 4-node
  timestamped channel ladder.** `AlertTransport.send()` returns one final
  `TransportResult`, not a stream of intermediate progress events, so
  there's no real per-step timestamp to show; a true ladder needs
  `AlertTransport` to expose progress as a `Flow`, not built here. §16's
  feedback micro-survey and the full radial Golden Hour Dial are likewise
  out of scope -- `SendingScreen` shows a numeral-only countup/countdown
  instead.
- **`pCrash` crossing the threshold with `severity == NONE` is treated as
  MODERATE, not silently ignored.** These are two independent heads of
  the same model and can disagree in principle; `CrashTriggerNotifier`
  picks a real severity rather than propagate a contradiction (a crash
  flagged real enough to launch the countdown, described as no crash at
  all) into the alert payload.
- **The full-screen-intent permission fallback is the platform's, not a
  custom one.** On API 34+, `USE_FULL_SCREEN_INTENT` needs an explicit
  Settings-mediated grant; `CrashTriggerNotifier` always calls
  `setFullScreenIntent()` regardless, since Android itself downgrades an
  ungranted full-screen intent to a normal heads-up notification rather
  than failing -- writing a custom fallback (e.g. attempting
  `startActivity()` directly from `DriveViewModel`'s background context)
  would just hit the same background-activity-start restriction the
  full-screen-intent mechanism exists to bypass.

## Known gaps worth knowing about before extending this

- **No embedded fonts.** `ui/theme/Type.kt` falls back to the platform
  default for Fraunces/Inter and to `FontFamily.Monospace` for IBM Plex
  Mono — this tool can't produce binary `.ttf`/`.otf` assets. Add the real
  variable fonts to `app/src/main/res/font/` and wire them in before any
  screenshot that's meant to represent the final typography.
- **`DeviceIdentity`'s salt is process-lifetime only**, not persisted —
  every cold start currently registers what looks like a new device. The
  real fix (a salt persisted in `EncryptedSharedPreferences`) belongs in
  `core-data`, which doesn't exist yet.
- **No launcher icon**, no adaptive icon set — `AndroidManifest.xml`
  points at a platform placeholder drawable on purpose.
- **Real bugs the Docker verification caught in the sensing pass** (fixed,
  documented here so the pattern is recognisable next time): an XML
  comment containing `--` broke the manifest merger a second time after
  being "fixed" once already -- worth grepping for before editing manifest
  comments, not just after. More importantly, `startForeground(id,
  notification, type)` -- the 3-arg overload that takes a foreground
  service type -- doesn't exist below API 29; calling it unconditionally
  on this project's minSdk 26 compiles cleanly against compileSdk 35 but
  would throw `NoSuchMethodError` at runtime on a real API 26-28 device.
  Compilation alone can't catch that class of bug; it needed a second,
  API-level-aware read of the code. `DriveSensingService.startForegroundCompat()`
  branches on `Build.VERSION.SDK_INT` instead.
- **Real bugs the transport pass added:** a KDoc comment containing the
  literal text `*1e5/*10` broke the entire rest of `Rrx1Codec.kt` -- Kotlin
  (unlike Java/C) supports *nested* block comments, so that `/*` substring
  opened an unintended inner comment with no matching close, leaving the
  real closing `*/` pointing at the wrong comment and everything after
  genuinely unclosed. Same failure family as the XML `--` bug, different
  language. And a Kotlin compiler limitation, not a mistake exactly:
  smart-casting a nullable `val` to non-null doesn't work across a Gradle
  module boundary the way it does within one module -- `TransportSection.kt`
  needed a local `val` to hold `result.httpsResponse` before the nullable
  field was usable smart-cast-free.
- **Real bugs the crash-screen pass added, both caught by the Docker
  verification, neither by review alone:** the XML `--`-in-comment bug
  recurred a *third* time -- this time in doc comments added to
  `AndroidManifest.xml` for `CrashCountdownActivity`'s `<activity>`
  element and the top permissions block -- and again failed the manifest
  merger with the exact same `ManifestMerger2$MergeFailureException`.
  Three occurrences across three separate passes is itself the lesson:
  grepping for `--` before touching a manifest comment isn't optional
  caution, it's a known-recurring failure mode in this codebase. Second,
  `CrashCountdownScreen.kt`'s `val buttonFill by animateFloatAsState(...)`
  failed to compile with "has no method `getValue`" -- Compose's property
  delegate syntax for `State<T>` needs `androidx.compose.runtime.getValue`
  imported explicitly (and `setValue` for mutable state), a step so easy
  to forget IntelliJ/Android Studio normally auto-imports it; a `kotlinc`
  build with no IDE has no such safety net. Also worth noting as a near-miss
  that *didn't* recur: an earlier attempt at the manifest's `<activity>`
  entry used a nonexistent `android:showOnLockScreen` attribute (the real
  API, `setShowWhenLocked()`/`setTurnScreenOn()`, is Activity-level, not a
  manifest attribute) -- caught on inline review before the Docker build
  ever ran, so it never shows up in a build log, but it's the same
  "verify against the real API surface, not what sounds plausible"
  discipline the rest of this project has needed repeatedly.
