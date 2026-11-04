package com.example.deepguard.ui.screens.analyze

import android.graphics.Bitmap
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Error
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Slider
import androidx.compose.material3.SliderDefaults
import androidx.compose.material3.Tab
import androidx.compose.material3.TabRow
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.deepguard.network.AnalysisDetailOut
import com.example.deepguard.presentation.AnalysisState
import com.example.deepguard.presentation.AnalysisViewModel
import com.example.deepguard.presentation.HeatmapState
import com.example.deepguard.ui.components.DeepGuardButton
import com.example.deepguard.ui.theme.ErrorColor
import com.example.deepguard.ui.theme.PrimaryBlue
import com.example.deepguard.ui.theme.SuccessGreen
import com.example.deepguard.ui.theme.WarningYellow
import com.example.deepguard.utils.FileUtil

@Composable
fun ResultScreen(
    analysisId: Int,
    initialData: AnalysisDetailOut? = null,
    viewModel: AnalysisViewModel,
    onNavigateBack: () -> Unit
) {
    val state by viewModel.state.collectAsState()
    val heatmapState by viewModel.heatmapState.collectAsState()
    var selectedTab by remember { mutableIntStateOf(0) } // 0: Overview, 1: Grad-CAM Heatmap, 2: Indicators

    var currentDetail by remember { mutableStateOf(initialData) }

    LaunchedEffect(analysisId) {
        if (initialData == null || initialData.id != analysisId) {
            viewModel.fetchAnalysisDetail(analysisId)
        }
    }

    LaunchedEffect(state) {
        if (state is AnalysisState.Success) {
            currentDetail = (state as AnalysisState.Success).result
        }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background)
    ) {
        // Top App Bar
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp, vertical = 12.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            IconButton(onClick = onNavigateBack) {
                Icon(
                    imageVector = Icons.Default.ArrowBack,
                    contentDescription = "Back",
                    tint = MaterialTheme.colorScheme.onBackground
                )
            }
            Text(
                text = "Scan Audit: #${currentDetail?.id ?: analysisId}",
                style = MaterialTheme.typography.titleLarge,
                fontWeight = FontWeight.Bold,
                color = MaterialTheme.colorScheme.onBackground,
                modifier = Modifier.weight(1f)
            )
            IconButton(onClick = { viewModel.fetchAnalysisDetail(analysisId) }) {
                Icon(
                    imageVector = Icons.Default.Refresh,
                    contentDescription = "Refresh",
                    tint = MaterialTheme.colorScheme.primary
                )
            }
        }

        if (state is AnalysisState.Processing && currentDetail == null) {
            Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    CircularProgressIndicator(color = MaterialTheme.colorScheme.primary)
                    Spacer(modifier = Modifier.height(16.dp))
                    Text(
                        text = "Loading analysis record from DeepGuard backend...",
                        color = MaterialTheme.colorScheme.onSurface
                    )
                }
            }
            return
        }

        if (state is AnalysisState.Error && currentDetail == null) {
            Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                Column(
                    horizontalAlignment = Alignment.CenterHorizontally,
                    modifier = Modifier.padding(24.dp)
                ) {
                    Icon(
                        imageVector = Icons.Default.Error,
                        contentDescription = null,
                        tint = ErrorColor,
                        modifier = Modifier.size(48.dp)
                    )
                    Spacer(modifier = Modifier.height(16.dp))
                    Text(
                        text = (state as AnalysisState.Error).message,
                        color = ErrorColor,
                        textAlign = TextAlign.Center
                    )
                    Spacer(modifier = Modifier.height(16.dp))
                    DeepGuardButton(
                        text = "Retry",
                        onClick = { viewModel.fetchAnalysisDetail(analysisId) }
                    )
                }
            }
            return
        }

        val detail = currentDetail
        if (detail == null) {
            Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                Text("Analysis record not found.", color = MaterialTheme.colorScheme.onSurface)
            }
            return
        }

        if (detail.status.equals("failed", ignoreCase = true)) {
            Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                Column(
                    horizontalAlignment = Alignment.CenterHorizontally,
                    modifier = Modifier.padding(24.dp)
                ) {
                    Icon(
                        imageVector = Icons.Default.Warning,
                        contentDescription = null,
                        tint = WarningYellow,
                        modifier = Modifier.size(48.dp)
                    )
                    Spacer(modifier = Modifier.height(16.dp))
                    Text(
                        text = "Analysis Processing Failed",
                        style = MaterialTheme.typography.titleLarge,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.onSurface,
                        textAlign = TextAlign.Center
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(
                        text = detail.errorMessage ?: "The analysis pipeline encountered an error.",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f),
                        textAlign = TextAlign.Center
                    )
                    Spacer(modifier = Modifier.height(24.dp))
                    DeepGuardButton(
                        text = "Return to Analyses",
                        onClick = onNavigateBack
                    )
                }
            }
            return
        }

        var selectedTab by remember { mutableIntStateOf(0) }
        
        // Tab Navigation
        TabRow(
            selectedTabIndex = selectedTab,
            containerColor = MaterialTheme.colorScheme.surface,
            contentColor = MaterialTheme.colorScheme.primary
        ) {
            Tab(
                selected = selectedTab == 0,
                onClick = { selectedTab = 0 },
                text = { Text("Overview", fontWeight = FontWeight.SemiBold) }
            )
            if (!detail.mediaType.equals("audio", ignoreCase = true)) {
                Tab(
                    selected = selectedTab == 1,
                    onClick = {
                        selectedTab = 1
                        if (heatmapState !is HeatmapState.Success && heatmapState !is HeatmapState.Loading) {
                            viewModel.loadHeatmap(detail.id)
                        }
                    },
                    text = { Text("Grad-CAM Heatmap", fontWeight = FontWeight.SemiBold) }
                )
            }
            Tab(
                selected = selectedTab == 2,
                onClick = { selectedTab = 2 },
                text = { Text("Indicators (${detail.indicators.size})", fontWeight = FontWeight.SemiBold) }
            )
        }

        when (selectedTab) {
            0 -> OverviewTab(detail = detail)
            1 -> HeatmapTab(
                analysisId = detail.id,
                mediaType = detail.mediaType,
                heatmapState = heatmapState,
                onSelectFrame = { frameIdx -> viewModel.loadHeatmap(detail.id, frame = frameIdx) },
                onRetry = { viewModel.loadHeatmap(detail.id) }
            )
            2 -> IndicatorsTab(indicators = detail.indicators)
        }
    }
}

@Composable
fun OverviewTab(detail: AnalysisDetailOut) {
    val result = detail.result
    val prediction = result?.prediction?.lowercase() ?: "unknown"
    val confidence = result?.confidence ?: 0.0

    val isAuthentic = prediction == "authentic" || prediction == "real"
    val isSynthetic = prediction == "synthetic" || prediction == "fake"

    val predColor = when {
        isAuthentic -> SuccessGreen
        isSynthetic -> ErrorColor
        else -> WarningYellow
    }

    val realProb = if (isAuthentic) confidence else (1.0 - confidence)
    val fakeProb = if (isSynthetic) confidence else (1.0 - confidence)

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp)
    ) {
        // Main Prediction Card
        Card(
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(16.dp),
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
        ) {
            Column(
                modifier = Modifier.padding(20.dp),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.Center
                ) {
                    Icon(
                        imageVector = if (isAuthentic) Icons.Default.CheckCircle else Icons.Default.Warning,
                        contentDescription = null,
                        tint = predColor,
                        modifier = Modifier.size(28.dp)
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        text = if (isAuthentic) "AUTHENTIC (REAL)" else if (isSynthetic) "SYNTHETIC (FAKE)" else "UNCERTAIN",
                        style = MaterialTheme.typography.headlineMedium,
                        fontWeight = FontWeight.Black,
                        color = predColor
                    )
                }

                Spacer(modifier = Modifier.height(12.dp))

                Text(
                    text = "Confidence: ${"%.2f".format(confidence * 100)}%",
                    style = MaterialTheme.typography.titleLarge,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.onSurface
                )

                Spacer(modifier = Modifier.height(16.dp))

                // Real vs Fake Probabilities
                Column(modifier = Modifier.fillMaxWidth()) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        Text("Authentic Probability", style = MaterialTheme.typography.bodySmall, color = SuccessGreen)
                        Text("${"%.2f".format(realProb * 100)}%", style = MaterialTheme.typography.bodySmall, fontWeight = FontWeight.Bold, color = SuccessGreen)
                    }
                    LinearProgressIndicator(
                        progress = realProb.toFloat().coerceIn(0f, 1f),
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(8.dp)
                            .clip(RoundedCornerShape(4.dp)),
                        color = SuccessGreen,
                        trackColor = SuccessGreen.copy(alpha = 0.2f)
                    )

                    Spacer(modifier = Modifier.height(10.dp))

                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        Text("Synthetic / Deepfake Probability", style = MaterialTheme.typography.bodySmall, color = ErrorColor)
                        Text("${"%.2f".format(fakeProb * 100)}%", style = MaterialTheme.typography.bodySmall, fontWeight = FontWeight.Bold, color = ErrorColor)
                    }
                    LinearProgressIndicator(
                        progress = fakeProb.toFloat().coerceIn(0f, 1f),
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(8.dp)
                            .clip(RoundedCornerShape(4.dp)),
                        color = ErrorColor,
                        trackColor = ErrorColor.copy(alpha = 0.2f)
                    )
                }
            }
        }

        Spacer(modifier = Modifier.height(16.dp))

        // Technical Metadata Card
        Card(
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(16.dp),
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
        ) {
            Column(modifier = Modifier.padding(16.dp)) {
                Text(
                    text = "Inference & Model Metadata",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.onSurface
                )
                Spacer(modifier = Modifier.height(12.dp))

                MetaRow("Model Name", result?.modelName ?: "EfficientNet-B0")
                MetaRow("Risk Level", (result?.riskLevel ?: "low").uppercase())
                MetaRow("Media Type", detail.mediaType.uppercase())
                MetaRow("Filename", detail.originalFilename)
                MetaRow("Processing Time", "${"%.3f".format(detail.processingTime ?: 0.0)}s")
                if (result?.faceManipulationScore != null) {
                    MetaRow("Face Manipulation Score", "${"%.4f".format(result.faceManipulationScore)}")
                }
                if (result?.ganArtifactScore != null) {
                    MetaRow("GAN Artifact Score", "${"%.4f".format(result.ganArtifactScore)}")
                }
                if (result?.temporalInconsistencyScore != null) {
                    MetaRow("Temporal Inconsistency Score", "${"%.4f".format(result.temporalInconsistencyScore)}")
                }
                if (result?.voiceCloningScore != null) {
                    MetaRow("Voice Cloning Score", "${"%.4f".format(result.voiceCloningScore)}")
                }
                if (result?.spectralAnomalyScore != null) {
                    MetaRow("Spectral Anomaly Score", "${"%.4f".format(result.spectralAnomalyScore)}")
                }
                if (detail.durationSeconds != null) {
                    MetaRow("Audio Duration", "${"%.2f".format(detail.durationSeconds)}s")
                }
                MetaRow("Timestamp", detail.createdAt)
            }
        }

        if (detail.mediaType.equals("audio", ignoreCase = true)) {
            Spacer(modifier = Modifier.height(16.dp))

            // Audio Forensic Breakdown Card
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(16.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text(
                        text = "Acoustic & Voice Cloning Breakdown",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.onSurface
                    )
                    Spacer(modifier = Modifier.height(12.dp))

                    val vcScore = result?.voiceCloningScore ?: 0.0
                    val saScore = result?.spectralAnomalyScore ?: 0.0

                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        Text("Voice Cloning / Synthesis Risk", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.8f))
                        Text("${"%.1f".format(vcScore * 100)}%", style = MaterialTheme.typography.bodySmall, fontWeight = FontWeight.Bold, color = if (vcScore > 0.6) ErrorColor else SuccessGreen)
                    }
                    LinearProgressIndicator(
                        progress = vcScore.toFloat().coerceIn(0f, 1f),
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(6.dp)
                            .clip(RoundedCornerShape(3.dp)),
                        color = if (vcScore > 0.6) ErrorColor else SuccessGreen,
                        trackColor = MaterialTheme.colorScheme.surfaceVariant
                    )

                    Spacer(modifier = Modifier.height(12.dp))

                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        Text("Spectral Anomaly Index", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.8f))
                        Text("${"%.1f".format(saScore * 100)}%", style = MaterialTheme.typography.bodySmall, fontWeight = FontWeight.Bold, color = if (saScore > 0.6) ErrorColor else SuccessGreen)
                    }
                    LinearProgressIndicator(
                        progress = saScore.toFloat().coerceIn(0f, 1f),
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(6.dp)
                            .clip(RoundedCornerShape(3.dp)),
                        color = if (saScore > 0.6) ErrorColor else SuccessGreen,
                        trackColor = MaterialTheme.colorScheme.surfaceVariant
                    )
                }
            }

            Spacer(modifier = Modifier.height(16.dp))

            // Forensic Disclaimer Card
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(12.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.primary.copy(alpha = 0.08f))
            ) {
                Row(modifier = Modifier.padding(14.dp), verticalAlignment = Alignment.Top) {
                    Icon(
                        imageVector = Icons.Default.Info,
                        contentDescription = null,
                        tint = MaterialTheme.colorScheme.primary,
                        modifier = Modifier.size(18.dp)
                    )
                    Spacer(modifier = Modifier.width(10.dp))
                    Text(
                        text = "Detection Scope: AASIST evaluates acoustic synthesis and neural vocoder artifacts. It distinguishes between synthetic/cloned speech and organic human speech, but does NOT perform speaker biometric verification to prove identity.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.75f),
                        lineHeight = 17.sp
                    )
                }
            }
        }
    }
}

@Composable
fun HeatmapTab(
    analysisId: Int,
    mediaType: String,
    heatmapState: HeatmapState,
    onSelectFrame: (Int) -> Unit = {},
    onRetry: () -> Unit
) {
    var viewMode by remember { mutableStateOf("overlay") } // "overlay", "heatmap", "original"
    var overlayOpacity by remember { mutableFloatStateOf(0.6f) }
    var selectedFrame by remember { mutableIntStateOf(0) }

    if (mediaType.equals("audio", ignoreCase = true)) {
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(24.dp),
            contentAlignment = Alignment.Center
        ) {
            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                Icon(
                    imageVector = Icons.Default.Info,
                    contentDescription = null,
                    tint = WarningYellow,
                    modifier = Modifier.size(40.dp)
                )
                Spacer(modifier = Modifier.height(12.dp))
                Text(
                    text = "Grad-CAM explainability heatmap is unavailable for audio files.",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurface,
                    textAlign = TextAlign.Center
                )
            }
        }
        return
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        // Video Keyframe Selector (if video)
        if (mediaType.equals("video", ignoreCase = true)) {
            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(bottom = 16.dp),
                shape = RoundedCornerShape(14.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
            ) {
                Column(modifier = Modifier.padding(14.dp)) {
                    Text(
                        text = "Video Keyframes (5 Sampled Frames)",
                        style = MaterialTheme.typography.titleSmall,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.onSurface
                    )
                    Spacer(modifier = Modifier.height(10.dp))
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(6.dp)
                    ) {
                        listOf(0, 1, 2, 3, 4).forEach { fIndex ->
                            val isSelected = selectedFrame == fIndex
                            Card(
                                modifier = Modifier
                                    .weight(1f)
                                    .clickable {
                                        selectedFrame = fIndex
                                        onSelectFrame(fIndex)
                                    },
                                shape = RoundedCornerShape(8.dp),
                                colors = CardDefaults.cardColors(
                                    containerColor = if (isSelected) MaterialTheme.colorScheme.primary.copy(alpha = 0.25f)
                                                     else MaterialTheme.colorScheme.background
                                )
                            ) {
                                Column(
                                    modifier = Modifier.padding(vertical = 8.dp),
                                    horizontalAlignment = Alignment.CenterHorizontally
                                ) {
                                    Text(
                                        text = "#${fIndex + 1}",
                                        style = MaterialTheme.typography.bodySmall,
                                        fontWeight = FontWeight.Bold,
                                        color = if (isSelected) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurface
                                    )
                                    Text(
                                        text = "${"%.1f".format(fIndex * 0.6)}s",
                                        style = MaterialTheme.typography.bodySmall,
                                        fontSize = 10.sp,
                                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f)
                                    )
                                }
                            }
                        }
                    }
                }
            }
        }

        when (heatmapState) {
            is HeatmapState.Idle, is HeatmapState.Loading -> {
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(300.dp),
                    contentAlignment = Alignment.Center
                ) {
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        CircularProgressIndicator(color = MaterialTheme.colorScheme.primary)
                        Spacer(modifier = Modifier.height(12.dp))
                        Text("Retrieving Grad-CAM Heatmap from FastAPI...", color = MaterialTheme.colorScheme.onSurface)
                    }
                }
            }
            is HeatmapState.Error -> {
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(260.dp),
                    contentAlignment = Alignment.Center
                ) {
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Text(text = heatmapState.message, color = ErrorColor, textAlign = TextAlign.Center)
                        Spacer(modifier = Modifier.height(12.dp))
                        DeepGuardButton(text = "Retry Heatmap", onClick = onRetry)
                    }
                }
            }
            is HeatmapState.Success -> {
                // Mode selector buttons
                val modes = if (mediaType.equals("video", ignoreCase = true)) {
                    listOf("overlay" to "Overlay Blend", "original" to "Original Keyframe")
                } else {
                    listOf("overlay" to "Overlay Blend", "heatmap" to "Heatmap Only", "original" to "Original Image")
                }

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceEvenly
                ) {
                    modes.forEach { (mode, label) ->
                        val isSelected = viewMode == mode
                        Card(
                            modifier = Modifier
                                .weight(1f)
                                .padding(horizontal = 4.dp)
                                .clickable { viewMode = mode },
                            shape = RoundedCornerShape(10.dp),
                            colors = CardDefaults.cardColors(
                                containerColor = if (isSelected) MaterialTheme.colorScheme.primary.copy(alpha = 0.2f)
                                                 else MaterialTheme.colorScheme.surface
                            )
                        ) {
                            Text(
                                text = label,
                                style = MaterialTheme.typography.bodySmall,
                                fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Normal,
                                color = if (isSelected) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurface,
                                modifier = Modifier
                                    .padding(vertical = 10.dp)
                                    .fillMaxWidth(),
                                textAlign = TextAlign.Center
                            )
                        }
                    }
                }

                Spacer(modifier = Modifier.height(12.dp))

                // Image Viewer Box
                val activeBytes = when (viewMode) {
                    "heatmap" -> heatmapState.heatmapBytes ?: heatmapState.overlayBytes
                    "original" -> heatmapState.originalBytes ?: heatmapState.overlayBytes
                    else -> heatmapState.overlayBytes
                }

                val bitmap = remember(activeBytes) { FileUtil.decodeBitmap(activeBytes) }

                Card(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(16.dp),
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
                ) {
                    if (bitmap != null) {
                        Image(
                            bitmap = bitmap.asImageBitmap(),
                            contentDescription = "Grad-CAM Visualization",
                            modifier = Modifier
                                .fillMaxWidth()
                                .height(280.dp)
                                .clip(RoundedCornerShape(16.dp)),
                            contentScale = ContentScale.Fit
                        )
                    } else {
                        Box(
                            modifier = Modifier
                                .fillMaxWidth()
                                .height(200.dp),
                            contentAlignment = Alignment.Center
                        ) {
                            Text("Heatmap visualization image rendered.", color = MaterialTheme.colorScheme.onSurface)
                        }
                    }
                }

                if (viewMode == "overlay") {
                    Spacer(modifier = Modifier.height(12.dp))
                    Text(
                        text = "Heatmap Opacity: ${"%.0f".format(overlayOpacity * 100)}%",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurface
                    )
                    Slider(
                        value = overlayOpacity,
                        onValueChange = { overlayOpacity = it },
                        valueRange = 0.1f..1.0f,
                        colors = SliderDefaults.colors(
                            thumbColor = MaterialTheme.colorScheme.primary,
                            activeTrackColor = MaterialTheme.colorScheme.primary
                        )
                    )
                }

                Spacer(modifier = Modifier.height(16.dp))

                // Explainability Disclaimer Card
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(12.dp),
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface.copy(alpha = 0.5f))
                ) {
                    Row(
                        modifier = Modifier.padding(14.dp),
                        verticalAlignment = Alignment.Top
                    ) {
                        Icon(
                            imageVector = Icons.Default.Info,
                            contentDescription = null,
                            tint = WarningYellow,
                            modifier = Modifier.size(20.dp)
                        )
                        Spacer(modifier = Modifier.width(10.dp))
                        Text(
                            text = "Grad-CAM highlights regions that influenced the model prediction. It is not a ground-truth manipulation mask.",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.8f),
                            lineHeight = 18.sp
                        )
                    }
                }
            }
        }
    }
}

@Composable
fun IndicatorsTab(indicators: List<com.example.deepguard.network.AnalysisIndicatorOut>) {
    if (indicators.isEmpty()) {
        Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            Text(text = "No forensic anomalies detected in media.", color = MaterialTheme.colorScheme.onSurface)
        }
    } else {
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(16.dp)
        ) {
            items(indicators) { indicator ->
                Card(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(vertical = 6.dp),
                    shape = RoundedCornerShape(12.dp),
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
                ) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text(
                                text = indicator.indicatorType.replace("_", " ").uppercase(),
                                fontWeight = FontWeight.Bold,
                                style = MaterialTheme.typography.bodyMedium,
                                color = MaterialTheme.colorScheme.onSurface
                            )
                            val sevColor = when (indicator.severity.lowercase()) {
                                "critical", "high" -> ErrorColor
                                "medium" -> WarningYellow
                                else -> PrimaryBlue
                            }
                            Text(
                                text = indicator.severity.uppercase(),
                                color = sevColor,
                                fontWeight = FontWeight.Bold,
                                style = MaterialTheme.typography.bodySmall
                            )
                        }
                        Spacer(modifier = Modifier.height(6.dp))
                        Text(
                            text = indicator.description,
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f)
                        )
                    }
                }
            }
        }
    }
}

@Composable
fun MetaRow(label: String, value: String) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 4.dp),
        horizontalArrangement = Arrangement.SpaceBetween
    ) {
        Text(text = label, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f))
        Text(text = value, style = MaterialTheme.typography.bodySmall, fontWeight = FontWeight.SemiBold, color = MaterialTheme.colorScheme.onSurface)
    }
}
