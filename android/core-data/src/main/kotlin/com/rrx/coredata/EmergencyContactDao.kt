package com.rrx.coredata

import androidx.room.Dao
import androidx.room.Delete
import androidx.room.Insert
import androidx.room.Query
import kotlinx.coroutines.flow.Flow

@Dao
interface EmergencyContactDao {

    @Query("SELECT * FROM emergency_contacts ORDER BY priority ASC")
    fun observeAll(): Flow<List<EmergencyContact>>

    @Query("SELECT * FROM emergency_contacts ORDER BY priority ASC")
    suspend fun getAll(): List<EmergencyContact>

    @Query("SELECT COUNT(*) FROM emergency_contacts")
    suspend fun count(): Int

    @Insert
    suspend fun insert(contact: EmergencyContact): Long

    @Delete
    suspend fun delete(contact: EmergencyContact)
}
