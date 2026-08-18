package com.rrx.coresensing

/**
 * One IMU tick. `accel*` comes from Android's TYPE_LINEAR_ACCELERATION
 * (gravity already removed) in units of g -- this is the same physical
 * quantity as ml/crash_detection/imu_data.py's `body_acc_*` (its own
 * comment: "Android's TYPE_LINEAR_ACCELERATION"). `gyro*` is in deg/s to
 * match ml/common/config.py's GYRO_RAIL_DPS convention (Android's
 * TYPE_GYROSCOPE reports rad/s; ImuSensorSource converts).
 */
data class ImuSample(
    val accelXG: Float,
    val accelYG: Float,
    val accelZG: Float,
    val gyroXDps: Float,
    val gyroYDps: Float,
    val gyroZDps: Float,
    val timestampNs: Long,
)
