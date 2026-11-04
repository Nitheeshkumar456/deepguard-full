package com.example.deepguard.presentation

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.deepguard.data.AuthRepository
import com.example.deepguard.network.ForgotPasswordRequest
import com.example.deepguard.network.OtpSendRequest
import com.example.deepguard.network.OtpVerifyRequest
import com.example.deepguard.network.ResetPasswordRequest
import com.example.deepguard.network.UserLoginRequest
import com.example.deepguard.network.UserRegisterRequest
import com.example.deepguard.network.UserResponse
import com.example.deepguard.utils.PasswordValidator
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

sealed class AuthState {
    object Idle : AuthState()
    object Loading : AuthState()
    data class Success(val message: String) : AuthState()
    data class Error(val error: String) : AuthState()
}

class AuthViewModel(
    private val authRepository: AuthRepository
) : ViewModel() {

    private val _authState = MutableStateFlow<AuthState>(AuthState.Idle)
    val authState: StateFlow<AuthState> = _authState.asStateFlow()

    private val _currentUser = MutableStateFlow<UserResponse?>(null)
    val currentUser: StateFlow<UserResponse?> = _currentUser.asStateFlow()

    // Temporary state to hold data across screens
    var tempEmail: String = ""
    var resetToken: String? = null
    var otpPurpose: String = "register" // "register" or "reset"

    init {
        viewModelScope.launch {
            com.example.deepguard.network.WebSocketManager.events.collect { msg ->
                if (msg.event == "profile.updated") {
                    loadCurrentUser()
                }
            }
        }
    }

    fun register(name: String, email: String, pass: String, confirmPass: String? = null) {
        if (_authState.value is AuthState.Loading) return

        if (name.isBlank() || email.isBlank() || pass.isBlank()) {
            _authState.value = AuthState.Error("Please fill in all fields.")
            return
        }

        if (!PasswordValidator.isValidEmail(email)) {
            _authState.value = AuthState.Error("Please enter a valid email address.")
            return
        }

        val checks = PasswordValidator.evaluate(pass)
        if (!checks.allPassed) {
            _authState.value = AuthState.Error("Please satisfy all password complexity rules.")
            return
        }

        if (confirmPass != null && pass != confirmPass) {
            _authState.value = AuthState.Error("Passwords do not match.")
            return
        }

        _authState.value = AuthState.Loading
        viewModelScope.launch {
            val result = authRepository.register(UserRegisterRequest(name.trim(), email.trim(), pass))
            result.onSuccess {
                tempEmail = email.trim()
                otpPurpose = "register"
                _authState.value = AuthState.Success(it.message)
            }.onFailure {
                _authState.value = AuthState.Error(it.message ?: "Registration failed")
            }
        }
    }

    fun login(email: String, pass: String) {
        if (_authState.value is AuthState.Loading) return

        if (email.isBlank() || pass.isBlank()) {
            _authState.value = AuthState.Error("Please fill in all fields.")
            return
        }

        _authState.value = AuthState.Loading
        viewModelScope.launch {
            val result = authRepository.login(UserLoginRequest(email.trim(), pass))
            result.onSuccess {
                // Fetch profile to populate current user info
                val meResult = authRepository.getMe()
                meResult.onSuccess { user ->
                    _currentUser.value = user
                }
                _authState.value = AuthState.Success("Login successful")
            }.onFailure {
                _authState.value = AuthState.Error(it.message ?: "Incorrect email or password.")
            }
        }
    }

    fun sendOtp(email: String, purpose: String = otpPurpose) {
        if (_authState.value is AuthState.Loading) return

        _authState.value = AuthState.Loading
        viewModelScope.launch {
            val targetEmail = email.ifBlank { tempEmail }.trim()
            val result = authRepository.sendOtp(OtpSendRequest(targetEmail, purpose))
            result.onSuccess {
                tempEmail = targetEmail
                otpPurpose = purpose
                _authState.value = AuthState.Success(it.message)
            }.onFailure {
                _authState.value = AuthState.Error(it.message ?: "Failed to send OTP")
            }
        }
    }

    fun verifyOtp(code: String) {
        if (_authState.value is AuthState.Loading) return

        if (code.length < 6) {
            _authState.value = AuthState.Error("Please enter the complete 6-digit code.")
            return
        }

        _authState.value = AuthState.Loading
        viewModelScope.launch {
            val result = authRepository.verifyOtp(OtpVerifyRequest(tempEmail, code.trim(), otpPurpose))
            result.onSuccess {
                if (otpPurpose == "reset") {
                    resetToken = it.resetToken
                }
                _authState.value = AuthState.Success(it.message)
            }.onFailure {
                _authState.value = AuthState.Error(it.message ?: "Invalid or expired verification code.")
            }
        }
    }
    
    fun forgotPassword(email: String) {
        if (_authState.value is AuthState.Loading) return

        if (email.isBlank()) {
            _authState.value = AuthState.Error("Please enter your email address.")
            return
        }

        if (!PasswordValidator.isValidEmail(email)) {
            _authState.value = AuthState.Error("Please enter a valid email address.")
            return
        }

        _authState.value = AuthState.Loading
        viewModelScope.launch {
            val result = authRepository.forgotPassword(ForgotPasswordRequest(email.trim()))
            result.onSuccess {
                tempEmail = email.trim()
                otpPurpose = "reset"
                _authState.value = AuthState.Success(it.message)
            }.onFailure {
                _authState.value = AuthState.Error(it.message ?: "Failed to request password reset")
            }
        }
    }

    fun resetPassword(newPass: String, confirmPass: String? = null) {
        if (_authState.value is AuthState.Loading) return

        if (resetToken.isNullOrBlank()) {
            _authState.value = AuthState.Error("Missing reset token")
            return
        }

        val checks = PasswordValidator.evaluate(newPass)
        if (!checks.allPassed) {
            _authState.value = AuthState.Error("Please satisfy all password complexity rules.")
            return
        }

        if (confirmPass != null && newPass != confirmPass) {
            _authState.value = AuthState.Error("Passwords do not match.")
            return
        }
        
        _authState.value = AuthState.Loading
        viewModelScope.launch {
            val result = authRepository.resetPassword(ResetPasswordRequest(tempEmail, resetToken!!, newPass))
            result.onSuccess {
                resetToken = null
                _authState.value = AuthState.Success(it.message)
            }.onFailure {
                _authState.value = AuthState.Error(it.message ?: "Failed to reset password")
            }
        }
    }

    fun logout(onComplete: () -> Unit) {
        viewModelScope.launch {
            _authState.value = AuthState.Loading
            authRepository.logout()
            _currentUser.value = null
            tempEmail = ""
            resetToken = null
            _authState.value = AuthState.Idle
            onComplete()
        }
    }

    fun checkPersistentLogin(onResult: (Boolean) -> Unit) {
        viewModelScope.launch {
            if (authRepository.hasStoredToken()) {
                val meResult = authRepository.getMe()
                meResult.onSuccess { user ->
                    _currentUser.value = user
                    onResult(true)
                }.onFailure {
                    _currentUser.value = null
                    onResult(false)
                }
            } else {
                _currentUser.value = null
                onResult(false)
            }
        }
    }

    fun loadCurrentUser() {
        viewModelScope.launch {
            val meResult = authRepository.getMe()
            meResult.onSuccess { user ->
                _currentUser.value = user
            }
        }
    }

    fun updateProfile(name: String, onComplete: ((Boolean, String) -> Unit)? = null) {
        if (name.isBlank()) {
            onComplete?.invoke(false, "Name cannot be empty")
            return
        }
        viewModelScope.launch {
            val currentVersion = _currentUser.value?.version
            val result = authRepository.updateProfile(name.trim(), currentVersion)
            result.onSuccess { updatedUser ->
                _currentUser.value = updatedUser
                onComplete?.invoke(true, "Profile updated successfully.")
            }.onFailure { error ->
                onComplete?.invoke(false, error.message ?: "Failed to update profile.")
            }
        }
    }

    fun resetState() {
        _authState.value = AuthState.Idle
    }
}

