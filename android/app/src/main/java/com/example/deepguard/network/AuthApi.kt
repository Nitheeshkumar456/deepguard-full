package com.example.deepguard.network

import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST

import retrofit2.http.PUT

interface AuthApi {

    @POST("api/auth/register")
    suspend fun register(@Body request: UserRegisterRequest): Response<MsgResponse>

    @POST("api/auth/login")
    suspend fun login(@Body request: UserLoginRequest): Response<TokenResponse>

    @POST("api/auth/logout")
    suspend fun logout(@Body request: RefreshRequest): Response<MsgResponse>

    @GET("api/auth/me")
    suspend fun getMe(): Response<UserResponse>

    @PUT("api/auth/profile")
    suspend fun updateProfile(@Body request: ProfileUpdateRequest): Response<UserResponse>

    @POST("api/auth/send-otp")
    suspend fun sendOtp(@Body request: OtpSendRequest): Response<MsgResponse>

    @POST("api/auth/verify-otp")
    suspend fun verifyOtp(@Body request: OtpVerifyRequest): Response<VerifyOtpResponse>

    @POST("api/auth/forgot-password")
    suspend fun forgotPassword(@Body request: ForgotPasswordRequest): Response<MsgResponse>

    @POST("api/auth/reset-password")
    suspend fun resetPassword(@Body request: ResetPasswordRequest): Response<MsgResponse>
}

