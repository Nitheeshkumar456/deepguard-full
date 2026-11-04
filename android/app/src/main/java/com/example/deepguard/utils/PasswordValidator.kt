package com.example.deepguard.utils

data class PasswordChecks(
    val hasMinLength: Boolean,
    val hasLowercase: Boolean,
    val hasUppercase: Boolean,
    val hasDigit: Boolean,
    val hasSpecial: Boolean
) {
    val allPassed: Boolean
        get() = hasMinLength && hasLowercase && hasUppercase && hasDigit && hasSpecial
}

object PasswordValidator {
    private val EMAIL_REGEX = "^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}\$".toRegex()

    fun evaluate(password: String): PasswordChecks {
        return PasswordChecks(
            hasMinLength = password.length >= 8,
            hasLowercase = password.any { it.isLowerCase() },
            hasUppercase = password.any { it.isUpperCase() },
            hasDigit = password.any { it.isDigit() },
            hasSpecial = password.any { !it.isLetterOrDigit() }
        )
    }

    fun isValidEmail(email: String): Boolean {
        return email.isNotBlank() && EMAIL_REGEX.matches(email.trim())
    }
}

