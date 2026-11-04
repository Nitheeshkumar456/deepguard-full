package com.example.deepguard.network

import retrofit2.http.Body
import retrofit2.http.DELETE
import retrofit2.http.GET
import retrofit2.http.PATCH
import retrofit2.http.POST
import retrofit2.http.Path
import retrofit2.http.Query

interface CasesApi {
    @GET("api/cases")
    suspend fun getCases(
        @Query("status") status: String? = null,
        @Query("priority") priority: String? = null,
        @Query("search") search: String? = null
    ): List<CaseSummaryDto>

    @POST("api/cases")
    suspend fun createCase(
        @Body request: CreateCaseRequest
    ): CaseDetailDto

    @GET("api/cases/{caseId}")
    suspend fun getCaseDetail(
        @Path("caseId") caseId: Int
    ): CaseDetailDto

    @PATCH("api/cases/{caseId}")
    suspend fun updateCase(
        @Path("caseId") caseId: Int,
        @Body request: UpdateCaseRequest
    ): CaseDetailDto

    @POST("api/cases/{caseId}/analyses")
    suspend fun attachAnalysis(
        @Path("caseId") caseId: Int,
        @Body request: AttachAnalysisRequest
    ): CaseDetailDto

    @DELETE("api/cases/{caseId}/analyses/{analysisId}")
    suspend fun detachAnalysis(
        @Path("caseId") caseId: Int,
        @Path("analysisId") analysisId: Int
    ): CaseDetailDto

    @POST("api/cases/{caseId}/notes")
    suspend fun addNote(
        @Path("caseId") caseId: Int,
        @Body request: AddCaseNoteRequest
    ): CaseDetailDto

    @DELETE("api/cases/{caseId}")
    suspend fun deleteCase(
        @Path("caseId") caseId: Int
    ): Map<String, String>

    @GET("api/analysis/compare")
    suspend fun compareAnalyses(
        @Query("id1") id1: Int,
        @Query("id2") id2: Int
    ): ComparisonResponseDto

    @GET("api/sessions")
    suspend fun getActiveSessions(): List<SessionInfoDto>

    @DELETE("api/sessions/{sessionId}")
    suspend fun revokeSession(
        @Path("sessionId") sessionId: Int
    ): Map<String, String>

    @DELETE("api/sessions/revoke-others")
    suspend fun revokeOtherSessions(): Map<String, String>
}
