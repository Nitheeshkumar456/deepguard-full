package com.example.deepguard.network

import com.google.gson.JsonElement
import com.google.gson.annotations.SerializedName

data class UserSettingsOut(
    @SerializedName("sensitivity_tolerance") val sensitivityTolerance: Float,
    @SerializedName("api_key") val apiKey: String,
    val version: Int,
    @SerializedName("updated_at") val updatedAt: String
)

data class UserSettingsUpdateRequest(
    @SerializedName("sensitivity_tolerance") val sensitivityTolerance: Float? = null,
    @SerializedName("api_key") val apiKey: String? = null,
    val version: Int? = null
)

data class NotificationOut(
    val id: Int,
    val category: String,
    val title: String,
    val body: String,
    @SerializedName("is_read") val isRead: Boolean,
    @SerializedName("related_analysis_id") val relatedAnalysisId: Int? = null,
    @SerializedName("created_at") val createdAt: String
)

data class SyncStateOut(
    @SerializedName("server_time") val serverTime: String,
    val user: UserResponse,
    val settings: UserSettingsOut,
    @SerializedName("unread_notifications") val unreadNotifications: Int,
    @SerializedName("total_analyses") val totalAnalyses: Int,
    @SerializedName("recent_analyses") val recentAnalyses: List<AnalysisSummaryOut>
)

data class SyncWebSocketMessage(
    val event: String,
    @SerializedName("user_id") val userId: Int?,
    val timestamp: String?,
    val version: Int?,
    @SerializedName("entity_id") val entityId: String?,
    val data: JsonElement?
)
