package com.example.deepguard.utils

import okhttp3.Headers
import okhttp3.ResponseBody.Companion.toResponseBody
import org.junit.Assert.assertEquals
import org.junit.Test
import retrofit2.Response
import java.net.SocketTimeoutException
import java.net.UnknownHostException

class ErrorUtilsTest {

    @Test
    fun testRateLimit429WithRetryAfter() {
        val headers = Headers.Builder().add("Retry-After", "45").build()
        val rawResponse = okhttp3.Response.Builder()
            .code(429)
            .message("Too Many Requests")
            .protocol(okhttp3.Protocol.HTTP_1_1)
            .request(okhttp3.Request.Builder().url("http://127.0.0.1/").build())
            .headers(headers)
            .build()

        val response = Response.error<Any>("{\"detail\":\"Rate limit exceeded\"}".toResponseBody(), rawResponse)
        val message = ErrorUtils.parseError(response)
        assertEquals("Please wait 45 seconds before requesting another code.", message)
    }

    @Test
    fun testRateLimit429WithoutRetryAfter() {
        val response = Response.error<Any>(429, "{\"detail\":\"Rate limit exceeded\"}".toResponseBody())
        val message = ErrorUtils.parseError(response)
        assertEquals("Please wait before requesting another code.", message)
    }

    @Test
    fun testValidationError422() {
        val response = Response.error<Any>(422, "{\"detail\":[{\"msg\":\"field required\"}]}".toResponseBody())
        val message = ErrorUtils.parseError(response)
        assertEquals("Please check your input values.", message)
    }

    @Test
    fun testServerError500() {
        val response = Response.error<Any>(500, "{\"detail\":\"Internal server error\"}".toResponseBody())
        val message = ErrorUtils.parseError(response)
        assertEquals("Server error. Please try again later.", message)
    }

    @Test
    fun testAuthError401SessionExpired() {
        val response = Response.error<Any>(401, "{\"detail\":\"Session expired or invalid credentials signature\"}".toResponseBody())
        val message = ErrorUtils.parseError(response)
        assertEquals("Session expired. Please log in again.", message)
    }

    @Test
    fun testAuthError401IncorrectCredentials() {
        val response = Response.error<Any>(401, "{\"detail\":\"Incorrect email or password.\"}".toResponseBody())
        val message = ErrorUtils.parseError(response)
        assertEquals("Incorrect email or password.", message)
    }

    @Test
    fun testBadRequest400CustomDetail() {
        val response = Response.error<Any>(400, "{\"detail\":\"An account with this email address already exists.\"}".toResponseBody())
        val message = ErrorUtils.parseError(response)
        assertEquals("An account with this email address already exists.", message)
    }

    @Test
    fun testNetworkExceptions() {
        val timeoutEx = SocketTimeoutException("connect timed out")
        val hostEx = UnknownHostException("Unable to resolve host")
        assertEquals("Unable to reach the server. Check your internet connection.", ErrorUtils.parseException(timeoutEx))
        assertEquals("Unable to reach the server. Check your internet connection.", ErrorUtils.parseException(hostEx))
    }
}
