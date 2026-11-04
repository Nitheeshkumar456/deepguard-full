package com.example.deepguard.utils

import com.google.gson.Gson
import com.google.gson.JsonObject
import retrofit2.Response
import java.io.IOException
import java.net.SocketTimeoutException
import java.net.UnknownHostException

object ErrorUtils {

    fun <T> parseError(response: Response<T>, defaultMessage: String? = null): String {
        val code = response.code()
        
        // Check rate limiting Retry-After header
        if (code == 429) {
            val retryAfter = response.headers()["Retry-After"]?.trim()?.toIntOrNull()
            return if (retryAfter != null && retryAfter > 0) {
                "Please wait $retryAfter seconds before requesting another code."
            } else {
                "Please wait before requesting another code."
            }
        }

        // Try extracting json "detail" if present
        val errorBodyStr = try {
            response.errorBody()?.string()
        } catch (e: Exception) {
            null
        }

        var detailMessage: String? = null
        if (!errorBodyStr.isNullOrBlank()) {
            try {
                val json = Gson().fromJson(errorBodyStr, JsonObject::class.java)
                if (json.has("detail") && json.get("detail").isJsonPrimitive) {
                    detailMessage = json.get("detail").asString
                }
            } catch (ignored: Exception) {
            }
        }

        return when (code) {
            400 -> {
                // If backend provides a specific detail like "An account with this email address already exists." or password strength
                if (!detailMessage.isNullOrBlank() && !detailMessage.equals("Bad Request", ignoreCase = true)) {
                    detailMessage
                } else {
                    defaultMessage ?: "Incorrect email or password."
                }
            }
            401 -> {
                if (defaultMessage == "Session expired" || (detailMessage != null && (detailMessage.contains("Session expired", ignoreCase = true) || detailMessage.contains("credentials", ignoreCase = true) || detailMessage.contains("not provided", ignoreCase = true)))) {
                    "Session expired. Please log in again."
                } else if (!detailMessage.isNullOrBlank() && !detailMessage.equals("Unauthorized", ignoreCase = true)) {
                    detailMessage
                } else {
                    defaultMessage ?: "Incorrect email or password."
                }
            }
            403 -> {
                detailMessage ?: "Access forbidden."
            }
            404 -> {
                detailMessage ?: "Requested resource not found."
            }
            422 -> {
                "Please check your input values."
            }
            500, 502, 503, 504 -> {
                "Server error. Please try again later."
            }
            else -> {
                detailMessage ?: defaultMessage ?: "An unexpected error occurred."
            }
        }
    }

    fun parseException(e: Throwable): String {
        return when (e) {
            is SocketTimeoutException, is UnknownHostException, is IOException -> {
                "Unable to reach the server. Check your internet connection."
            }
            else -> {
                e.message ?: "An unexpected error occurred."
            }
        }
    }
}
