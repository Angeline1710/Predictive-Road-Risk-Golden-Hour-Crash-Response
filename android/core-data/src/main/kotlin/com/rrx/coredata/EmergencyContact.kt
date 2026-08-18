package com.rrx.coredata

import androidx.room.Entity
import androidx.room.PrimaryKey

/**
 * UX-APPFLOW.md §11.4: "Up to 5, priority-ordered ... Adding via contact
 * picker only -- never manual typing." [contactId]/[lookupKey] identify the
 * Android Contacts Provider row a contact was picked from -- kept so a
 * future re-sync (the number changed, the contact was deleted) has
 * something to reconcile against, not just a frozen copy of what the
 * picker returned once.
 */
@Entity(tableName = "emergency_contacts")
data class EmergencyContact(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val contactId: Long,
    val lookupKey: String,
    val displayName: String,
    val phoneNumber: String,
    /** 1 = contacted first. Enforced unique by [EmergencyContactDao] query
     * ordering, not a DB constraint -- re-priorities on delete are a
     * plain re-write of the remaining rows' priority, not a gap-filling
     * migration. */
    val priority: Int,
)
