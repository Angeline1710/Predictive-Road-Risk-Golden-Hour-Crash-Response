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
| `app` | Real: Hilt DI, Compose + Material3 theme transcribed from UX-APPFLOW.md §28/§6, Retrofit client, and one working screen that registers the device against the live backend (`POST /v1/devices/register`, DTOs matching `backend/app/schemas/device.py` field-for-field) |
| `core-sensing` | Placeholder only — see `Placeholder.kt`. IMU ring buffer, Stage-A gate, foreground service: not built (~4 person-days, MVP-PLAN.md §3.3) |
| `core-detection` | Placeholder only. TFLite runner for `ml/artifacts/crash_fusion_deployable_v1.tflite`: not built (~1 person-day) |
| `core-transport` | Placeholder only. Real HTTPS→SMS channel strategy with retry/parallel-send-on-CRITICAL: not built (~2.5 person-days). `app`'s Retrofit call is explicitly not this — it's one direct call proving the toolchain, not the real transport layer |
| `core-data` | Placeholder only. Room offline queue, EncryptedSharedPreferences token/medical storage: not built |

No sensing, no crash detection, no cancel-window screen, no onboarding, no
drive mode. Those are the bulk of MVP-PLAN.md §3.3's remaining ~21
person-days and are correctly out of scope for a single scaffolding pass.

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
- **No gradle wrapper committed.** `gradlew`/`gradlew.bat`/
  `gradle/wrapper/gradle-wrapper.jar` need `gradle wrapper
  --gradle-version 8.7` run once, from inside a real Gradle install (or
  the verification Docker image) — that's a generated binary artifact,
  not something to hand-write. Until then, build with the Docker image's
  system `gradle` instead of `./gradlew`.
- **No launcher icon**, no adaptive icon set — `AndroidManifest.xml`
  points at a platform placeholder drawable on purpose.
