package com.example.deepguard.data

import com.example.deepguard.network.AuthApi
import com.example.deepguard.network.ForgotPasswordRequest
import com.example.deepguard.network.MsgResponse
import com.example.deepguard.network.OtpSendRequest
import com.example.deepguard.network.OtpVerifyRequest
import com.example.deepguard.network.RefreshRequest
import com.example.deepguard.network.ResetPasswordRequest
import com.example.deepguard.network.TokenResponse
import com.example.deepguard.network.UserLoginRequest
import com.example.deepguard.network.UserRegisterRequest
import com.example.deepguard.network.UserResponse
import com.example.deepguard.network.VerifyOtpResponse
import com.example.deepguard.utils.ErrorUtils
import kotlinx.coroutines.flow.firstOrNull

open class AuthRepository(
    private val authApi: AuthApi,
    private val tokenManager: TokenManager
) {
    open suspend fun register(request: UserRegisterRequest): Result<MsgResponse> {
        return try {
            val response = authApi.register(request)
            if (response.isSuccessful && response.body() != null) {
                Result.success(response.body()!!)
            } else {
                Result.failure(Exception(ErrorUtils.parseError(response, "Registration failed")))
            }
        } catch (e: Exception) {
            Result.failure(Exception(ErrorUtils.parseException(e)))
        }
    }

    open suspend fun login(request: UserLoginRequest): Result<TokenResponse> {
        return try {
            val response = authApi.login(request)
            if (response.isSuccessful && response.body() != null) {
                val tokenResponse = response.body()!!
                tokenManager.saveTokens(tokenResponse.accessToken, tokenResponse.refreshToken)
                com.example.deepguard.network.WebSocketManager.initialize(tokenManager)
                Result.success(tokenResponse)
            } else {
                Result.failure(Exception(ErrorUtils.parseError(response, "Login failed")))
            }
        } catch (e: Exception) {
            Result.failure(Exception(ErrorUtils.parseException(e)))
        }
    }

    open suspend fun getMe(): Result<UserResponse> {
        return try {
            val response = authApi.getMe()
            if (response.isSuccessful && response.body() != null) {
                com.example.deepguard.network.WebSocketManager.initialize(tokenManager)
                Result.success(response.body()!!)
            } else {
                if (response.code() == 401) {
                    tokenManager.clearTokens()
                    com.example.deepguard.network.WebSocketManager.disconnect()
                }
                Result.failure(Exception(ErrorUtils.parseError(response, "Session expired")))
            }
        } catch (e: Exception) {
            Result.failure(Exception(ErrorUtils.parseException(e)))
        }
    }

    open suspend fun updateProfile(name: String, version: Int? = null): Result<UserResponse> {
        return try {
            val response = authApi.updateProfile(com.example.deepguard.network.ProfileUpdateRequest(name, version))
            if (response.isSuccessful && response.body() != null) {
                Result.success(response.body()!!)
            } else {
                if (response.code() == 409) {
                    Result.failure(Exception("Conflict: Profile has been modified on another device. Please refresh."))
                } else {
                    Result.failure(Exception(ErrorUtils.parseError(response, "Failed to update profile")))
                }
            }
        } catch (e: Exception) {
            Result.failure(Exception(ErrorUtils.parseException(e)))
        }
    }


    open suspend fun logout(): Result<MsgResponse> {
        return try {
            val refreshToken = tokenManager.refreshToken.firstOrNull() ?: ""
            val response = authApi.logout(RefreshRequest(refreshToken))
            tokenManager.clearTokens()
            com.example.deepguard.network.WebSocketManager.disconnect()
            if (response.isSuccessful && response.body() != null) {
                Result.success(response.body()!!)
            } else {
                Result.success(MsgResponse("Logged out"))
            }
        } catch (e: Exception) {
            tokenManager.clearTokens()
            com.example.deepguard.network.WebSocketManager.disconnect()
            Result.success(MsgResponse("Logged out"))
        }
    }

    open suspend fun sendOtp(request: OtpSendRequest): Result<MsgResponse> {
        return try {
            val response = authApi.sendOtp(request)
            if (response.isSuccessful && response.body() != null) {
                Result.success(response.body()!!)
            } else {
                Result.failure(Exception(ErrorUtils.parseError(response, "Failed to send OTP")))
            }
        } catch (e: Exception) {
            Result.failure(Exception(ErrorUtils.parseException(e)))
        }
    }

    open suspend fun verifyOtp(request: OtpVerifyRequest): Result<VerifyOtpResponse> {
        return try {
            val response = authApi.verifyOtp(request)
            if (response.isSuccessful && response.body() != null) {
                Result.success(response.body()!!)
            } else {
                Result.failure(Exception(ErrorUtils.parseError(response, "Invalid or expired verification code.")))
            }
        } catch (e: Exception) {
            Result.failure(Exception(ErrorUtils.parseException(e)))
        }
    }

    open suspend fun forgotPassword(request: ForgotPasswordRequest): Result<MsgResponse> {
        return try {
            val response = authApi.forgotPassword(request)
            if (response.isSuccessful && response.body() != null) {
                Result.success(response.body()!!)
            } else {
                Result.failure(Exception(ErrorUtils.parseError(response, "Failed to request password reset")))
            }
        } catch (e: Exception) {
            Result.failure(Exception(ErrorUtils.parseException(e)))
        }
    }

    open suspend fun resetPassword(request: ResetPasswordRequest): Result<MsgResponse> {
        return try {
            val response = authApi.resetPassword(request)
            if (response.isSuccessful && response.body() != null) {
                Result.success(response.body()!!)
            } else {
                Result.failure(Exception(ErrorUtils.parseError(response, "Failed to reset password")))
            }
        } catch (e: Exception) {
            Result.failure(Exception(ErrorUtils.parseException(e)))
        }
    }

    open suspend fun hasStoredToken(): Boolean {
        return !tokenManager.accessToken.firstOrNull().isNullOrBlank()
    }
}

