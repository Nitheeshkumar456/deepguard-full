package com.example.deepguard.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import com.example.deepguard.presentation.AuthState
import com.example.deepguard.presentation.AuthViewModel
import com.example.deepguard.ui.components.DeepGuardButton
import com.example.deepguard.ui.components.DeepGuardTextField
import com.example.deepguard.ui.theme.ErrorColor
import com.example.deepguard.ui.theme.Slate400
import com.example.deepguard.ui.theme.Slate700
import com.example.deepguard.ui.theme.SuccessColor
import com.example.deepguard.utils.PasswordValidator

@Composable
fun ForgotPasswordScreen(
    viewModel: AuthViewModel,
    onNavigateToOtp: () -> Unit,
    onNavigateBack: () -> Unit
) {
    val authState by viewModel.authState.collectAsState()
    
    var email by remember { mutableStateOf(viewModel.tempEmail) }
    
    // Check if we are in the "Enter New Password" phase
    val isResetPhase = viewModel.resetToken != null
    var newPassword by remember { mutableStateOf("") }
    var confirmPassword by remember { mutableStateOf("") }
    var localError by remember { mutableStateOf<String?>(null) }

    val checks = PasswordValidator.evaluate(newPassword)

    LaunchedEffect(authState) {
        if (authState is AuthState.Success) {
            viewModel.resetState()
            if (!isResetPhase) {
                onNavigateToOtp()
            } else {
                onNavigateBack() // Go back to login after successful reset
            }
        }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background)
            .verticalScroll(rememberScrollState())
            .padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        Spacer(modifier = Modifier.height(16.dp))

        Text(
            text = if (isResetPhase) "Set New Password" else "Forgot Password",
            style = MaterialTheme.typography.headlineLarge,
            color = MaterialTheme.colorScheme.onBackground
        )
        Text(
            text = if (isResetPhase) "Please choose a strong, unique password." else "Enter your email to receive a reset code",
            style = MaterialTheme.typography.bodyLarge,
            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f),
            modifier = Modifier.padding(top = 8.dp, bottom = 24.dp)
        )

        if (!isResetPhase) {
            DeepGuardTextField(
                value = email,
                onValueChange = { email = it; localError = null },
                label = "Email Address"
            )
        } else {
            DeepGuardTextField(
                value = newPassword,
                onValueChange = { newPassword = it; localError = null },
                label = "New Password",
                visualTransformation = PasswordVisualTransformation()
            )

            Spacer(modifier = Modifier.height(12.dp))

            DeepGuardTextField(
                value = confirmPassword,
                onValueChange = { confirmPassword = it; localError = null },
                label = "Confirm New Password",
                visualTransformation = PasswordVisualTransformation()
            )

            // Password complexity checklist
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = 12.dp, bottom = 8.dp)
                    .background(
                        color = MaterialTheme.colorScheme.surface,
                        shape = MaterialTheme.shapes.small
                    )
                    .padding(12.dp),
                verticalArrangement = Arrangement.spacedBy(6.dp)
            ) {
                Text(
                    text = "Complexity Requirements:",
                    style = MaterialTheme.typography.labelMedium,
                    fontWeight = FontWeight.SemiBold,
                    color = MaterialTheme.colorScheme.onSurface
                )
                RequirementRow(label = "At least 8 characters", isPassed = checks.hasMinLength)
                RequirementRow(label = "One lowercase letter", isPassed = checks.hasLowercase)
                RequirementRow(label = "One uppercase letter", isPassed = checks.hasUppercase)
                RequirementRow(label = "One numeric digit", isPassed = checks.hasDigit)
                RequirementRow(label = "One special character", isPassed = checks.hasSpecial)
                if (confirmPassword.isNotEmpty()) {
                    RequirementRow(
                        label = "Passwords match",
                        isPassed = newPassword.isNotEmpty() && newPassword == confirmPassword
                    )
                }
            }
        }
        
        val displayError = localError ?: (authState as? AuthState.Error)?.error
        if (!displayError.isNullOrBlank()) {
            Text(
                text = displayError,
                color = ErrorColor,
                style = MaterialTheme.typography.bodySmall,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = 8.dp)
            )
        }

        Spacer(modifier = Modifier.height(24.dp))

        DeepGuardButton(
            text = if (isResetPhase) "Update Password" else "Send Reset Code",
            onClick = { 
                localError = null
                if (!isResetPhase) {
                    if (email.isBlank()) {
                        localError = "Please enter your email address."
                        return@DeepGuardButton
                    }
                    if (!PasswordValidator.isValidEmail(email)) {
                        localError = "Please enter a valid email address."
                        return@DeepGuardButton
                    }
                    viewModel.forgotPassword(email)
                } else {
                    if (newPassword.isBlank() || confirmPassword.isBlank()) {
                        localError = "Please fill in all fields."
                        return@DeepGuardButton
                    }
                    if (!checks.allPassed) {
                        localError = "Please satisfy all password complexity rules."
                        return@DeepGuardButton
                    }
                    if (newPassword != confirmPassword) {
                        localError = "Passwords do not match."
                        return@DeepGuardButton
                    }
                    viewModel.resetPassword(newPassword, confirmPassword)
                }
            },
            isLoading = authState is AuthState.Loading
        )

        Spacer(modifier = Modifier.height(16.dp))

        TextButton(onClick = onNavigateBack) {
            Text(text = "Back to Login", color = MaterialTheme.colorScheme.primary)
        }

        Spacer(modifier = Modifier.height(16.dp))
    }
}

@Composable
private fun RequirementRow(label: String, isPassed: Boolean) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(
            modifier = Modifier
                .size(8.dp)
                .clip(CircleShape)
                .background(if (isPassed) SuccessColor else Slate700)
        ) {}
        Spacer(modifier = Modifier.width(8.dp))
        Text(
            text = label,
            style = MaterialTheme.typography.bodySmall,
            color = if (isPassed) SuccessColor else Slate400
        )
    }
}

