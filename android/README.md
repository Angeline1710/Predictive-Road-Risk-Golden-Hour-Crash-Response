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
| `app` | Real: Hilt DI, Compose + Material3 theme transcribed from UX-APPFLOW.md §28/§6, Retrofit client, device registration against the live backend, and a Drive Mode section (permission requests, start/stop, live Stage-A readout) |
| `core-sensing` | **Real**, 2026-08-18: `ImuRingBuffer` + `StageAGate` (mirrors `ml/crash_detection/build_dataset.py`'s `stage_a_pass()` full/degraded logic exactly, 14 unit tests), `ImuSensorSource` (real SensorManager, TYPE_LINEAR_ACCELERATION + TYPE_GYROSCOPE), `GpsSpeedSource` (FusedLocationProviderClient), `DrivingDetector` (Activity Recognition IN_VEHICLE transitions), `DriveSensingService` (foreground service tying it together). Does **not** invoke a crash classifier or do anything with a confirmed Stage-A trigger yet -- that's core-detection and the cancel-window screen |
| `core-detection` | Placeholder only. TFLite runner for `ml/artifacts/crash_fusion_deployable_v1.tflite`: not built (~1 person-day) |
| `core-transport` | Placeholder only. Real HTTPS→SMS channel strategy with retry/parallel-send-on-CRITICAL: not built (~2.5 person-days). `app`'s Retrofit call is explicitly not this — it's one direct call proving the toolchain, not the real transport layer |
| `core-data` | Placeholder only. Room offline queue, EncryptedSharedPreferences token/medical storage: not built |

Still missing: crash detection itself, the cancel-window screen, transport,
onboarding, drive-mode UI beyond the raw sensor readout. See
MVP-PLAN.md §3.3 for what's left and its cost.

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
