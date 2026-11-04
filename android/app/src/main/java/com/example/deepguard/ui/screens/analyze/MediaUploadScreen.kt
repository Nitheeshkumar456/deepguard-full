package com.example.deepguard.ui.screens.analyze

import android.graphics.Bitmap
import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
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
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Image
import androidx.compose.material.icons.filled.UploadFile
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.foundation.BorderStroke
import androidx.compose.material.icons.filled.Audiotrack
import androidx.compose.material.icons.filled.Info
import androidx.compose.ui.unit.sp
import com.example.deepguard.ui.theme.WarningYellow
import com.example.deepguard.network.AnalysisDetailOut
import com.example.deepguard.presentation.AnalysisState
import com.example.deepguard.presentation.AnalysisViewModel
import com.example.deepguard.ui.components.DeepGuardButton
import com.example.deepguard.ui.theme.ErrorColor
import com.example.deepguard.utils.FileUtil
import java.io.File

@Composable
fun MediaUploadScreen(
    mediaType: String,
    viewModel: AnalysisViewModel,
    onNavigateToResult: (AnalysisDetailOut) -> Unit
) {
    val context = LocalContext.current
    val state by viewModel.state.collectAsState()
    var selectedUri by remember { mutableStateOf<Uri?>(null) }
    var selectedFile by remember { mutableStateOf<File?>(null) }
    var previewBitmap by remember { mutableStateOf<Bitmap?>(null) }
    var localValidationError by remember { mutableStateOf<String?>(null) }

    val filePickerLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.GetContent()
    ) { uri: Uri? ->
        selectedUri = uri
        localValidationError = null
        if (uri != null) {
            val file = FileUtil.getFileFromUri(context, uri)
            selectedFile = file
            if (mediaType.equals("image", ignoreCase = true)) {
                previewBitmap = FileUtil.loadBitmap(context, uri)
                if (file != null) {
                    val valRes = FileUtil.validateImageFile(file)
                    if (valRes.isFailure) {
                        localValidationError = valRes.exceptionOrNull()?.message
                    }
                }
            } else if (mediaType.equals("video", ignoreCase = true)) {
                previewBitmap = FileUtil.loadVideoThumbnail(context, uri)
                if (file != null) {
                    val valRes = FileUtil.validateVideoFile(file)
                    if (valRes.isFailure) {
                        localValidationError = valRes.exceptionOrNull()?.message
                    }
                }
            } else if (mediaType.equals("audio", ignoreCase = true)) {
                previewBitmap = null
                if (file != null) {
                    val valRes = FileUtil.validateAudioFile(file)
                    if (valRes.isFailure) {
                        localValidationError = valRes.exceptionOrNull()?.message
                    }
                }
            } else {
                previewBitmap = null
            }
        } else {
            selectedFile = null
            previewBitmap = null
        }
    }

    LaunchedEffect(state) {
        if (state is AnalysisState.Success) {
            onNavigateToResult((state as AnalysisState.Success).result)
        }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background)
            .verticalScroll(rememberScrollState())
            .padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        Text(
            text = "Upload ${mediaType.replaceFirstChar { it.uppercase() }}",
            style = MaterialTheme.typography.headlineLarge,
            color = MaterialTheme.colorScheme.onBackground
        )

        Text(
            text = "Submit media for authentic vs synthetic AI verification",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f),
            modifier = Modifier.padding(top = 4.dp, bottom = 20.dp)
        )

        if (mediaType.equals("audio", ignoreCase = true)) {
            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(bottom = 20.dp),
                shape = RoundedCornerShape(12.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.primary.copy(alpha = 0.1f)),
                border = BorderStroke(1.dp, MaterialTheme.colorScheme.primary.copy(alpha = 0.3f))
            ) {
                Row(
                    modifier = Modifier.padding(14.dp),
                    verticalAlignment = Alignment.Top
                ) {
                    Icon(
                        imageVector = Icons.Default.Audiotrack,
                        contentDescription = null,
                        tint = MaterialTheme.colorScheme.primary,
                        modifier = Modifier.size(20.dp)
                    )
                    Spacer(modifier = Modifier.width(10.dp))
                    Text(
                        text = "AASIST Deepfake Audio Engine Active: Powered by Integrated Spectro-Temporal Graph Attention Networks trained on ASVspoof 2019 to detect synthetic speech, neural vocoder artifacts, and voice cloning.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurface,
                        lineHeight = 18.sp
                    )
                }
            }
        }

        when (state) {
            is AnalysisState.Idle, is AnalysisState.Error -> {
                if (state is AnalysisState.Error) {
                    Text(
                        text = (state as AnalysisState.Error).message,
                        color = ErrorColor,
                        style = MaterialTheme.typography.bodyMedium,
                        textAlign = TextAlign.Center,
                        modifier = Modifier.padding(bottom = 16.dp)
                    )
                }

                if (localValidationError != null) {
                    Text(
                        text = localValidationError!!,
                        color = ErrorColor,
                        style = MaterialTheme.typography.bodyMedium,
                        textAlign = TextAlign.Center,
                        modifier = Modifier.padding(bottom = 16.dp)
                    )
                }

                if (selectedFile != null && selectedUri != null) {
                    Card(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(bottom = 20.dp),
                        shape = RoundedCornerShape(16.dp),
                        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
                    ) {
                        Column(
                            modifier = Modifier.padding(16.dp),
                            horizontalAlignment = Alignment.CenterHorizontally
                        ) {
                            if (previewBitmap != null) {
                                Image(
                                    bitmap = previewBitmap!!.asImageBitmap(),
                                    contentDescription = "Selected Media Preview",
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .height(200.dp)
                                        .clip(RoundedCornerShape(12.dp))
                                        .background(MaterialTheme.colorScheme.background),
                                    contentScale = ContentScale.Crop
                                )
                                Spacer(modifier = Modifier.height(12.dp))
                            } else if (mediaType.equals("audio", ignoreCase = true)) {
                                Icon(
                                    imageVector = Icons.Default.Audiotrack,
                                    contentDescription = "Audio file",
                                    tint = MaterialTheme.colorScheme.primary,
                                    modifier = Modifier
                                        .size(64.dp)
                                        .padding(8.dp)
                                )
                                Spacer(modifier = Modifier.height(8.dp))
                            }

                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Column(modifier = Modifier.weight(1f)) {
                                    Text(
                                        text = selectedFile!!.name,
                                        style = MaterialTheme.typography.bodyMedium,
                                        fontWeight = FontWeight.Bold,
                                        color = MaterialTheme.colorScheme.onSurface
                                    )
                                    Text(
                                        text = FileUtil.formatFileSize(selectedFile!!.length()),
                                        style = MaterialTheme.typography.bodySmall,
                                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f)
                                    )
                                }
                                IconButton(
                                    onClick = {
                                        selectedUri = null
                                        selectedFile = null
                                        previewBitmap = null
                                        localValidationError = null
                                    }
                                ) {
                                    Icon(
                                        imageVector = Icons.Default.Close,
                                        contentDescription = "Remove file",
                                        tint = ErrorColor
                                    )
                                }
                            }
                        }
                    }

                    DeepGuardButton(
                        text = when (mediaType.lowercase()) {
                            "video" -> "Analyze Video Now"
                            "audio" -> "Analyze Audio Now"
                            else -> "Analyze Image Now"
                        },
                        onClick = {
                            if (localValidationError == null && selectedFile != null) {
                                viewModel.uploadAndAnalyze(selectedFile!!, mediaType)
                            }
                        }
                    )

                    Spacer(modifier = Modifier.height(12.dp))

                    OutlinedButton(
                        onClick = {
                            val mime = when (mediaType.lowercase()) {
                                "image" -> "image/*"
                                "video" -> "video/*"
                                "audio" -> "audio/*"
                                else -> "*/*"
                            }
                            filePickerLauncher.launch(mime)
                        },
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(50.dp),
                        shape = RoundedCornerShape(12.dp),
                        colors = ButtonDefaults.outlinedButtonColors(
                            contentColor = MaterialTheme.colorScheme.primary
                        )
                    ) {
                        Text("Choose Different File")
                    }
                } else {
                    Card(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(bottom = 24.dp),
                        shape = RoundedCornerShape(16.dp),
                        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
                    ) {
                        Column(
                            modifier = Modifier.padding(32.dp),
                            horizontalAlignment = Alignment.CenterHorizontally
                        ) {
                            Icon(
                                imageVector = when (mediaType.lowercase()) {
                                    "video" -> Icons.Default.UploadFile
                                    "audio" -> Icons.Default.Audiotrack
                                    else -> Icons.Default.Image
                                },
                                contentDescription = null,
                                tint = MaterialTheme.colorScheme.primary,
                                modifier = Modifier.size(48.dp)
                            )
                            Spacer(modifier = Modifier.height(16.dp))
                            Text(
                                text = when (mediaType.lowercase()) {
                                    "video" -> "Select a video from Files or Gallery"
                                    "audio" -> "Select an audio recording from Files"
                                    else -> "Select an image from Gallery or Files"
                                },
                                style = MaterialTheme.typography.titleMedium,
                                fontWeight = FontWeight.SemiBold,
                                color = MaterialTheme.colorScheme.onSurface
                            )
                            Spacer(modifier = Modifier.height(8.dp))
                            Text(
                                text = when (mediaType.lowercase()) {
                                    "video" -> "Supports MP4, MOV, AVI, MKV, WEBM (Max 500MB)"
                                    "audio" -> "Supports MP3, WAV, FLAC, AAC, OGG, M4A (Max 50MB)"
                                    else -> "Supports JPG, PNG, WEBP (Max 20MB)"
                                },
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f)
                            )
                        }
                    }

                    DeepGuardButton(
                        text = "Select File",
                        onClick = {
                            val mime = when (mediaType.lowercase()) {
                                "image" -> "image/*"
                                "video" -> "video/*"
                                "audio" -> "audio/*"
                                else -> "*/*"
                            }
                            filePickerLauncher.launch(mime)
                        }
                    )
                }
            }
            is AnalysisState.Uploading -> {
                CircularProgressIndicator(color = MaterialTheme.colorScheme.primary)
                Spacer(modifier = Modifier.height(16.dp))
                Text(
                    text = "Uploading file securely to DeepGuard...",
                    style = MaterialTheme.typography.bodyLarge,
                    color = MaterialTheme.colorScheme.onSurface
                )
            }
            is AnalysisState.Processing -> {
                CircularProgressIndicator(color = MaterialTheme.colorScheme.primary)
                Spacer(modifier = Modifier.height(16.dp))
                Text(
                    text = when {
                        mediaType.equals("video", ignoreCase = true) ->
                            "AI is analyzing video keyframes...\nExtracting facial sequences and running temporal analysis."
                        mediaType.equals("audio", ignoreCase = true) ->
                            "AI is analyzing audio waveform...\nExecuting AASIST spectro-temporal graph attention inference."
                        else ->
                            "AI is analyzing the media...\nExecuting EfficientNet-B0 inference."
                    },
                    style = MaterialTheme.typography.bodyLarge,
                    color = MaterialTheme.colorScheme.onSurface,
                    textAlign = TextAlign.Center
                )
            }
            is AnalysisState.Success -> {
                // Handled via LaunchedEffect
            }
        }
    }
}
