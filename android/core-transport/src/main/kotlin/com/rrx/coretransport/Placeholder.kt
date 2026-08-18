package com.rrx.coretransport

/**
 * Not implemented. Owns the real channel-strategy logic PRD.md §6.3.1
 * describes: try HTTPS first, fall back to the RRX1 SMS wire protocol
 * (backend/app/services/sms_protocol.py's counterpart) on failure, retry
 * via WorkManager, and send both channels in parallel on CRITICAL
 * severity -- MVP-PLAN.md §3.3's "Transport" line item (~2.5 person-days).
 *
 * `app/network/RrxApi.kt` in this scaffold makes one direct Retrofit call
 * (device registration) to prove the toolchain and DTO contract work; it
 * is explicitly not this layer and has none of the above.
 */
internal object TransportNotImplemented
