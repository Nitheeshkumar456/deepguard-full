package com.example.deepguard.data

import com.example.deepguard.network.MsgResponse
import com.example.deepguard.network.NotificationOut
import com.example.deepguard.network.SyncApi
import com.example.deepguard.network.SyncStateOut
import com.example.deepguard.network.UserSettingsOut
import com.example.deepguard.network.UserSettingsUpdateRequest
import com.example.deepguard.utils.ErrorUtils

open class SyncRepository(
    private val syncApi: SyncApi
) {
    open suspend fun getSettings(): Result<UserSettingsOut> {
        return try {
            val response = syncApi.getSettings()
            if (response.isSuccessful && response.body() != null) {
                Result.success(response.body()!!)
            } else {
                Result.failure(Exception(ErrorUtils.parseError(response, "Failed to load settings")))
            }
        } catch (e: Exception) {
            Result.failure(Exception(ErrorUtils.parseException(e)))
        }
    }

    open suspend fun updateSettings(request: UserSettingsUpdateRequest): Result<UserSettingsOut> {
        return try {
            val response = syncApi.updateSettings(request)
            if (response.isSuccessful && response.body() != null) {
                Result.success(response.body()!!)
            } else {
                if (response.code() == 409) {
                    Result.failure(Exception("Conflict: Settings were modified on another device. Please reload."))
                } else {
                    Result.failure(Exception(ErrorUtils.parseError(response, "Failed to save settings")))
                }
            }
        } catch (e: Exception) {
            Result.failure(Exception(ErrorUtils.parseException(e)))
        }
    }

    open suspend fun getNotifications(): Result<List<NotificationOut>> {
        return try {
            val response = syncApi.getNotifications()
            if (response.isSuccessful && response.body() != null) {
                Result.success(response.body()!!)
            } else {
                Result.failure(Exception(ErrorUtils.parseError(response, "Failed to load notifications")))
            }
        } catch (e: Exception) {
            Result.failure(Exception(ErrorUtils.parseException(e)))
        }
    }

    open suspend fun markNotificationAsRead(id: Int): Result<NotificationOut> {
        return try {
            val response = syncApi.markNotificationAsRead(id)
            if (response.isSuccessful && response.body() != null) {
                Result.success(response.body()!!)
            } else {
                Result.failure(Exception(ErrorUtils.parseError(response, "Failed to mark notification as read")))
            }
        } catch (e: Exception) {
            Result.failure(Exception(ErrorUtils.parseException(e)))
        }
    }

    open suspend fun markAllNotificationsAsRead(): Result<MsgResponse> {
        return try {
            val response = syncApi.markAllNotificationsAsRead()
            if (response.isSuccessful && response.body() != null) {
                Result.success(response.body()!!)
            } else {
                Result.failure(Exception(ErrorUtils.parseError(response, "Failed to mark all as read")))
            }
        } catch (e: Exception) {
            Result.failure(Exception(ErrorUtils.parseException(e)))
        }
    }

    open suspend fun deleteNotification(id: Int): Result<MsgResponse> {
        return try {
            val response = syncApi.deleteNotification(id)
            if (response.isSuccessful && response.body() != null) {
                Result.success(response.body()!!)
            } else {
                Result.failure(Exception(ErrorUtils.parseError(response, "Failed to delete notification")))
            }
        } catch (e: Exception) {
            Result.failure(Exception(ErrorUtils.parseException(e)))
        }
    }

    open suspend fun clearAllNotifications(): Result<MsgResponse> {
        return try {
            val response = syncApi.clearAllNotifications()
            if (response.isSuccessful && response.body() != null) {
                Result.success(response.body()!!)
            } else {
                Result.failure(Exception(ErrorUtils.parseError(response, "Failed to clear notifications")))
            }
        } catch (e: Exception) {
            Result.failure(Exception(ErrorUtils.parseException(e)))
        }
    }

    open suspend fun getSyncState(): Result<SyncStateOut> {
        return try {
            val response = syncApi.getSyncState()
            if (response.isSuccessful && response.body() != null) {
                Result.success(response.body()!!)
            } else {
                Result.failure(Exception(ErrorUtils.parseError(response, "Failed to get sync state")))
            }
        } catch (e: Exception) {
            Result.failure(Exception(ErrorUtils.parseException(e)))
        }
    }
}
