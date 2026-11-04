package com.example.deepguard.presentation

import com.example.deepguard.data.AnalysisRepository
import com.example.deepguard.network.AnalysisApi
import com.example.deepguard.network.AnalysisDetailOut
import com.example.deepguard.network.AnalysisHistoryOut
import com.example.deepguard.network.AnalysisResultOut
import com.example.deepguard.network.AnalysisSubmitResponse
import com.example.deepguard.network.MsgResponse
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import okhttp3.MultipartBody
import com.example.deepguard.presentation.HeatmapState
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.ResponseBody
import okhttp3.ResponseBody.Companion.toResponseBody
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import retrofit2.Response
import java.io.File

@OptIn(ExperimentalCoroutinesApi::class)
class AnalysisViewModelTest {

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
    fun testInitialStateIsIdle() {
        val fakeApi = FakeAnalysisApi()
        val repo = AnalysisRepository(fakeApi)
        val viewModel = AnalysisViewModel(repo)

        assertEquals(AnalysisState.Idle, viewModel.state.value)
        assertEquals(HeatmapState.Idle, viewModel.heatmapState.value)
    }

    @Test
    fun testUploadAndAnalyzeSuccess() = runTest {
        val fakeApi = FakeAnalysisApi()
        val repo = AnalysisRepository(fakeApi)
        val viewModel = AnalysisViewModel(repo)

        val tempFile = File.createTempFile("test_upload", ".jpg")
        try {
            tempFile.writeText("fake image bytes")
            viewModel.uploadAndAnalyze(tempFile, "image")
            advanceUntilIdle()

            assertTrue(viewModel.state.value is AnalysisState.Success)
            val successState = viewModel.state.value as AnalysisState.Success
            assertEquals(101, successState.result.id)
            assertEquals("completed", successState.result.status)
            assertEquals("authentic", successState.result.result?.prediction)
        } finally {
            tempFile.delete()
        }
    }

    @Test
    fun testUploadInvalidExtensionRejected() = runTest {
        val fakeApi = FakeAnalysisApi()
        val repo = AnalysisRepository(fakeApi)
        val viewModel = AnalysisViewModel(repo)

        val tempFile = File.createTempFile("invalid_file", ".txt")
        try {
            tempFile.writeText("some text")
            viewModel.uploadAndAnalyze(tempFile, "image")
            advanceUntilIdle()

            assertTrue(viewModel.state.value is AnalysisState.Error)
            val errState = viewModel.state.value as AnalysisState.Error
            assertTrue(errState.message.contains("Unsupported file type"))
        } finally {
            tempFile.delete()
        }
    }

    @Test
    fun testFetchAnalysisDetailSuccess() = runTest {
        val fakeApi = FakeAnalysisApi()
        val repo = AnalysisRepository(fakeApi)
        val viewModel = AnalysisViewModel(repo)

        viewModel.fetchAnalysisDetail(101)
        advanceUntilIdle()

        assertTrue(viewModel.state.value is AnalysisState.Success)
        val detail = (viewModel.state.value as AnalysisState.Success).result
        assertEquals(101, detail.id)
        assertEquals("authentic", detail.result?.prediction)
    }

    @Test
    fun testLoadHeatmapSuccess() = runTest {
        val fakeApi = FakeAnalysisApi()
        val repo = AnalysisRepository(fakeApi)
        val viewModel = AnalysisViewModel(repo)

        viewModel.loadHeatmap(101)
        advanceUntilIdle()

        assertTrue(viewModel.heatmapState.value is HeatmapState.Success)
        val heatmapSuccess = viewModel.heatmapState.value as HeatmapState.Success
        assertTrue(heatmapSuccess.overlayBytes.isNotEmpty())
    }

    @Test
    fun testVideoUploadAndAnalyzeSuccessWithPolling() = runTest {
        val fakeApi = FakeAnalysisApi(videoStatus = "queued")
        val repo = AnalysisRepository(fakeApi)
        val viewModel = AnalysisViewModel(repo)

        val tempFile = File.createTempFile("test_upload", ".mp4")
        try {
            tempFile.writeText("fake video bytes")
            viewModel.uploadAndAnalyze(tempFile, "video")
            advanceUntilIdle()

            assertTrue(viewModel.state.value is AnalysisState.Success)
            val successState = viewModel.state.value as AnalysisState.Success
            assertEquals(102, successState.result.id)
            assertEquals("completed", successState.result.status)
        } finally {
            tempFile.delete()
        }
    }

    @Test
    fun testVideoUploadInvalidExtensionRejected() = runTest {
        val fakeApi = FakeAnalysisApi()
        val repo = AnalysisRepository(fakeApi)
        val viewModel = AnalysisViewModel(repo)

        val tempFile = File.createTempFile("invalid_video", ".exe")
        try {
            tempFile.writeText("binary data")
            viewModel.uploadAndAnalyze(tempFile, "video")
            advanceUntilIdle()

            assertTrue(viewModel.state.value is AnalysisState.Error)
            val errState = viewModel.state.value as AnalysisState.Error
            assertTrue(errState.message.contains("Unsupported file type"))
        } finally {
            tempFile.delete()
        }
    }

    @Test
    fun testVideoKeyframeHeatmapSuccess() = runTest {
        val fakeApi = FakeAnalysisApi()
        val repo = AnalysisRepository(fakeApi)
        val viewModel = AnalysisViewModel(repo)

        viewModel.loadHeatmap(102, frame = 3)
        advanceUntilIdle()

        assertTrue(viewModel.heatmapState.value is HeatmapState.Success)
        val heatmapSuccess = viewModel.heatmapState.value as HeatmapState.Success
        assertTrue(heatmapSuccess.overlayBytes.isNotEmpty())
    }

    @Test
    fun testAudioUploadModelUnavailablePropagated() = runTest {
        val fakeApi = FakeAnalysisApi(audioStatus = "failed", audioError = "Audio analysis model is unavailable. No trained audio deepfake detection model is installed on the system.")
        val repo = AnalysisRepository(fakeApi)
        val viewModel = AnalysisViewModel(repo)

        val tempFile = File.createTempFile("test_audio", ".mp3")
        try {
            tempFile.writeText("fake audio data")
            viewModel.uploadAndAnalyze(tempFile, "audio")
            advanceUntilIdle()

            assertTrue(viewModel.state.value is AnalysisState.Error)
            val errState = viewModel.state.value as AnalysisState.Error
            assertTrue(errState.message.contains("Audio analysis model is unavailable"))
        } finally {
            tempFile.delete()
        }
    }

    @Test
    fun testAudioUploadInvalidExtensionRejected() = runTest {
        val fakeApi = FakeAnalysisApi()
        val repo = AnalysisRepository(fakeApi)
        val viewModel = AnalysisViewModel(repo)

        val tempFile = File.createTempFile("invalid_audio", ".zip")
        try {
            tempFile.writeText("zip data")
            viewModel.uploadAndAnalyze(tempFile, "audio")
            advanceUntilIdle()

            assertTrue(viewModel.state.value is AnalysisState.Error)
            val errState = viewModel.state.value as AnalysisState.Error
            assertTrue(errState.message.contains("Unsupported file type"))
        } finally {
            tempFile.delete()
        }
    }

    @Test
    fun testResetState() = runTest {
        val fakeApi = FakeAnalysisApi()
        val repo = AnalysisRepository(fakeApi)
        val viewModel = AnalysisViewModel(repo)

        val tempFile = File.createTempFile("test_upload", ".jpg")
        try {
            tempFile.writeText("fake image bytes")
            viewModel.uploadAndAnalyze(tempFile, "image")
            advanceUntilIdle()
            viewModel.resetState()

            assertEquals(AnalysisState.Idle, viewModel.state.value)
            assertEquals(HeatmapState.Idle, viewModel.heatmapState.value)
        } finally {
            tempFile.delete()
        }
    }
}

private class FakeAnalysisApi(
    private val videoStatus: String = "completed",
    private val audioStatus: String = "completed",
    private val audioError: String? = null
) : AnalysisApi {
    override suspend fun uploadImage(file: MultipartBody.Part): Response<AnalysisSubmitResponse> {
        return Response.success(
            AnalysisSubmitResponse(
                analysisId = 101,
                status = "completed",
                message = "Image processed",
                mediaType = "image",
                originalFilename = "test_upload.jpg",
                fileSize = 1024L
            )
        )
    }

    override suspend fun uploadVideo(file: MultipartBody.Part): Response<AnalysisSubmitResponse> {
        return Response.success(
            AnalysisSubmitResponse(
                analysisId = 102,
                status = videoStatus,
                message = "Video accepted",
                mediaType = "video",
                originalFilename = "test_upload.mp4",
                fileSize = 2048L
            )
        )
    }

    override suspend fun uploadAudio(file: MultipartBody.Part): Response<AnalysisSubmitResponse> {
        return Response.success(
            AnalysisSubmitResponse(
                analysisId = 103,
                status = audioStatus,
                message = audioError ?: "Audio processed",
                mediaType = "audio",
                originalFilename = "test_upload.wav",
                fileSize = 512L
            )
        )
    }

    override suspend fun getHistory(page: Int, pageSize: Int, mediaType: String?, status: String?): Response<AnalysisHistoryOut> {
        return Response.success(
            AnalysisHistoryOut(
                items = emptyList(),
                total = 0,
                page = page,
                pageSize = pageSize,
                pages = 1
            )
        )
    }

    override suspend fun getAnalysisDetail(analysisId: Int): Response<AnalysisDetailOut> {
        return Response.success(
            AnalysisDetailOut(
                id = analysisId,
                userId = 1,
                mediaType = "image",
                originalFilename = "test_upload.jpg",
                fileSize = 1024L,
                mimeType = "image/jpeg",
                durationSeconds = null,
                width = 512,
                height = 512,
                status = "completed",
                errorMessage = null,
                processingTime = 0.25,
                createdAt = "2026-08-27T12:00:00Z",
                completedAt = "2026-08-27T12:00:01Z",
                result = AnalysisResultOut(
                    id = 501,
                    prediction = "authentic",
                    confidence = 0.98,
                    riskLevel = "low",
                    modelName = "deepguard-cnn-v1",
                    modelVersion = "1.0.0",
                    faceManipulationScore = 0.02,
                    ganArtifactScore = 0.01,
                    temporalInconsistencyScore = null,
                    voiceCloningScore = null,
                    spectralAnomalyScore = null,
                    createdAt = "2026-08-27T12:00:01Z"
                ),
                indicators = emptyList()
            )
        )
    }

    override suspend fun getHeatmap(analysisId: Int, type: String, frame: Int?): Response<ResponseBody> {
        val dummyBytes = "fake-jpeg-bytes".toByteArray()
        return Response.success(dummyBytes.toResponseBody("image/jpeg".toMediaTypeOrNull()))
    }

    override suspend fun getOriginalMedia(analysisId: Int, frame: Int?): Response<ResponseBody> {
        val dummyBytes = "fake-original-bytes".toByteArray()
        return Response.success(dummyBytes.toResponseBody("image/jpeg".toMediaTypeOrNull()))
    }

    override suspend fun deleteAnalysis(analysisId: Int): Response<MsgResponse> {
        return Response.success(MsgResponse("Deleted"))
    }
}
