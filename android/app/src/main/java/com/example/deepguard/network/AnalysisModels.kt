package com.example.deepguard.network

import com.google.gson.annotations.SerializedName

data class AnalysisSubmitResponse(
    @SerializedName("analysis_id") val analysisId: Int,
    val status: String,
    val message: String,
    @SerializedName("media_type") val mediaType: String,
    @SerializedName("original_filename") val originalFilename: String,
    @SerializedName("file_size") val fileSize: Long
)

data class AnalysisSummaryOut(
    val id: Int,
    @SerializedName("media_type") val mediaType: String,
    @SerializedName("original_filename") val originalFilename: String,
    @SerializedName("file_size") val fileSize: Long?,
    val status: String,
    @SerializedName("created_at") val createdAt: String,
    @SerializedName("completed_at") val completedAt: String?,
    @SerializedName("processing_time") val processingTime: Double?,
    val prediction: String?,
    val confidence: Double?,
    @SerializedName("risk_level") val riskLevel: String?
)

data class AnalysisHistoryOut(
    val items: List<AnalysisSummaryOut>,
    val total: Int,
    val page: Int,
    @SerializedName("page_size") val pageSize: Int,
    val pages: Int
)

data class AnalysisIndicatorOut(
    val id: Int,
    @SerializedName("indicator_type") val indicatorType: String,
    val description: String,
    val severity: String,
    @SerializedName("timestamp_seconds") val timestampSeconds: Double?,
    @SerializedName("frame_number") val frameNumber: Int?,
    @SerializedName("region_x") val regionX: Double?,
    @SerializedName("region_y") val regionY: Double?,
    @SerializedName("region_w") val regionW: Double?,
    @SerializedName("region_h") val regionH: Double?,
    @SerializedName("created_at") val createdAt: String
)

data class AnalysisResultOut(
    val id: Int,
    val prediction: String,
    val confidence: Double,
    @SerializedName("risk_level") val riskLevel: String,
    @SerializedName("model_name") val modelName: String,
    @SerializedName("model_version") val modelVersion: String?,
    @SerializedName("face_manipulation_score") val faceManipulationScore: Double?,
    @SerializedName("gan_artifact_score") val ganArtifactScore: Double?,
    @SerializedName("temporal_inconsistency_score") val temporalInconsistencyScore: Double?,
    @SerializedName("voice_cloning_score") val voiceCloningScore: Double?,
    @SerializedName("spectral_anomaly_score") val spectralAnomalyScore: Double?,
    @SerializedName("created_at") val createdAt: String
)

data class AnalysisDetailOut(
    val id: Int,
    @SerializedName("user_id") val userId: Int,
    @SerializedName("media_type") val mediaType: String,
    @SerializedName("original_filename") val originalFilename: String,
    @SerializedName("file_size") val fileSize: Long?,
    @SerializedName("mime_type") val mimeType: String?,
    @SerializedName("duration_seconds") val durationSeconds: Double?,
    val width: Int?,
    val height: Int?,
    val status: String,
    @SerializedName("error_message") val errorMessage: String?,
    @SerializedName("processing_time") val processingTime: Double?,
    @SerializedName("created_at") val createdAt: String,
    @SerializedName("completed_at") val completedAt: String?,
    val result: AnalysisResultOut?,
    val indicators: List<AnalysisIndicatorOut> = emptyList(),
    @SerializedName("heatmap_available") val heatmapAvailable: Boolean? = null,
    @SerializedName("heatmap_url") val heatmapUrl: String? = null,
    @SerializedName("original_media_url") val originalMediaUrl: String? = null
)
