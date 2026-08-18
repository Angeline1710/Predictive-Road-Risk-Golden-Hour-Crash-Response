package com.rrx.app.ui.onboarding

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import com.rrx.app.R
import com.rrx.app.ui.theme.Bitumen000
import com.rrx.app.ui.theme.Bitumen200
import com.rrx.app.ui.theme.Highway300
import com.rrx.app.ui.theme.InkInverse
import com.rrx.app.ui.theme.Paper100
import com.rrx.app.ui.theme.Sodium500
import com.rrx.app.ui.theme.TypeCaption
import com.rrx.app.ui.theme.TypeHeading2
import com.rrx.app.ui.theme.TypeLabel

private val BLOOD_GROUPS = listOf("A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-")

/** UX-APPFLOW.md §11.4, Step 7. */
@Composable
fun MedicalScreen(viewModel: OnboardingViewModel) {
    val form by viewModel.medicalForm.collectAsState()

    Column(
        modifier = Modifier.fillMaxSize().background(Bitumen000).verticalScroll(rememberScrollState()).padding(24.dp),
    ) {
        Text(stringResource(R.string.onboarding_medical_title), style = TypeHeading2, color = InkInverse)
        Text(
            stringResource(R.string.onboarding_medical_subtitle),
            style = TypeCaption,
            color = Paper100.copy(alpha = 0.6f),
            modifier = Modifier.padding(top = 4.dp, bottom = 20.dp),
        )

        Text(stringResource(R.string.onboarding_medical_blood_group), style = TypeLabel, color = Paper100)
        Column(modifier = Modifier.padding(top = 8.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            BLOOD_GROUPS.chunked(4).forEach { row ->
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    row.forEach { group ->
                        BloodGroupChip(
                            label = group,
                            selected = form.bloodGroup == group,
                            onClick = {
                                viewModel.updateMedicalForm {
                                    it.copy(bloodGroup = if (it.bloodGroup == group) null else group)
                                }
                            },
                        )
                    }
                }
            }
        }

        OutlinedTextField(
            value = form.allergies,
            onValueChange = { value -> viewModel.updateMedicalForm { it.copy(allergies = value) } },
            label = { Text(stringResource(R.string.onboarding_medical_allergies)) },
            modifier = Modifier.padding(top = 20.dp).fillMaxWidth(),
        )
        OutlinedTextField(
            value = form.conditions,
            onValueChange = { value -> viewModel.updateMedicalForm { it.copy(conditions = value) } },
            label = { Text(stringResource(R.string.onboarding_medical_conditions)) },
            modifier = Modifier.padding(top = 12.dp).fillMaxWidth(),
        )

        Row(
            modifier = Modifier.padding(top = 16.dp).fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween,
        ) {
            Text(stringResource(R.string.onboarding_medical_organ_donor), color = Paper100)
            Switch(
                checked = form.organDonor == true,
                onCheckedChange = { checked -> viewModel.updateMedicalForm { it.copy(organDonor = checked) } },
            )
        }

        Row(modifier = Modifier.padding(top = 20.dp), verticalAlignment = Alignment.CenterVertically) {
            Text("🔒", modifier = Modifier.padding(end = 8.dp))
            Text(stringResource(R.string.onboarding_medical_encryption_line), style = TypeCaption, color = Highway300)
        }

        Button(
            onClick = viewModel::saveMedicalAndContinue,
            modifier = Modifier.padding(top = 24.dp).fillMaxWidth().height(56.dp),
        ) {
            val hasAnyField = form.bloodGroup != null || form.allergies.isNotBlank() ||
                form.conditions.isNotBlank() || form.organDonor != null
            Text(
                if (hasAnyField) stringResource(R.string.onboarding_medical_continue) else stringResource(R.string.onboarding_medical_skip)
            )
        }
    }
}

@Composable
private fun BloodGroupChip(label: String, selected: Boolean, onClick: () -> Unit) {
    Box(
        modifier = Modifier
            .clip(RoundedCornerShape(8.dp))
            .background(if (selected) Sodium500 else Bitumen200)
            .clickable(onClick = onClick)
            .padding(horizontal = 14.dp, vertical = 10.dp),
    ) {
        Text(label, color = if (selected) Bitumen000 else Paper100)
    }
}
