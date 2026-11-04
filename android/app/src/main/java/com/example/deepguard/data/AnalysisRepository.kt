package com.example.deepguard.data

import com.example.deepguard.network.AnalysisApi
import com.example.deepguard.network.AnalysisDetailOut
import com.example.deepguard.network.AnalysisHistoryOut
import com.example.deepguard.network.AnalysisSubmitResponse
import com.example.deepguard.network.MsgResponse
import com.example.deepguard.utils.ErrorUtils
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.asRequestBody
import java.io.File

open class AnalysisRepository(
    private val analysisApi: AnalysisApi
) {
    open suspend fun uploadMedia(file: File, type: String): Result<AnalysisSubmitResponse> {
        return try {
            val mediaType = when (type.lowercase()) {
                "image" -> "image/*"
                "video" -> "video/*"
                "audio" -> "audio/*"
                else -> "*/*"
            }.toMediaTypeOrNull()

            val requestFile = file.asRequestBody(mediaType)
            val body = MultipartBody.Part.createFormData("file", file.name, requestFile)

            val response = when (type.lowercase()) {
                "image" -> analysisApi.uploadImage(body)
                "video" -> analysisApi.uploadVideo(body)
                "audio" -> analysisApi.uploadAudio(body)
                else -> throw IllegalArgumentException("Unknown media type")
            }

            if (response.isSuccessful && response.body() != null) {
                Result.success(response.body()!!)
            } else {
                Result.failure(Exception(ErrorUtils.parseError(response, "Upload failed")))
            }
        } catch (e: Exception) {
            Result.failure(Exception(ErrorUtils.parseException(e)))
        }
    }

    open suspend fun getHistory(page: Int = 1, pageSize: Int = 20): Result<AnalysisHistoryOut> {
        return try {
            val response = analysisApi.getHistory(page, pageSize)
            if (response.isSuccessful && response.body() != null) {
                Result.success(response.body()!!)
            } else {
                Result.failure(Exception(ErrorUtils.parseError(response, "Failed to fetch history")))
            }
        } catch (e: Exception) {
            Result.failure(Exception(ErrorUtils.parseException(e)))
        }
    }

    open suspend fun getAnalysisDetail(analysisId: Int): Result<AnalysisDetailOut> {
        return try {
            val response = analysisApi.getAnalysisDetail(analysisId)
            if (response.isSuccessful && response.body() != null) {
                Result.success(response.body()!!)
            } else {
                Result.failure(Exception(ErrorUtils.parseError(response, "Failed to fetch details")))
            }
        } catch (e: Exception) {
            Result.failure(Exception(ErrorUtils.parseException(e)))
        }
    }

    open suspend fun getHeatmap(analysisId: Int, type: String = "overlay", frame: Int? = null): Result<ByteArray> {
        return try {
            val response = analysisApi.getHeatmap(analysisId, type, frame)
            if (response.isSuccessful && response.body() != null) {
                Result.success(response.body()!!.bytes())
            } else {
                Result.failure(Exception(ErrorUtils.parseError(response, "Failed to fetch heatmap")))
            }
        } catch (e: Exception) {
            Result.failure(Exception(ErrorUtils.parseException(e)))
        }
    }

    open suspend fun getOriginalMedia(analysisId: Int, frame: Int? = null): Result<ByteArray> {
        return try {
            val response = analysisApi.getOriginalMedia(analysisId, frame)
            if (response.isSuccessful && response.body() != null) {
                Result.success(response.body()!!.bytes())
            } else {
                Result.failure(Exception(ErrorUtils.parseError(response, "Failed to fetch original media")))
            }
        } catch (e: Exception) {
            Result.failure(Exception(ErrorUtils.parseException(e)))
        }
    }

    open suspend fun deleteAnalysis(analysisId: Int): Result<MsgResponse> {
        return try {
            val response = analysisApi.deleteAnalysis(analysisId)
            if (response.isSuccessful && response.body() != null) {
                Result.success(response.body()!!)
            } else {
                Result.failure(Exception(ErrorUtils.parseError(response, "Failed to delete")))
            }
        } catch (e: Exception) {
            Result.failure(Exception(ErrorUtils.parseException(e)))
        }
    }
}
