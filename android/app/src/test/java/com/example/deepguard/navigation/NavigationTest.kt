package com.example.deepguard.navigation

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class NavigationTest {

    @Test
    fun testScreenRoutes() {
        assertEquals("splash", Screen.Splash.route)
        assertEquals("onboarding", Screen.Onboarding.route)
        assertEquals("login", Screen.Login.route)
        assertEquals("signup", Screen.Signup.route)
        assertEquals("otp_verification", Screen.OtpVerification.route)
        assertEquals("forgot_password", Screen.ForgotPassword.route)
        assertEquals("main", Screen.Main.route)
    }

    @Test
    fun testParameterizedRoutes() {
        val uploadImageRoute = Screen.UploadMedia.createRoute("image")
        assertEquals("upload_media/image", uploadImageRoute)

        val uploadVideoRoute = Screen.UploadMedia.createRoute("video")
        assertEquals("upload_media/video", uploadVideoRoute)
    }

    @Test
    fun testBottomNavScreens() {
        assertEquals("home", BottomNavScreen.Home.route)
        assertEquals("analyze", BottomNavScreen.Analyze.route)
        assertEquals("history", BottomNavScreen.History.route)
        assertEquals("profile", BottomNavScreen.Profile.route)
    }
}
