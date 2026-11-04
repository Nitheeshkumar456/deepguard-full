package com.example.deepguard.presentation

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.deepguard.data.AnalysisRepository
import com.example.deepguard.network.AnalysisSummaryOut
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

sealed class HistoryState {
    object Loading : HistoryState()
    data class Success(val items: List<AnalysisSummaryOut>) : HistoryState()
    data class Error(val message: String) : HistoryState()
}

class HistoryViewModel(
    private val repository: AnalysisRepository
) : ViewModel() {

    private val _state = MutableStateFlow<HistoryState>(HistoryState.Loading)
    val state: StateFlow<HistoryState> = _state.asStateFlow()

    init {
        viewModelScope.launch {
            com.example.deepguard.network.WebSocketManager.events.collect { msg ->
                when (msg.event) {
                    "media.uploaded", "media.deleted", "analysis.completed", "analysis.failed", "history.updated" -> {
                        refreshSilently()
                    }
                }
            }
        }
    }

    fun fetchHistory() {
        _state.value = HistoryState.Loading
        viewModelScope.launch {
            val result = repository.getHistory(page = 1, pageSize = 50)
            result.onSuccess { historyOut ->
                _state.value = HistoryState.Success(historyOut.items)
            }.onFailure { error ->
                _state.value = HistoryState.Error(error.message ?: "Failed to load history")
            }
        }
    }

    fun refreshSilently() {
        viewModelScope.launch {
            val result = repository.getHistory(page = 1, pageSize = 50)
            result.onSuccess { historyOut ->
                _state.value = HistoryState.Success(historyOut.items)
            }
        }
    }

    fun deleteHistoryItem(id: Int) {
        viewModelScope.launch {
            repository.deleteAnalysis(id)
            // Re-fetch after deletion
            fetchHistory()
        }
    }
}
