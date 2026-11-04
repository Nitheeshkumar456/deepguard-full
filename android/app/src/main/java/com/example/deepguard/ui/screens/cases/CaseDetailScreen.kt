package com.example.deepguard.ui.screens.cases

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.deepguard.data.TokenManager
import com.example.deepguard.network.*
import com.example.deepguard.ui.theme.*
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CaseDetailScreen(
    caseId: Int,
    tokenManager: TokenManager,
    onNavigateBack: () -> Unit,
    onNavigateToAnalysis: (Int) -> Unit
) {
    val coroutineScope = rememberCoroutineScope()
    val casesApi = remember { ApiClient.getCasesApi(tokenManager) }
    val analysisApi = remember { ApiClient.getAnalysisApi(tokenManager) }

    var caseDetail by remember { mutableStateOf<CaseDetailDto?>(null) }
    var isLoading by remember { mutableStateOf(true) }
    var errorMessage by remember { mutableStateOf<String?>(null) }

    // Add note dialog state
    var isAddNoteDialogOpen by remember { mutableStateOf(false) }
    var newNoteContent by remember { mutableStateOf("") }
    var isSubmittingNote by remember { mutableStateOf(false) }

    // Attach analysis dialog state
    var isAttachDialogOpen by remember { mutableStateOf(false) }
    var availableAnalyses by remember { mutableStateOf<List<AnalysisSummaryOut>>(emptyList()) }
    var selectedAnalysisId by remember { mutableStateOf<Int?>(null) }
    var attachNotes by remember { mutableStateOf("") }
    var isAttaching by remember { mutableStateOf(false) }

    fun loadCaseDetail() {
        coroutineScope.launch {
            isLoading = true
            errorMessage = null
            try {
                val detail = casesApi.getCaseDetail(caseId)
                caseDetail = detail
            } catch (e: Exception) {
                errorMessage = e.localizedMessage ?: "Failed to load case detail"
            } finally {
                isLoading = false
            }
        }
    }

    LaunchedEffect(caseId) {
        loadCaseDetail()
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Text(
                        caseDetail?.caseNumber ?: "Case Detail",
                        fontFamily = androidx.compose.ui.text.font.FontFamily.Monospace,
                        fontSize = 16.sp,
                        fontWeight = FontWeight.Bold
                    )
                },
                navigationIcon = {
                    IconButton(onClick = onNavigateBack) {
                        Icon(Icons.Default.ArrowBack, contentDescription = "Back", tint = Color.White)
                    }
                },
                actions = {
                    IconButton(onClick = {
                        coroutineScope.launch {
                            try {
                                casesApi.deleteCase(caseId)
                                onNavigateBack()
                            } catch (e: Exception) {
                                errorMessage = e.localizedMessage
                            }
                        }
                    }) {
                        Icon(Icons.Default.Delete, contentDescription = "Delete Case", tint = ErrorColor)
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = Slate900,
                    titleContentColor = Color.White
                )
            )
        },
        containerColor = Background
    ) { paddingValues ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
        ) {
            when {
                isLoading -> {
                    CircularProgressIndicator(
                        modifier = Modifier.align(Alignment.Center),
                        color = Violet600
                    )
                }
                caseDetail != null -> {
                    val c = caseDetail!!
                    LazyColumn(
                        modifier = Modifier.fillMaxSize(),
                        contentPadding = PaddingValues(16.dp),
                        verticalArrangement = Arrangement.spacedBy(16.dp)
                    ) {
                        // Header Info Card
                        item {
                            Card(
                                shape = RoundedCornerShape(16.dp),
                                colors = CardDefaults.cardColors(containerColor = Surface)
                            ) {
                                Column(modifier = Modifier.padding(16.dp)) {
                                    Row(
                                        modifier = Modifier.fillMaxWidth(),
                                        horizontalArrangement = Arrangement.SpaceBetween,
                                        verticalAlignment = Alignment.CenterVertically
                                    ) {
                                        Text(
                                            text = c.caseNumber,
                                            fontFamily = androidx.compose.ui.text.font.FontFamily.Monospace,
                                            color = Violet400,
                                            fontSize = 12.sp,
                                            fontWeight = FontWeight.Bold
                                        )
                                        Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                                            PriorityBadge(c.priority)
                                            StatusBadge(c.status)
                                        }
                                    }

                                    Spacer(modifier = Modifier.height(10.dp))
                                    Text(
                                        text = c.title,
                                        fontSize = 18.sp,
                                        fontWeight = FontWeight.Bold,
                                        color = Color.White
                                    )

                                    if (!c.description.isNullOrBlank()) {
                                        Spacer(modifier = Modifier.height(6.dp))
                                        Text(
                                            text = c.description,
                                            fontSize = 13.sp,
                                            color = Slate400,
                                            lineHeight = 18.sp
                                        )
                                    }

                                    // Quick Status Change buttons
                                    Spacer(modifier = Modifier.height(14.dp))
                                    Text("Change Investigation Status:", fontSize = 11.sp, color = Slate400)
                                    Spacer(modifier = Modifier.height(6.dp))
                                    Row(
                                        modifier = Modifier.fillMaxWidth(),
                                        horizontalArrangement = Arrangement.spacedBy(6.dp)
                                    ) {
                                        listOf("OPEN", "IN_REVIEW", "FLAGGED", "RESOLVED").forEach { st ->
                                            OutlinedButton(
                                                onClick = {
                                                    coroutineScope.launch {
                                                        try {
                                                            val updated = casesApi.updateCase(c.id, UpdateCaseRequest(status = st))
                                                            caseDetail = updated
                                                        } catch (e: Exception) {
                                                            errorMessage = e.localizedMessage
                                                        }
                                                    }
                                                },
                                                modifier = Modifier.weight(1f),
                                                contentPadding = PaddingValues(horizontal = 2.dp, vertical = 2.dp),
                                                colors = ButtonDefaults.outlinedButtonColors(
                                                    containerColor = if (c.status == st) Violet600.copy(alpha = 0.3f) else Color.Transparent
                                                )
                                            ) {
                                                Text(st.take(4), fontSize = 10.sp, maxLines = 1)
                                            }
                                        }
                                    }
                                }
                            }
                        }

                        // Attached Evidence Section Header
                        item {
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Text(
                                    text = "Evidence Artifacts (${c.analyses.size})",
                                    fontSize = 16.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = Color.White
                                )
                                TextButton(
                                    onClick = {
                                        coroutineScope.launch {
                                            try {
                                                val res = analysisApi.getHistory(1, 50)
                                                val items = res.body()?.items ?: emptyList()
                                                availableAnalyses = items
                                                if (availableAnalyses.isNotEmpty()) {
                                                    selectedAnalysisId = availableAnalyses.first().id
                                                }
                                                isAttachDialogOpen = true
                                            } catch (e: Exception) {
                                                errorMessage = e.localizedMessage
                                            }
                                        }
                                    }
                                ) {
                                    Icon(Icons.Default.Add, contentDescription = null, modifier = Modifier.size(16.dp))
                                    Spacer(modifier = Modifier.width(4.dp))
                                    Text("Attach", fontSize = 13.sp)
                                }
                            }
                        }

                        // Evidence List
                        if (c.analyses.isEmpty()) {
                            item {
                                Box(
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .clip(RoundedCornerShape(12.dp))
                                        .background(Surface.copy(alpha = 0.5f))
                                        .padding(20.dp),
                                    contentAlignment = Alignment.Center
                                ) {
                                    Text("No evidence attached yet", fontSize = 13.sp, color = Slate400)
                                }
                            }
                        } else {
                            items(c.analyses) { a ->
                                Card(
                                    modifier = Modifier.fillMaxWidth(),
                                    shape = RoundedCornerShape(12.dp),
                                    colors = CardDefaults.cardColors(containerColor = Surface)
                                ) {
                                    Row(
                                        modifier = Modifier
                                            .fillMaxWidth()
                                            .padding(12.dp),
                                        horizontalArrangement = Arrangement.SpaceBetween,
                                        verticalAlignment = Alignment.CenterVertically
                                    ) {
                                        Column(modifier = Modifier.weight(1f)) {
                                            Row(
                                                verticalAlignment = Alignment.CenterVertically,
                                                horizontalArrangement = Arrangement.spacedBy(6.dp)
                                            ) {
                                                Text(
                                                    text = a.mediaType.uppercase(),
                                                    fontSize = 10.sp,
                                                    fontWeight = FontWeight.Bold,
                                                    color = Violet400
                                                )
                                                if (a.prediction != null) {
                                                    Text(
                                                        text = "• ${a.prediction.uppercase()}",
                                                        fontSize = 10.sp,
                                                        fontWeight = FontWeight.Bold,
                                                        color = if (a.prediction == "synthetic") ErrorColor else SuccessColor
                                                    )
                                                }
                                            }
                                            Spacer(modifier = Modifier.height(2.dp))
                                            Text(
                                                text = a.originalFilename,
                                                fontSize = 13.sp,
                                                fontWeight = FontWeight.Medium,
                                                color = Color.White,
                                                maxLines = 1
                                            )
                                            if (!a.notes.isNullOrBlank()) {
                                                Text(
                                                    text = a.notes,
                                                    fontSize = 11.sp,
                                                    color = Slate400,
                                                    fontStyle = androidx.compose.ui.text.font.FontStyle.Italic
                                                )
                                            }
                                        }

                                        Row(verticalAlignment = Alignment.CenterVertically) {
                                            IconButton(onClick = { onNavigateToAnalysis(a.analysisId) }) {
                                                Icon(Icons.Default.OpenInNew, contentDescription = "View", tint = Violet400, modifier = Modifier.size(18.dp))
                                            }
                                            IconButton(onClick = {
                                                coroutineScope.launch {
                                                    try {
                                                        val updated = casesApi.detachAnalysis(c.id, a.analysisId)
                                                        caseDetail = updated
                                                    } catch (e: Exception) {
                                                        errorMessage = e.localizedMessage
                                                    }
                                                }
                                            }) {
                                                Icon(Icons.Default.Close, contentDescription = "Detach", tint = Slate400, modifier = Modifier.size(18.dp))
                                            }
                                        }
                                    }
                                }
                            }
                        }

                        // Notes Section Header
                        item {
                            Spacer(modifier = Modifier.height(8.dp))
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Text(
                                    text = "Investigator Notes (${c.notes.size})",
                                    fontSize = 16.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = Color.White
                                )
                                TextButton(onClick = { isAddNoteDialogOpen = true }) {
                                    Icon(Icons.Default.AddComment, contentDescription = null, modifier = Modifier.size(16.dp))
                                    Spacer(modifier = Modifier.width(4.dp))
                                    Text("Add Note", fontSize = 13.sp)
                                }
                            }
                        }

                        // Notes List
                        if (c.notes.isEmpty()) {
                            item {
                                Box(
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .clip(RoundedCornerShape(12.dp))
                                        .background(Surface.copy(alpha = 0.5f))
                                        .padding(20.dp),
                                    contentAlignment = Alignment.Center
                                ) {
                                    Text("No investigator notes recorded", fontSize = 13.sp, color = Slate400)
                                }
                            }
                        } else {
                            items(c.notes) { n ->
                                Card(
                                    modifier = Modifier.fillMaxWidth(),
                                    shape = RoundedCornerShape(12.dp),
                                    colors = CardDefaults.cardColors(containerColor = Surface.copy(alpha = 0.8f))
                                ) {
                                    Column(modifier = Modifier.padding(12.dp)) {
                                        Row(
                                            modifier = Modifier.fillMaxWidth(),
                                            horizontalArrangement = Arrangement.SpaceBetween
                                        ) {
                                            Text(n.authorName, fontSize = 11.sp, fontWeight = FontWeight.Bold, color = Violet400)
                                            Text(n.createdAt.take(16).replace("T", " "), fontSize = 10.sp, color = Slate400)
                                        }
                                        Spacer(modifier = Modifier.height(4.dp))
                                        Text(n.content, fontSize = 12.sp, color = Color.White)
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    // Add Note Dialog
    if (isAddNoteDialogOpen) {
        AlertDialog(
            onDismissRequest = { if (!isSubmittingNote) isAddNoteDialogOpen = false },
            title = { Text("Add Investigator Note", color = Color.White, fontWeight = FontWeight.Bold) },
            text = {
                OutlinedTextField(
                    value = newNoteContent,
                    onValueChange = { newNoteContent = it },
                    label = { Text("Note content") },
                    placeholder = { Text("Enter technical finding or observation...") },
                    modifier = Modifier.fillMaxWidth(),
                    maxLines = 4
                )
            },
            confirmButton = {
                Button(
                    onClick = {
                        if (newNoteContent.isNotBlank()) {
                            coroutineScope.launch {
                                isSubmittingNote = true
                                try {
                                    val updated = casesApi.addNote(caseId, AddCaseNoteRequest(newNoteContent.trim()))
                                    caseDetail = updated
                                    newNoteContent = ""
                                    isAddNoteDialogOpen = false
                                } catch (e: Exception) {
                                    errorMessage = e.localizedMessage
                                } finally {
                                    isSubmittingNote = false
                                }
                            }
                        }
                    },
                    enabled = !isSubmittingNote && newNoteContent.isNotBlank(),
                    colors = ButtonDefaults.buttonColors(containerColor = Violet600)
                ) {
                    Text(if (isSubmittingNote) "Posting..." else "Post Note")
                }
            },
            dismissButton = {
                TextButton(onClick = { isAddNoteDialogOpen = false }) {
                    Text("Cancel", color = Slate400)
                }
            },
            containerColor = Surface
        )
    }

    // Attach Analysis Dialog
    if (isAttachDialogOpen) {
        AlertDialog(
            onDismissRequest = { if (!isAttaching) isAttachDialogOpen = false },
            title = { Text("Attach Media Evidence", color = Color.White, fontWeight = FontWeight.Bold) },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    Text("Select a completed scan from your analysis history:", fontSize = 12.sp, color = Slate400)
                    availableAnalyses.forEach { a ->
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .clip(RoundedCornerShape(8.dp))
                                .background(if (selectedAnalysisId == a.id) Violet600.copy(alpha = 0.25f) else Color.Transparent)
                                .clickable { selectedAnalysisId = a.id }
                                .padding(8.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            RadioButton(
                                selected = selectedAnalysisId == a.id,
                                onClick = { selectedAnalysisId = a.id },
                                colors = RadioButtonDefaults.colors(selectedColor = Violet600)
                            )
                            Spacer(modifier = Modifier.width(8.dp))
                            Column {
                                Text(a.originalFilename, fontSize = 12.sp, color = Color.White, maxLines = 1)
                                Text("${a.mediaType.uppercase()} • ${a.status}", fontSize = 10.sp, color = Slate400)
                            }
                        }
                    }
                }
            },
            confirmButton = {
                Button(
                    onClick = {
                        val aid = selectedAnalysisId
                        if (aid != null) {
                            coroutineScope.launch {
                                isAttaching = true
                                try {
                                    val updated = casesApi.attachAnalysis(
                                        caseId,
                                        AttachAnalysisRequest(analysisId = aid, notes = attachNotes.ifEmpty { null })
                                    )
                                    caseDetail = updated
                                    isAttachDialogOpen = false
                                } catch (e: Exception) {
                                    errorMessage = e.localizedMessage
                                } finally {
                                    isAttaching = false
                                }
                            }
                        }
                    },
                    enabled = !isAttaching && selectedAnalysisId != null,
                    colors = ButtonDefaults.buttonColors(containerColor = Violet600)
                ) {
                    Text(if (isAttaching) "Attaching..." else "Attach")
                }
            },
            dismissButton = {
                TextButton(onClick = { isAttachDialogOpen = false }) {
                    Text("Cancel", color = Slate400)
                }
            },
            containerColor = Surface
        )
    }
}
