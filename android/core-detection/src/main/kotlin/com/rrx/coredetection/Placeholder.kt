package com.rrx.coredetection

/**
 * Not implemented. Owns the TFLite interpreter that loads
 * `ml/artifacts/crash_fusion_deployable_v1.tflite` and assembles its four
 * raw inputs (IMU 200x9, raw audio for the baked-in mel frontend, GPS
 * 12x1, tabular) -- MVP-PLAN.md §3.3's "TFLite runner" line item
 * (~1 person-day, cheap precisely because normalisation and the mel
 * transform are baked into the graph, per §4.1). Not built yet.
 */
internal object DetectionNotImplemented
