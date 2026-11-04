package com.example.deepguard.presentation

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.deepguard.data.SyncRepository
import com.example.deepguard.network.NotificationOut
import com.example.deepguard.network.WebSocketManager
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

class NotificationViewModel(
    private val syncRepository: SyncRepository
) : ViewModel() {

    private val _notifications = MutableStateFlow<List<NotificationOut>>(emptyList())
    val notifications: StateFlow<List<NotificationOut>> = _notifications.asStateFlow()

    private val _isLoading = MutableStateFlow(false)
    val isLoading: StateFlow<Boolean> = _isLoading.asStateFlow()

    private val _errorMessage = MutableStateFlow<String?>(null)
    val errorMessage: StateFlow<String?> = _errorMessage.asStateFlow()

    init {
        loadNotifications()
        viewModelScope.launch {
            WebSocketManager.events.collect { msg ->
                when (msg.event) {
                    "notification.created", "notification.read" -> {
                        loadNotifications(silent = true)
                    }
                }
            }
        }
    }

    fun loadNotifications(silent: Boolean = false) {
        if (!silent) _isLoading.value = true
        _errorMessage.value = null
        viewModelScope.launch {
            val result = syncRepository.getNotifications()
            result.onSuccess {
                _notifications.value = it
            }.onFailure {
                if (!silent) _errorMessage.value = it.message ?: "Failed to load notifications"
            }
            if (!silent) _isLoading.value = false
        }
    }

    fun markAsRead(id: Int) {
        viewModelScope.launch {
            val result = syncRepository.markNotificationAsRead(id)
            result.onSuccess { updated ->
                _notifications.value = _notifications.value.map {
                    if (it.id == id) updated else it
                }
            }
        }
    }

    fun markAllAsRead() {
        viewModelScope.launch {
            val result = syncRepository.markAllNotificationsAsRead()
            result.onSuccess {
                _notifications.value = _notifications.value.map {
                    it.copy(isRead = true)
                }
            }
        }
    }

    fun deleteNotification(id: Int) {
        viewModelScope.launch {
            val result = syncRepository.deleteNotification(id)
            result.onSuccess {
                _notifications.value = _notifications.value.filter { it.id != id }
            }
        }
    }

    fun clearAll() {
        viewModelScope.launch {
            val result = syncRepository.clearAllNotifications()
            result.onSuccess {
                _notifications.value = emptyList()
            }
        }
    }
}
