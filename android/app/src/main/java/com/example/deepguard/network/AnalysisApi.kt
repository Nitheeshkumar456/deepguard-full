package com.example.deepguard.network

import okhttp3.MultipartBody
import okhttp3.ResponseBody
import retrofit2.Response
import retrofit2.http.DELETE
import retrofit2.http.GET
import retrofit2.http.Multipart
import retrofit2.http.POST
import retrofit2.http.Part
import retrofit2.http.Path
import retrofit2.http.Query

interface AnalysisApi {

    @Multipart
    @POST("api/analysis/image")
    suspend fun uploadImage(
        @Part file: MultipartBody.Part
    ): Response<AnalysisSubmitResponse>

    @Multipart
    @POST("api/analysis/video")
    suspend fun uploadVideo(
        @Part file: MultipartBody.Part
    ): Response<AnalysisSubmitResponse>

    @Multipart
    @POST("api/analysis/audio")
    suspend fun uploadAudio(
        @Part file: MultipartBody.Part
    ): Response<AnalysisSubmitResponse>

    @GET("api/analysis/history")
    suspend fun getHistory(
        @Query("page") page: Int = 1,
        @Query("page_size") pageSize: Int = 20,
        @Query("media_type") mediaType: String? = null,
        @Query("status") status: String? = null
    ): Response<AnalysisHistoryOut>

    @GET("api/analysis/{analysis_id}")
    suspend fun getAnalysisDetail(
        @Path("analysis_id") analysisId: Int
    ): Response<AnalysisDetailOut>

    @GET("api/analysis/{analysis_id}/heatmap")
    suspend fun getHeatmap(
        @Path("analysis_id") analysisId: Int,
        @Query("type") type: String = "overlay",
        @Query("frame") frame: Int? = null
    ): Response<ResponseBody>

    @GET("api/analysis/{analysis_id}/media")
    suspend fun getOriginalMedia(
        @Path("analysis_id") analysisId: Int,
        @Query("frame") frame: Int? = null
    ): Response<ResponseBody>

    @DELETE("api/analysis/{analysis_id}")
    suspend fun deleteAnalysis(
        @Path("analysis_id") analysisId: Int
    ): Response<MsgResponse>
}
