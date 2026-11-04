package com.example.deepguard.presentation

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.deepguard.data.SyncRepository
import com.example.deepguard.network.UserSettingsOut
import com.example.deepguard.network.UserSettingsUpdateRequest
import com.example.deepguard.network.WebSocketManager
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

class SettingsViewModel(
    private val syncRepository: SyncRepository
) : ViewModel() {

    private val _settings = MutableStateFlow<UserSettingsOut?>(null)
    val settings: StateFlow<UserSettingsOut?> = _settings.asStateFlow()

    private val _isLoading = MutableStateFlow(false)
    val isLoading: StateFlow<Boolean> = _isLoading.asStateFlow()

    private val _errorMessage = MutableStateFlow<String?>(null)
    val errorMessage: StateFlow<String?> = _errorMessage.asStateFlow()

    init {
        loadSettings()
        viewModelScope.launch {
            WebSocketManager.events.collect { msg ->
                if (msg.event == "settings.updated") {
                    loadSettings(silent = true)
                }
            }
        }
    }

    fun loadSettings(silent: Boolean = false) {
        if (!silent) _isLoading.value = true
        _errorMessage.value = null
        viewModelScope.launch {
            val result = syncRepository.getSettings()
            result.onSuccess {
                _settings.value = it
            }.onFailure {
                if (!silent) _errorMessage.value = it.message ?: "Failed to load settings"
            }
            if (!silent) _isLoading.value = false
        }
    }

    fun updateSettings(
        sensitivityTolerance: Float?,
        apiKey: String?,
        onComplete: ((Boolean, String) -> Unit)? = null
    ) {
        val currentVersion = _settings.value?.version
        _isLoading.value = true
        _errorMessage.value = null
        viewModelScope.launch {
            val req = UserSettingsUpdateRequest(
                sensitivityTolerance = sensitivityTolerance,
                apiKey = apiKey,
                version = currentVersion
            )
            val result = syncRepository.updateSettings(req)
            result.onSuccess { updated ->
                _settings.value = updated
                _isLoading.value = false
                onComplete?.invoke(true, "Settings saved successfully.")
            }.onFailure { err ->
                _isLoading.value = false
                _errorMessage.value = err.message
                onComplete?.invoke(false, err.message ?: "Failed to update settings")
            }
        }
    }
}
