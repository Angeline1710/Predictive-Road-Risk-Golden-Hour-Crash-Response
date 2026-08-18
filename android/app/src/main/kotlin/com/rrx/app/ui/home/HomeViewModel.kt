package com.rrx.app.ui.home

import android.content.Context
import android.os.Build
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rrx.app.device.DeviceIdentity
import com.rrx.app.network.RrxApi
import com.rrx.app.network.dto.DeviceRegisterRequest
import dagger.hilt.android.lifecycle.HiltViewModel
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

sealed interface RegistrationState {
    data object Idle : RegistrationState
    data object InFlight : RegistrationState
    data class Registered(val deviceId: String) : RegistrationState
    data class Failed(val message: String) : RegistrationState
}

@HiltViewModel
class HomeViewModel @Inject constructor(
    private val api: RrxApi,
    @ApplicationContext private val context: Context,
) : ViewModel() {

    private val _state = MutableStateFlow<RegistrationState>(RegistrationState.Idle)
    val state: StateFlow<RegistrationState> = _state

    /**
     * Exercises the real `POST /v1/devices/register` contract end to end --
     * this is the scaffold's one genuine proof that the toolchain, DTOs,
     * and the backend agree with each other, not a canned response.
     */
    fun registerDevice() {
        _state.value = RegistrationState.InFlight
        viewModelScope.launch {
            try {
                val response = api.registerDevice(
                    DeviceRegisterRequest(
                        deviceHash = DeviceIdentity.saltedHash(context),
                        model = Build.MODEL,
                        androidVersion = Build.VERSION.RELEASE,
                        appVersion = "0.1.0-scaffold",
                    )
                )
                _state.value = RegistrationState.Registered(response.deviceId)
            } catch (e: Exception) {
                _state.value = RegistrationState.Failed(e.message ?: e::class.simpleName ?: "unknown error")
            }
        }
    }
}
