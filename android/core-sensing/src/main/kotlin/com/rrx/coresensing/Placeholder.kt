package com.rrx.coresensing

/**
 * Not implemented. Owns the 200-sample IMU ring buffer, the Stage-A gate
 * (STAGE_A_G / STAGE_A_MIN_SPEED_KMH from ml/common/config.py), the
 * foreground service, and Activity Recognition gating -- MVP-PLAN.md §3.3's
 * "Sensing" and "Stage-A gate + drive-session lifecycle" line items (~4
 * person-days). This module exists to fix the boundary per PRD.md §12.6,
 * not to claim the work is done.
 */
internal object SensingNotImplemented
