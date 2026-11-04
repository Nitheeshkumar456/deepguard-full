package com.example.deepguard.presentation

import com.example.deepguard.data.AnalysisRepository
import com.example.deepguard.network.AnalysisApi
import com.example.deepguard.network.AnalysisDetailOut
import com.example.deepguard.network.AnalysisHistoryOut
import com.example.deepguard.network.AnalysisSubmitResponse
import com.example.deepguard.network.AnalysisSummaryOut
import com.example.deepguard.network.MsgResponse
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import okhttp3.MultipartBody
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import retrofit2.Response

@OptIn(ExperimentalCoroutinesApi::class)
class HistoryViewModelTest {

    private val testDispatcher = StandardTestDispatcher()

    @Before
    fun setUp() {
        Dispatchers.setMain(testDispatcher)
    }

    @After
    fun tearDown() {
        Dispatchers.resetMain()
    }

    @Test
    fun testFetchHistorySuccess() = runTest {
        val fakeApi = FakeHistoryAnalysisApi()
        val repo = AnalysisRepository(fakeApi)
        val viewModel = HistoryViewModel(repo)

        viewModel.fetchHistory()
        advanceUntilIdle()

        assertTrue(viewModel.state.value is HistoryState.Success)
        val successState = viewModel.state.value as HistoryState.Success
        assertEquals(2, successState.items.size)
        assertEquals("test1.jpg", successState.items[0].originalFilename)
        assertEquals("synthetic", successState.items[0].prediction)
    }

    @Test
    fun testDeleteHistoryItemRefetches() = runTest {
        val fakeApi = FakeHistoryAnalysisApi()
        val repo = AnalysisRepository(fakeApi)
        val viewModel = HistoryViewModel(repo)

        viewModel.deleteHistoryItem(1)
        advanceUntilIdle()

        assertTrue(viewModel.state.value is HistoryState.Success)
    }
}

private class FakeHistoryAnalysisApi : AnalysisApi {
    override suspend fun uploadImage(file: MultipartBody.Part): Response<AnalysisSubmitResponse> {
        throw UnsupportedOperationException()
    }

    override suspend fun uploadVideo(file: MultipartBody.Part): Response<AnalysisSubmitResponse> {
        throw UnsupportedOperationException()
    }

    override suspend fun uploadAudio(file: MultipartBody.Part): Response<AnalysisSubmitResponse> {
        throw UnsupportedOperationException()
    }

    override suspend fun getHistory(page: Int, pageSize: Int, mediaType: String?, status: String?): Response<AnalysisHistoryOut> {
        return Response.success(
            AnalysisHistoryOut(
                items = listOf(
                    AnalysisSummaryOut(
                        id = 1,
                        mediaType = "image",
                        originalFilename = "test1.jpg",
                        fileSize = 2048L,
                        status = "completed",
                        createdAt = "2026-08-27T12:00:00Z",
                        completedAt = "2026-08-27T12:00:01Z",
                        processingTime = 0.32,
                        prediction = "synthetic",
                        confidence = 0.92,
                        riskLevel = "high"
                    ),
                    AnalysisSummaryOut(
                        id = 2,
                        mediaType = "video",
                        originalFilename = "test2.mp4",
                        fileSize = 1048576L,
                        status = "completed",
                        createdAt = "2026-08-27T12:01:00Z",
                        completedAt = "2026-08-27T12:01:05Z",
                        processingTime = 3.2,
                        prediction = "authentic",
                        confidence = 0.88,
                        riskLevel = "low"
                    )
                ),
                total = 2,
                page = page,
                pageSize = pageSize,
                pages = 1
            )
        )
    }

    override suspend fun getAnalysisDetail(analysisId: Int): Response<AnalysisDetailOut> {
        throw UnsupportedOperationException()
    }

    override suspend fun getHeatmap(analysisId: Int, type: String, frame: Int?): Response<okhttp3.ResponseBody> {
        throw UnsupportedOperationException()
    }

    override suspend fun getOriginalMedia(analysisId: Int, frame: Int?): Response<okhttp3.ResponseBody> {
        throw UnsupportedOperationException()
    }

    override suspend fun deleteAnalysis(analysisId: Int): Response<MsgResponse> {
        return Response.success(MsgResponse("Deleted"))
    }
}
