package com.example.deepguard.network

import android.util.Log
import com.example.deepguard.data.TokenManager
import com.google.gson.Gson
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.firstOrNull
import kotlinx.coroutines.launch
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import java.util.concurrent.TimeUnit
import kotlin.math.min
import kotlin.math.pow

import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive

object WebSocketManager {
    private const val TAG = "DeepGuardSyncWS"
    private val gson = Gson()
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

    private val client by lazy {
        OkHttpClient.Builder()
            .readTimeout(0, TimeUnit.MILLISECONDS) // Indefinite read for persistent WS
            .connectTimeout(15, TimeUnit.SECONDS)
            .build()
    }

    private var webSocket: WebSocket? = null
    private var tokenManager: TokenManager? = null

    private val _events = MutableSharedFlow<SyncWebSocketMessage>(extraBufferCapacity = 64)
    val events: SharedFlow<SyncWebSocketMessage> = _events.asSharedFlow()

    private val _isConnected = MutableStateFlow(false)
    val isConnected: StateFlow<Boolean> = _isConnected.asStateFlow()

    private var reconnectAttempt = 0
    private var isExplicitlyStopped = false
    private var reconnectJob: Job? = null
    private var pingJob: Job? = null

    fun initialize(tokenMgr: TokenManager) {
        tokenManager = tokenMgr
        connect()
    }

    @Synchronized
    fun connect() {
        val tm = tokenManager ?: return
        isExplicitlyStopped = false

        scope.launch {
            val token = tm.accessToken.firstOrNull()
            if (token.isNullOrBlank()) {
                Log.d(TAG, "No auth token available, skipping WebSocket connection.")
                return@launch
            }

            if (webSocket != null && _isConnected.value) {
                return@launch
            }

            val baseWsUrl = AppConfig.BASE_URL
                .replace("http://", "ws://")
                .replace("https://", "wss://")
                .trimEnd('/')

            val fullUrl = "$baseWsUrl/api/ws?token=$token"
            Log.d(TAG, "Connecting to WebSocket: $baseWsUrl/api/ws")

            val request = Request.Builder()
                .url(fullUrl)
                .build()

            webSocket = client.newWebSocket(request, object : WebSocketListener() {
                override fun onOpen(ws: WebSocket, response: Response) {
                    Log.i(TAG, "Connected to DeepGuard real-time sync backend.")
                    reconnectAttempt = 0
                    _isConnected.value = true
                    startHeartbeat()
                }

                override fun onMessage(ws: WebSocket, text: String) {
                    try {
                        val message = gson.fromJson(text, SyncWebSocketMessage::class.java)
                        if (message != null && message.event.isNotBlank()) {
                            Log.d(TAG, "Sync event received: ${message.event}")
                            scope.launch {
                                _events.emit(message)
                            }
                        }
                    } catch (e: Exception) {
                        Log.w(TAG, "Failed to parse sync message: $text", e)
                    }
                }

                override fun onClosing(ws: WebSocket, code: Int, reason: String) {
                    Log.d(TAG, "WebSocket closing: $code / $reason")
                    _isConnected.value = false
                    stopHeartbeat()
                }

                override fun onClosed(ws: WebSocket, code: Int, reason: String) {
                    Log.d(TAG, "WebSocket closed: $code / $reason")
                    _isConnected.value = false
                    stopHeartbeat()
                    webSocket = null
                    scheduleReconnect()
                }

                override fun onFailure(ws: WebSocket, t: Throwable, response: Response?) {
                    Log.w(TAG, "WebSocket failure: ${t.message}")
                    _isConnected.value = false
                    stopHeartbeat()
                    webSocket = null
                    scheduleReconnect()
                }
            })
        }
    }

    @Synchronized
    fun disconnect() {
        isExplicitlyStopped = true
        cancelReconnect()
        stopHeartbeat()
        try {
            webSocket?.close(1000, "App paused or logged out")
        } catch (_: Exception) {}
        webSocket = null
        _isConnected.value = false
    }

    private fun startHeartbeat() {
        stopHeartbeat()
        pingJob = scope.launch {
            while (isActive && _isConnected.value) {
                delay(25000)
                try {
                    webSocket?.send("{\"type\":\"ping\"}")
                } catch (_: Exception) {}
            }
        }
    }

    private fun stopHeartbeat() {
        pingJob?.cancel()
        pingJob = null
    }

    private fun scheduleReconnect() {
        if (isExplicitlyStopped) return
        cancelReconnect()

        val delayMs = min(1000.0 * 1.5.pow(reconnectAttempt.toDouble()), 15000.0).toLong()
        reconnectAttempt++
        Log.d(TAG, "Scheduling sync reconnect in ${delayMs}ms (attempt $reconnectAttempt)...")

        reconnectJob = scope.launch {
            delay(delayMs)
            connect()
        }
    }

    private fun cancelReconnect() {
        reconnectJob?.cancel()
        reconnectJob = null
    }
}
