package com.example.deepguard.data

import com.example.deepguard.network.AnalysisDetailOut
import com.example.deepguard.network.AnalysisIndicatorOut
import com.example.deepguard.network.AnalysisResultOut
import com.example.deepguard.network.TokenResponse
import com.example.deepguard.network.VerifyOtpResponse
import com.google.gson.Gson
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test

class DataModelSerializationTest {

    private val gson = Gson()

    @Test
    fun testTokenResponseDeserialization() {
        val json = """
            {
                "access_token": "access_xyz",
                "refresh_token": "refresh_xyz",
                "token_type": "bearer"
            }
        """.trimIndent()

        val token = gson.fromJson(json, TokenResponse::class.java)
        assertEquals("access_xyz", token.accessToken)
        assertEquals("refresh_xyz", token.refreshToken)
        assertEquals("bearer", token.tokenType)
    }

    @Test
    fun testVerifyOtpResponseDeserialization() {
        val json = """
            {
                "verified": true,
                "reset_token": "reset_token_123",
                "message": "OTP verification successful"
            }
        """.trimIndent()

        val resp = gson.fromJson(json, VerifyOtpResponse::class.java)
        assertTrue(resp.verified)
        assertEquals("reset_token_123", resp.resetToken)
        assertEquals("OTP verification successful", resp.message)
    }

    @Test
    fun testAnalysisDetailOutSerializationAndDeserialization() {
        val detail = AnalysisDetailOut(
            id = 42,
            userId = 1,
            mediaType = "image",
            originalFilename = "deepfake_sample.jpg",
            fileSize = 1048576L,
            mimeType = "image/jpeg",
            durationSeconds = null,
            width = 1920,
            height = 1080,
            status = "completed",
            errorMessage = null,
            processingTime = 0.45,
            createdAt = "2026-08-27T12:00:00Z",
            completedAt = "2026-08-27T12:00:01Z",
            result = AnalysisResultOut(
                id = 101,
                prediction = "synthetic",
                confidence = 0.942,
                riskLevel = "high",
                modelName = "deepguard-cnn-v1",
                modelVersion = "1.0.0",
                faceManipulationScore = 0.95,
                ganArtifactScore = 0.88,
                temporalInconsistencyScore = null,
                voiceCloningScore = null,
                spectralAnomalyScore = null,
                createdAt = "2026-08-27T12:00:01Z"
            ),
            indicators = listOf(
                AnalysisIndicatorOut(
                    id = 201,
                    indicatorType = "facial_boundary_artifacts",
                    description = "Irregular blending detected at jawline border",
                    severity = "high",
                    timestampSeconds = null,
                    frameNumber = null,
                    regionX = 0.25,
                    regionY = 0.35,
                    regionW = 0.5,
                    regionH = 0.4,
                    createdAt = "2026-08-27T12:00:01Z"
                )
            )
        )

        val json = gson.toJson(detail)
        assertNotNull(json)

        val parsed = gson.fromJson(json, AnalysisDetailOut::class.java)
        assertEquals(42, parsed.id)
        assertEquals("image", parsed.mediaType)
        assertEquals("synthetic", parsed.result?.prediction)
        assertEquals(0.942, parsed.result?.confidence ?: 0.0, 0.001)
        assertEquals(1, parsed.indicators.size)
        assertEquals("high", parsed.indicators[0].severity)
    }
}
