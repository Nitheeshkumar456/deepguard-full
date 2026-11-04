package com.example.deepguard.network

import com.google.gson.annotations.SerializedName

data class CaseSummaryDto(
    @SerializedName("id") val id: Int,
    @SerializedName("case_number") val caseNumber: String,
    @SerializedName("title") val title: String,
    @SerializedName("description") val description: String?,
    @SerializedName("status") val status: String,
    @SerializedName("priority") val priority: String,
    @SerializedName("tags") val tags: String?,
    @SerializedName("analyses_count") val analysesCount: Int,
    @SerializedName("notes_count") val notesCount: Int,
    @SerializedName("created_at") val createdAt: String,
    @SerializedName("updated_at") val updatedAt: String
)

data class CaseAnalysisItemDto(
    @SerializedName("id") val id: Int,
    @SerializedName("analysis_id") val analysisId: Int,
    @SerializedName("notes") val notes: String?,
    @SerializedName("added_at") val addedAt: String,
    @SerializedName("media_type") val mediaType: String,
    @SerializedName("original_filename") val originalFilename: String,
    @SerializedName("prediction") val prediction: String?,
    @SerializedName("confidence") val confidence: Float?,
    @SerializedName("risk_level") val riskLevel: String?
)

data class CaseNoteDto(
    @SerializedName("id") val id: Int,
    @SerializedName("author_name") val authorName: String,
    @SerializedName("content") val content: String,
    @SerializedName("created_at") val createdAt: String
)

data class CaseDetailDto(
    @SerializedName("id") val id: Int,
    @SerializedName("case_number") val caseNumber: String,
    @SerializedName("title") val title: String,
    @SerializedName("description") val description: String?,
    @SerializedName("status") val status: String,
    @SerializedName("priority") val priority: String,
    @SerializedName("tags") val tags: String?,
    @SerializedName("created_at") val createdAt: String,
    @SerializedName("updated_at") val updatedAt: String,
    @SerializedName("analyses") val analyses: List<CaseAnalysisItemDto>,
    @SerializedName("notes") val notes: List<CaseNoteDto>
)

data class CreateCaseRequest(
    @SerializedName("title") val title: String,
    @SerializedName("description") val description: String? = null,
    @SerializedName("priority") val priority: String? = "MEDIUM",
    @SerializedName("tags") val tags: String? = null,
    @SerializedName("initial_analysis_ids") val initialAnalysisIds: List<Int>? = null
)

data class UpdateCaseRequest(
    @SerializedName("title") val title: String? = null,
    @SerializedName("description") val description: String? = null,
    @SerializedName("status") val status: String? = null,
    @SerializedName("priority") val priority: String? = null,
    @SerializedName("tags") val tags: String? = null
)

data class AddCaseNoteRequest(
    @SerializedName("content") val content: String
)

data class AttachAnalysisRequest(
    @SerializedName("analysis_id") val analysisId: Int,
    @SerializedName("notes") val notes: String? = null
)

data class ComparisonIndicatorDto(
    @SerializedName("id") val id: Int,
    @SerializedName("type") val type: String,
    @SerializedName("description") val description: String,
    @SerializedName("severity") val severity: String
)

data class ComparisonItemDto(
    @SerializedName("id") val id: Int,
    @SerializedName("media_type") val mediaType: String,
    @SerializedName("original_filename") val originalFilename: String,
    @SerializedName("prediction") val prediction: String?,
    @SerializedName("confidence") val confidence: Float?,
    @SerializedName("risk_level") val riskLevel: String?,
    @SerializedName("model_name") val modelName: String?,
    @SerializedName("face_manipulation_score") val faceManipulationScore: Float?,
    @SerializedName("gan_artifact_score") val ganArtifactScore: Float?,
    @SerializedName("spectral_anomaly_score") val spectralAnomalyScore: Float?,
    @SerializedName("voice_cloning_score") val voiceCloningScore: Float?,
    @SerializedName("indicators") val indicators: List<ComparisonIndicatorDto>
)

data class ComparisonMetaDto(
    @SerializedName("same_modality") val sameModality: Boolean,
    @SerializedName("prediction_match") val predictionMatch: Boolean,
    @SerializedName("risk_match") val riskMatch: Boolean,
    @SerializedName("confidence_delta") val confidenceDelta: Float,
    @SerializedName("common_indicators") val commonIndicators: List<String>,
    @SerializedName("item1_unique_indicators") val item1UniqueIndicators: List<String>,
    @SerializedName("item2_unique_indicators") val item2UniqueIndicators: List<String>,
    @SerializedName("forensic_verdict") val forensicVerdict: String
)

data class ComparisonResponseDto(
    @SerializedName("item1") val item1: ComparisonItemDto,
    @SerializedName("item2") val item2: ComparisonItemDto,
    @SerializedName("comparison") val comparison: ComparisonMetaDto
)

data class SessionInfoDto(
    @SerializedName("id") val id: Int,
    @SerializedName("device_name") val deviceName: String,
    @SerializedName("platform") val platform: String,
    @SerializedName("ip_address") val ipAddress: String?,
    @SerializedName("created_at") val createdAt: String,
    @SerializedName("last_active_at") val lastActiveAt: String?,
    @SerializedName("is_current") val isCurrent: Boolean
)
