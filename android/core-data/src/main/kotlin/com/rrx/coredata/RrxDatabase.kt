package com.rrx.coredata

import androidx.room.Database
import androidx.room.RoomDatabase

/** Version 1, one table -- the offline alert-retry queue and cached
 * risk-tile storage `core-data`'s original placeholder comment described
 * are still unbuilt (folded into MVP-PLAN.md §3.3's "Settings, privacy"
 * line item, not part of this onboarding pass). */
@Database(entities = [EmergencyContact::class], version = 1, exportSchema = false)
abstract class RrxDatabase : RoomDatabase() {
    abstract fun emergencyContactDao(): EmergencyContactDao
}
