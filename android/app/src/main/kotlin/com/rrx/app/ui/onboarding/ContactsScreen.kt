package com.rrx.app.ui.onboarding

import android.content.Context
import android.content.Intent
import android.net.Uri
import android.provider.ContactsContract
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import com.rrx.app.R
import com.rrx.app.ui.theme.Bitumen000
import com.rrx.app.ui.theme.Bitumen200
import com.rrx.app.ui.theme.InkInverse
import com.rrx.app.ui.theme.Paper100
import com.rrx.app.ui.theme.TypeCaption
import com.rrx.app.ui.theme.TypeHeading2
import com.rrx.coredata.EmergencyContact

/**
 * UX-APPFLOW.md §11.4, Step 6. Picks directly against
 * `ContactsContract.CommonDataKinds.Phone.CONTENT_URI` (not the generic
 * Contacts picker + a follow-up query) so the single URI the system
 * grants temporary read access to on return is also the one queried for
 * name/number -- no `READ_CONTACTS` permission needed, and matches
 * §11.4's "never manual typing" requirement structurally, not just by
 * convention.
 */
@Composable
fun ContactsScreen(viewModel: OnboardingViewModel) {
    val context = LocalContext.current
    val contacts by viewModel.contacts.collectAsState()

    val launcher = rememberLauncherForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
        val uri = result.data?.data ?: return@rememberLauncherForActivityResult
        resolvePickedPhoneContact(context, uri)?.let { viewModel.addContact(it) }
    }

    Column(modifier = Modifier.fillMaxSize().background(Bitumen000).padding(24.dp)) {
        Text(stringResource(R.string.onboarding_contacts_title), style = TypeHeading2, color = InkInverse)
        Text(
            stringResource(R.string.onboarding_contacts_subtitle),
            style = TypeCaption,
            color = Paper100.copy(alpha = 0.6f),
            modifier = Modifier.padding(top = 4.dp, bottom = 16.dp),
        )

        if (contacts.isEmpty()) {
            Text(stringResource(R.string.onboarding_contacts_empty), color = Paper100.copy(alpha = 0.6f))
        } else {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                contacts.forEach { contact -> ContactRow(contact, onRemove = { viewModel.removeContact(contact) }) }
            }
        }

        if (contacts.size < OnboardingViewModel.MAX_CONTACTS) {
            OutlinedButton(
                onClick = {
                    launcher.launch(Intent(Intent.ACTION_PICK, ContactsContract.CommonDataKinds.Phone.CONTENT_URI))
                },
                modifier = Modifier.padding(top = 16.dp).fillMaxWidth().height(48.dp),
            ) {
                Text(stringResource(R.string.onboarding_contacts_add))
            }
        } else {
            Text(
                stringResource(R.string.onboarding_contacts_limit_reached),
                style = TypeCaption,
                color = Paper100.copy(alpha = 0.6f),
                modifier = Modifier.padding(top = 16.dp),
            )
        }

        Button(onClick = viewModel::advance, modifier = Modifier.padding(top = 24.dp).fillMaxWidth().height(56.dp)) {
            Text(if (contacts.isEmpty()) stringResource(R.string.onboarding_contacts_skip) else stringResource(R.string.onboarding_contacts_continue))
        }
    }
}

@Composable
private fun ContactRow(contact: EmergencyContact, onRemove: () -> Unit) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(8.dp))
            .background(Bitumen200)
            .padding(12.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Column(modifier = Modifier.weight(1f)) {
            Text(contact.displayName, color = InkInverse)
            Text(maskPhoneNumber(contact.phoneNumber), style = TypeCaption, color = Paper100.copy(alpha = 0.6f))
        }
        Text("#${contact.priority}", style = TypeCaption, color = Paper100.copy(alpha = 0.5f))
        TextButton(onClick = onRemove) { Text("Remove") }
    }
}

/** UX-APPFLOW.md §11.4's mock shows `+91 ••••• •4471` -- country code and
 * the last 4 digits visible, everything else masked. */
private fun maskPhoneNumber(number: String): String {
    val digits = number.filter { it.isDigit() || it == '+' }
    if (digits.length <= 4) return digits
    val visibleTail = digits.takeLast(4)
    val visibleHead = if (digits.startsWith("+")) digits.takeWhile { it == '+' } + digits.drop(1).take(2) else ""
    return "$visibleHead ${"•".repeat(5)} •$visibleTail"
}

private fun resolvePickedPhoneContact(context: Context, uri: Uri): EmergencyContact? {
    context.contentResolver.query(uri, null, null, null, null)?.use { cursor ->
        if (!cursor.moveToFirst()) return null
        val contactId = cursor.getColumnIndex(ContactsContract.CommonDataKinds.Phone.CONTACT_ID)
            .takeIf { it >= 0 }?.let { cursor.getLong(it) } ?: return null
        val lookupKey = cursor.getColumnIndex(ContactsContract.CommonDataKinds.Phone.LOOKUP_KEY)
            .takeIf { it >= 0 }?.let { cursor.getString(it) } ?: ""
        val displayName = cursor.getColumnIndex(ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME)
            .takeIf { it >= 0 }?.let { cursor.getString(it) } ?: "Unknown"
        val number = cursor.getColumnIndex(ContactsContract.CommonDataKinds.Phone.NUMBER)
            .takeIf { it >= 0 }?.let { cursor.getString(it) } ?: return null
        return EmergencyContact(contactId = contactId, lookupKey = lookupKey, displayName = displayName, phoneNumber = number, priority = 0)
    }
    return null
}
