package com.example.deepguard.presentation

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.deepguard.data.AnalysisRepository
import com.example.deepguard.network.AnalysisDetailOut
import com.example.deepguard.utils.FileUtil
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import java.io.File

sealed class AnalysisState {
    object Idle : AnalysisState()
    object Uploading : AnalysisState()
    object Processing : AnalysisState()
    data class Success(val result: AnalysisDetailOut) : AnalysisState()
    data class Error(val message: String) : AnalysisState()
}

sealed class HeatmapState {
    object Idle : HeatmapState()
    object Loading : HeatmapState()
    data class Success(
        val overlayBytes: ByteArray,
        val heatmapBytes: ByteArray?,
        val originalBytes: ByteArray?
    ) : HeatmapState()
    data class Error(val message: String) : HeatmapState()
}

class AnalysisViewModel(
    private val repository: AnalysisRepository
) : ViewModel() {

    private val _state = MutableStateFlow<AnalysisState>(AnalysisState.Idle)
    val state: StateFlow<AnalysisState> = _state.asStateFlow()

    private val _heatmapState = MutableStateFlow<HeatmapState>(HeatmapState.Idle)
    val heatmapState: StateFlow<HeatmapState> = _heatmapState.asStateFlow()

    private var activeAnalysisId: Int? = null

    init {
        viewModelScope.launch {
            com.example.deepguard.network.WebSocketManager.events.collect { msg ->
                val activeId = activeAnalysisId
                if (activeId != null && msg.entityId == activeId.toString()) {
                    when (msg.event) {
                        "analysis.completed" -> {
                            val detailResult = repository.getAnalysisDetail(activeId)
                            detailResult.onSuccess { detail ->
                                _state.value = AnalysisState.Success(detail)
                            }
                        }
                        "analysis.failed" -> {
                            _state.value = AnalysisState.Error("Analysis failed on server")
                        }
                    }
                }
            }
        }
    }

    fun uploadAndAnalyze(file: File, mediaType: String) {
        if (mediaType.equals("image", ignoreCase = true)) {
            val validation = FileUtil.validateImageFile(file)
            if (validation.isFailure) {
                _state.value = AnalysisState.Error(validation.exceptionOrNull()?.message ?: "Invalid image file")
                return
            }
        } else if (mediaType.equals("video", ignoreCase = true)) {
            val validation = FileUtil.validateVideoFile(file)
            if (validation.isFailure) {
                _state.value = AnalysisState.Error(validation.exceptionOrNull()?.message ?: "Invalid video file")
                return
            }
        } else if (mediaType.equals("audio", ignoreCase = true)) {
            val validation = FileUtil.validateAudioFile(file)
            if (validation.isFailure) {
                _state.value = AnalysisState.Error(validation.exceptionOrNull()?.message ?: "Invalid audio file")
                return
            }
        }

        _state.value = AnalysisState.Uploading
        viewModelScope.launch {
            val result = repository.uploadMedia(file, mediaType)
            result.onSuccess { response ->
                if (response.status == "completed") {
                    activeAnalysisId = response.analysisId
                    // Synchronous completion — immediately fetch detail
                    val detailResult = repository.getAnalysisDetail(response.analysisId)
                    detailResult.onSuccess { detail ->
                        _state.value = AnalysisState.Success(detail)
                    }.onFailure { err ->
                        _state.value = AnalysisState.Error(err.message ?: "Failed to fetch analysis result")
                    }
                } else if (response.status == "failed") {
                    _state.value = AnalysisState.Error(response.message)
                } else {
                    activeAnalysisId = response.analysisId
                    _state.value = AnalysisState.Processing
                    pollAnalysisStatus(response.analysisId)
                }
            }.onFailure { error ->
                _state.value = AnalysisState.Error(error.message ?: "Upload failed")
            }
        }
    }

    fun fetchAnalysisDetail(analysisId: Int) {
        activeAnalysisId = analysisId
        _state.value = AnalysisState.Processing
        viewModelScope.launch {
            val result = repository.getAnalysisDetail(analysisId)
            result.onSuccess { detail ->
                if (detail.status == "completed") {
                    _state.value = AnalysisState.Success(detail)
                } else if (detail.status == "failed") {
                    _state.value = AnalysisState.Error(detail.errorMessage ?: "Analysis failed")
                } else {
                    _state.value = AnalysisState.Processing
                    pollAnalysisStatus(analysisId)
                }
            }.onFailure { error ->
                _state.value = AnalysisState.Error(error.message ?: "Failed to load analysis details")
            }
        }
    }

    fun loadHeatmap(analysisId: Int, frame: Int? = null) {
        _heatmapState.value = HeatmapState.Loading
        viewModelScope.launch {
            val overlayRes = repository.getHeatmap(analysisId, type = "overlay", frame = frame)
            if (overlayRes.isFailure) {
                _heatmapState.value = HeatmapState.Error(overlayRes.exceptionOrNull()?.message ?: "Failed to load heatmap")
                return@launch
            }
            val overlayBytes = overlayRes.getOrNull()!!

            val pureHeatmapBytes = repository.getHeatmap(analysisId, type = "heatmap", frame = frame).getOrNull()
            val origBytes = repository.getOriginalMedia(analysisId, frame = frame).getOrNull()

            _heatmapState.value = HeatmapState.Success(
                overlayBytes = overlayBytes,
                heatmapBytes = pureHeatmapBytes,
                originalBytes = origBytes
            )
        }
    }

    private suspend fun pollAnalysisStatus(analysisId: Int) {
        var isPolling = true
        var retryCount = 0
        while (isPolling && retryCount < 30) { // Max 1 minute polling (2s intervals)
            val result = repository.getAnalysisDetail(analysisId)
            result.onSuccess { detail ->
                if (detail.status == "completed") {
                    _state.value = AnalysisState.Success(detail)
                    isPolling = false
                } else if (detail.status == "failed") {
                    _state.value = AnalysisState.Error(detail.errorMessage ?: "Analysis failed")
                    isPolling = false
                }
            }.onFailure {
                // If it fails occasionally (e.g. timeout), keep polling
                retryCount++
            }
            if (isPolling) {
                delay(2000)
                retryCount++
            }
        }
        
        if (isPolling) {
            _state.value = AnalysisState.Error("Analysis timed out")
        }
    }

    fun resetState() {
        _state.value = AnalysisState.Idle
        _heatmapState.value = HeatmapState.Idle
    }
}
