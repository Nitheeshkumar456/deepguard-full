package com.example.deepguard.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.text.KeyboardOptions
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
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.example.deepguard.presentation.AuthState
import com.example.deepguard.presentation.AuthViewModel
import com.example.deepguard.ui.components.DeepGuardButton
import com.example.deepguard.ui.components.DeepGuardTextField
import com.example.deepguard.ui.theme.ErrorColor

@Composable
fun OtpVerificationScreen(
    viewModel: AuthViewModel,
    onVerificationSuccess: (purpose: String) -> Unit
) {
    val authState by viewModel.authState.collectAsState()
    
    var otpCode by remember { mutableStateOf("") }
    val purpose = viewModel.otpPurpose

    LaunchedEffect(authState) {
        if (authState is AuthState.Success) {
            viewModel.resetState()
            onVerificationSuccess(purpose)
        }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background)
            .padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        Text(
            text = if (purpose == "reset") "Password Reset Code" else "Verify Email",
            style = MaterialTheme.typography.headlineLarge,
            color = MaterialTheme.colorScheme.onBackground
        )
        Text(
            text = "We sent a 6-digit verification code to\n${viewModel.tempEmail}",
            style = MaterialTheme.typography.bodyLarge,
            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f),
            textAlign = TextAlign.Center,
            modifier = Modifier.padding(top = 8.dp, bottom = 32.dp)
        )

        DeepGuardTextField(
            value = otpCode,
            onValueChange = { input -> 
                val filtered = input.filter { it.isDigit() }
                if (filtered.length <= 6) otpCode = filtered 
            },
            label = "Enter 6-Digit Code",
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number)
        )
        
        if (authState is AuthState.Error) {
            Text(
                text = (authState as AuthState.Error).error,
                color = ErrorColor,
                style = MaterialTheme.typography.bodySmall,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = 8.dp)
            )
        }

        Spacer(modifier = Modifier.height(24.dp))

        DeepGuardButton(
            text = "Verify Code",
            onClick = { 
                if (otpCode.length == 6) {
                    viewModel.verifyOtp(otpCode)
                }
            },
            isLoading = authState is AuthState.Loading,
            enabled = otpCode.length == 6 && authState !is AuthState.Loading
        )

        Spacer(modifier = Modifier.height(16.dp))

        TextButton(
            onClick = { viewModel.sendOtp(viewModel.tempEmail, purpose) },
            enabled = authState !is AuthState.Loading
        ) {
            Text(
                text = "Resend Code",
                color = if (authState is AuthState.Loading) MaterialTheme.colorScheme.onSurface.copy(alpha = 0.4f) else MaterialTheme.colorScheme.primary
            )
        }
    }
}

