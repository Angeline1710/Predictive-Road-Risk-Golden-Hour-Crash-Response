package com.rrx.coredata

/**
 * Not implemented. Owns the Room offline queue (alerts that failed to send
 * over every channel, retried on reconnect), cached risk-tile storage, the
 * cancellation log, and EncryptedSharedPreferences-backed token/medical-info
 * storage. Not in MVP-PLAN.md §3.3's estimate as its own line item --
 * folded into "Transport" (offline queue) and "Settings, privacy" (secure
 * storage) -- but broken out here as its own module per PRD.md §12.6.
 */
internal object DataNotImplemented
