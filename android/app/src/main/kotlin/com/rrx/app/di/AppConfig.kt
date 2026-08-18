package com.rrx.app.di

/** Shared across Hilt modules so the backend base URL isn't duplicated as
 * a string literal in more than one place. */
object AppConfig {
    // 10.0.2.2 is the standard Android emulator alias for the host
    // machine's localhost -- backend/docker-compose.yml publishes the API
    // on host port 8000. A physical device on the demo Wi-Fi needs the
    // host's real LAN IP instead, same "companion-phone on the same
    // network" pattern MVP-PLAN.md §2② already established for SMS.
    const val BASE_URL = "http://10.0.2.2:8000/"

    // Placeholder destination for RRX1 SMS sends -- the real deployment
    // needs this to be the SMS gateway's or companion-phone's actual
    // number, which isn't decided/configured yet (MVP-PLAN.md §2②).
    const val SMS_DESTINATION_PLACEHOLDER = "+10000000000"
}
