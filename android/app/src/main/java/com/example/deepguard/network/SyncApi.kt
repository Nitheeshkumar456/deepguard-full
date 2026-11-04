package com.example.deepguard.network

import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.DELETE
import retrofit2.http.GET
import retrofit2.http.PATCH
import retrofit2.http.PUT
import retrofit2.http.Path

interface SyncApi {

    @GET("api/settings")
    suspend fun getSettings(): Response<UserSettingsOut>

    @PUT("api/settings")
    suspend fun updateSettings(@Body request: UserSettingsUpdateRequest): Response<UserSettingsOut>

    @GET("api/notifications")
    suspend fun getNotifications(): Response<List<NotificationOut>>

    @PATCH("api/notifications/{id}/read")
    suspend fun markNotificationAsRead(@Path("id") id: Int): Response<NotificationOut>

    @PATCH("api/notifications/read-all")
    suspend fun markAllNotificationsAsRead(): Response<MsgResponse>

    @DELETE("api/notifications/{id}")
    suspend fun deleteNotification(@Path("id") id: Int): Response<MsgResponse>

    @DELETE("api/notifications")
    suspend fun clearAllNotifications(): Response<MsgResponse>

    @GET("api/sync/state")
    suspend fun getSyncState(): Response<SyncStateOut>
}
