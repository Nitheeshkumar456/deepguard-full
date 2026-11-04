package com.example.deepguard.utils

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class PasswordValidatorTest {

    @Test
    fun testValidPasswordMeetsAllCriteria() {
        val checks = PasswordValidator.evaluate("SecurePass123!")
        assertTrue(checks.hasMinLength)
        assertTrue(checks.hasLowercase)
        assertTrue(checks.hasUppercase)
        assertTrue(checks.hasDigit)
        assertTrue(checks.hasSpecial)
        assertTrue(checks.allPassed)
    }

    @Test
    fun testPasswordTooShortFails() {
        val checks = PasswordValidator.evaluate("Pass1!")
        assertFalse(checks.hasMinLength)
        assertFalse(checks.allPassed)
    }

    @Test
    fun testPasswordMissingUppercaseFails() {
        val checks = PasswordValidator.evaluate("secretpass123!")
        assertFalse(checks.hasUppercase)
        assertFalse(checks.allPassed)
    }

    @Test
    fun testPasswordMissingLowercaseFails() {
        val checks = PasswordValidator.evaluate("SECRETPASS123!")
        assertFalse(checks.hasLowercase)
        assertFalse(checks.allPassed)
    }

    @Test
    fun testPasswordMissingDigitFails() {
        val checks = PasswordValidator.evaluate("SecretPassword!")
        assertFalse(checks.hasDigit)
        assertFalse(checks.allPassed)
    }

    @Test
    fun testPasswordMissingSpecialCharFails() {
        val checks = PasswordValidator.evaluate("SecretPass123")
        assertFalse(checks.hasSpecial)
        assertFalse(checks.allPassed)
    }

    @Test
    fun testEmailValidation() {
        assertTrue(PasswordValidator.isValidEmail("user@example.com"))
        assertTrue(PasswordValidator.isValidEmail("test.user+deepguard@domain.co.uk"))
        assertFalse(PasswordValidator.isValidEmail("invalid-email"))
        assertFalse(PasswordValidator.isValidEmail(""))
    }
}
