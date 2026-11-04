package com.example.deepguard.presentation

import com.example.deepguard.data.AuthRepository
import com.example.deepguard.data.TokenManager
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
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import retrofit2.Response

@OptIn(ExperimentalCoroutinesApi::class)
class AuthViewModelTest {

    private val testDispatcher = StandardTestDispatcher()

    @Before
    fun setUp() {
        Dispatchers.setMain(testDispatcher)
    }

    @After
    fun tearDown() {
        Dispatchers.resetMain()
    }

    @Test
    fun testInitialStateIsIdle() = runTest {
        val fakeApi = FakeAuthApi()
        val fakeTokenManager = FakeTokenManager()
        val repo = AuthRepository(fakeApi, fakeTokenManager)
        val viewModel = AuthViewModel(repo)

        assertEquals(AuthState.Idle, viewModel.authState.value)
    }

    @Test
    fun testRegisterPasswordValidationFailure() = runTest {
        val fakeApi = FakeAuthApi()
        val fakeTokenManager = FakeTokenManager()
        val repo = AuthRepository(fakeApi, fakeTokenManager)
        val viewModel = AuthViewModel(repo)

        // Weak password missing special character and uppercase
        viewModel.register("John Doe", "john@example.com", "weakpass1", "weakpass1")
        advanceUntilIdle()

        assertTrue(viewModel.authState.value is AuthState.Error)
        assertEquals("Please satisfy all password complexity rules.", (viewModel.authState.value as AuthState.Error).error)
    }

    @Test
    fun testRegisterPasswordMismatchFailure() = runTest {
        val fakeApi = FakeAuthApi()
        val fakeTokenManager = FakeTokenManager()
        val repo = AuthRepository(fakeApi, fakeTokenManager)
        val viewModel = AuthViewModel(repo)

        viewModel.register("John Doe", "john@example.com", "SecretPass123!", "MismatchPass123!")
        advanceUntilIdle()

        assertTrue(viewModel.authState.value is AuthState.Error)
        assertEquals("Passwords do not match.", (viewModel.authState.value as AuthState.Error).error)
    }

    @Test
    fun testRegisterSuccess() = runTest {
        val fakeApi = FakeAuthApi()
        val fakeTokenManager = FakeTokenManager()
        val repo = AuthRepository(fakeApi, fakeTokenManager)
        val viewModel = AuthViewModel(repo)

        viewModel.register("John Doe", "john@example.com", "SecretPass123!", "SecretPass123!")
        advanceUntilIdle()

        assertTrue(viewModel.authState.value is AuthState.Success)
        assertEquals("john@example.com", viewModel.tempEmail)
        assertEquals("register", viewModel.otpPurpose)
    }

    @Test
    fun testLoginSuccessPopulatesCurrentUser() = runTest {
        val fakeApi = FakeAuthApi()
        val fakeTokenManager = FakeTokenManager()
        val repo = AuthRepository(fakeApi, fakeTokenManager)
        val viewModel = AuthViewModel(repo)

        viewModel.login("john@example.com", "SecretPass123!")
        advanceUntilIdle()

        assertTrue(viewModel.authState.value is AuthState.Success)
        assertEquals("sample_access_token", fakeTokenManager.savedAccessToken)
        assertEquals("John Doe", viewModel.currentUser.value?.name)
        assertEquals("john@example.com", viewModel.currentUser.value?.email)
    }

    @Test
    fun testLogoutClearsTokensAndUser() = runTest {
        val fakeApi = FakeAuthApi()
        val fakeTokenManager = FakeTokenManager()
        val repo = AuthRepository(fakeApi, fakeTokenManager)
        val viewModel = AuthViewModel(repo)

        viewModel.login("john@example.com", "SecretPass123!")
        advanceUntilIdle()

        var logoutCompleted = false
        viewModel.logout { logoutCompleted = true }
        advanceUntilIdle()

        assertTrue(logoutCompleted)
        assertNull(fakeTokenManager.savedAccessToken)
        assertNull(viewModel.currentUser.value)
        assertEquals(AuthState.Idle, viewModel.authState.value)
    }

    @Test
    fun testVerifyOtpSuccess() = runTest {
        val fakeApi = FakeAuthApi()
        val fakeTokenManager = FakeTokenManager()
        val repo = AuthRepository(fakeApi, fakeTokenManager)
        val viewModel = AuthViewModel(repo)

        viewModel.tempEmail = "john@example.com"
        viewModel.otpPurpose = "reset"
        viewModel.verifyOtp("123456")
        advanceUntilIdle()

        assertTrue(viewModel.authState.value is AuthState.Success)
        assertEquals("fake_reset_token", viewModel.resetToken)
    }

    @Test
    fun testResetPasswordMissingTokenFails() = runTest {
        val fakeApi = FakeAuthApi()
        val fakeTokenManager = FakeTokenManager()
        val repo = AuthRepository(fakeApi, fakeTokenManager)
        val viewModel = AuthViewModel(repo)

        viewModel.resetToken = null
        viewModel.resetPassword("NewSecretPass123!", "NewSecretPass123!")

        assertTrue(viewModel.authState.value is AuthState.Error)
        assertEquals("Missing reset token", (viewModel.authState.value as AuthState.Error).error)
    }

    @Test
    fun testResetPasswordSuccess() = runTest {
        val fakeApi = FakeAuthApi()
        val fakeTokenManager = FakeTokenManager()
        val repo = AuthRepository(fakeApi, fakeTokenManager)
        val viewModel = AuthViewModel(repo)

        viewModel.tempEmail = "john@example.com"
        viewModel.resetToken = "valid_reset_token"
        viewModel.resetPassword("NewSecretPass123!", "NewSecretPass123!")
        advanceUntilIdle()

        assertTrue(viewModel.authState.value is AuthState.Success)
        assertNull(viewModel.resetToken)
    }

    @Test
    fun testPersistentLoginSuccess() = runTest {
        val fakeApi = FakeAuthApi()
        val fakeTokenManager = FakeTokenManager().apply { savedAccessToken = "valid_token" }
        val repo = AuthRepository(fakeApi, fakeTokenManager)
        val viewModel = AuthViewModel(repo)

        var loginResult: Boolean? = null
        viewModel.checkPersistentLogin { loginResult = it }
        advanceUntilIdle()

        assertTrue(loginResult == true)
        assertEquals("John Doe", viewModel.currentUser.value?.name)
    }

    @Test
    fun testPersistentLoginFailureClearsTokens() = runTest {
        val fakeApi = object : FakeAuthApi() {
            override suspend fun getMe(): Response<UserResponse> {
                return Response.error(401, okhttp3.ResponseBody.Companion.run { "{\"detail\":\"Session expired\"}".toResponseBody() })
            }
        }
        val fakeTokenManager = FakeTokenManager().apply { savedAccessToken = "expired_token" }
        val repo = AuthRepository(fakeApi, fakeTokenManager)
        val viewModel = AuthViewModel(repo)

        var loginResult: Boolean? = null
        viewModel.checkPersistentLogin { loginResult = it }
        advanceUntilIdle()

        assertTrue(loginResult == false)
        assertNull(fakeTokenManager.savedAccessToken)
        assertNull(viewModel.currentUser.value)
    }

    @Test
    fun testSendOtpPreservesPurpose() = runTest {
        val fakeApi = FakeAuthApi()
        val fakeTokenManager = FakeTokenManager()
        val repo = AuthRepository(fakeApi, fakeTokenManager)
        val viewModel = AuthViewModel(repo)

        viewModel.tempEmail = "reset_user@example.com"
        viewModel.otpPurpose = "reset"
        viewModel.sendOtp("reset_user@example.com", "reset")
        advanceUntilIdle()

        assertTrue(viewModel.authState.value is AuthState.Success)
        assertEquals("reset", viewModel.otpPurpose)
        assertEquals("reset_user@example.com", viewModel.tempEmail)
    }

    @Test
    fun testResetState() = runTest {
        val fakeApi = FakeAuthApi()
        val fakeTokenManager = FakeTokenManager()
        val repo = AuthRepository(fakeApi, fakeTokenManager)
        val viewModel = AuthViewModel(repo)

        viewModel.register("John Doe", "john@example.com", "SecretPass123!", "SecretPass123!")
        advanceUntilIdle()
        viewModel.resetState()

        assertEquals(AuthState.Idle, viewModel.authState.value)
    }
}

private open class FakeAuthApi : AuthApi {
    override suspend fun register(request: UserRegisterRequest): Response<MsgResponse> {
        return Response.success(MsgResponse("Registration successful. OTP sent."))
    }

    override suspend fun login(request: UserLoginRequest): Response<TokenResponse> {
        return Response.success(TokenResponse("sample_access_token", "sample_refresh_token", "bearer"))
    }

    override suspend fun logout(request: RefreshRequest): Response<MsgResponse> {
        return Response.success(MsgResponse("Logged out successfully"))
    }

    override suspend fun getMe(): Response<UserResponse> {
        return Response.success(
            UserResponse(
                id = 1,
                name = "John Doe",
                email = "john@example.com",
                isActive = true,
                isVerified = true,
                createdAt = "2026-08-31T00:00:00"
            )
        )
    }

    override suspend fun updateProfile(request: com.example.deepguard.network.ProfileUpdateRequest): Response<UserResponse> {
        return Response.success(
            UserResponse(
                id = 1,
                name = request.name,
                email = "john@example.com",
                isActive = true,
                isVerified = true,
                createdAt = "2026-08-31T00:00:00"
            )
        )
    }


    override suspend fun sendOtp(request: OtpSendRequest): Response<MsgResponse> {
        return Response.success(MsgResponse("OTP sent successfully."))
    }

    override suspend fun verifyOtp(request: OtpVerifyRequest): Response<VerifyOtpResponse> {
        return Response.success(VerifyOtpResponse(true, "fake_reset_token", "OTP verified"))
    }

    override suspend fun forgotPassword(request: ForgotPasswordRequest): Response<MsgResponse> {
        return Response.success(MsgResponse("Reset OTP sent"))
    }

    override suspend fun resetPassword(request: ResetPasswordRequest): Response<MsgResponse> {
        return Response.success(MsgResponse("Password reset successful"))
    }
}

private class FakeTokenManager : TokenManager(null) {
    var savedAccessToken: String? = null
    var savedRefreshToken: String? = null

    override val accessToken: kotlinx.coroutines.flow.Flow<String?> = kotlinx.coroutines.flow.flow {
        emit(savedAccessToken)
    }

    override val refreshToken: kotlinx.coroutines.flow.Flow<String?> = kotlinx.coroutines.flow.flow {
        emit(savedRefreshToken)
    }

    override suspend fun saveTokens(accessToken: String, refreshToken: String) {
        savedAccessToken = accessToken
        savedRefreshToken = refreshToken
    }

    override suspend fun clearTokens() {
        savedAccessToken = null
        savedRefreshToken = null
    }
}

