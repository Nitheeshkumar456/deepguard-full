package com.example.deepguard.network

import com.google.gson.annotations.SerializedName

data class UserRegisterRequest(
    val name: String,
    val email: String,
    val password: String
)

data class UserLoginRequest(
    val email: String,
    val password: String
)

data class TokenResponse(
    @SerializedName("access_token") val accessToken: String,
    @SerializedName("refresh_token") val refreshToken: String,
    @SerializedName("token_type") val tokenType: String = "bearer"
)

data class MsgResponse(
    val message: String
)

data class OtpSendRequest(
    val email: String,
    val purpose: String = "register"
)

data class OtpVerifyRequest(
    val email: String,
    val code: String,
    val purpose: String = "register"
)

data class VerifyOtpResponse(
    val verified: Boolean,
    @SerializedName("reset_token") val resetToken: String? = null,
    val message: String
)

data class ForgotPasswordRequest(
    val email: String
)

data class ResetPasswordRequest(
    val email: String,
    val token: String,
    @SerializedName("new_password") val newPassword: String
)

data class RefreshRequest(
    @SerializedName("refresh_token") val refreshToken: String
)

data class UserResponse(
    val id: Int,
    val name: String,
    val email: String,
    @SerializedName("is_active") val isActive: Boolean,
    @SerializedName("is_verified") val isVerified: Boolean,
    val version: Int = 1,
    @SerializedName("created_at") val createdAt: String
)

data class ProfileUpdateRequest(
    val name: String,
    val version: Int? = null
)


