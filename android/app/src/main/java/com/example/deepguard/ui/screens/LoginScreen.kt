package com.example.deepguard.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
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
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import com.example.deepguard.presentation.AuthState
import com.example.deepguard.presentation.AuthViewModel
import com.example.deepguard.ui.components.DeepGuardButton
import com.example.deepguard.ui.components.DeepGuardTextField
import com.example.deepguard.ui.theme.ErrorColor
import com.example.deepguard.utils.PasswordValidator

@Composable
fun LoginScreen(
    viewModel: AuthViewModel,
    onNavigateToSignup: () -> Unit,
    onNavigateToForgotPassword: () -> Unit,
    onLoginSuccess: () -> Unit
) {
    val authState by viewModel.authState.collectAsState()
    
    var email by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    var localError by remember { mutableStateOf<String?>(null) }

    LaunchedEffect(authState) {
        if (authState is AuthState.Success) {
            viewModel.resetState()
            onLoginSuccess()
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
            text = "Welcome Back",
            style = MaterialTheme.typography.headlineLarge,
            color = MaterialTheme.colorScheme.onBackground
        )
        Text(
            text = "Sign in to DeepGuard AI",
            style = MaterialTheme.typography.bodyLarge,
            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f),
            modifier = Modifier.padding(top = 8.dp, bottom = 32.dp)
        )

        DeepGuardTextField(
            value = email,
            onValueChange = { email = it; localError = null },
            label = "Email Address"
        )
        
        Spacer(modifier = Modifier.height(16.dp))

        DeepGuardTextField(
            value = password,
            onValueChange = { password = it; localError = null },
            label = "Password",
            visualTransformation = PasswordVisualTransformation()
        )

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
            text = "Sign In",
            onClick = { 
                localError = null
                if (email.isBlank() || password.isBlank()) {
                    localError = "Please fill in all fields."
                    return@DeepGuardButton
                }
                if (!PasswordValidator.isValidEmail(email)) {
                    localError = "Please enter a valid email address."
                    return@DeepGuardButton
                }
                viewModel.login(email, password)
            },
            isLoading = authState is AuthState.Loading
        )

        Spacer(modifier = Modifier.height(16.dp))

        TextButton(onClick = onNavigateToForgotPassword) {
            Text(text = "Forgot Password?", color = MaterialTheme.colorScheme.primary)
        }

        Spacer(modifier = Modifier.height(8.dp))

        TextButton(onClick = onNavigateToSignup) {
            Text(
                text = "Don't have an account? Sign up",
                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.8f),
                fontWeight = FontWeight.Bold
            )
        }

        Spacer(modifier = Modifier.height(16.dp))
    }
}

