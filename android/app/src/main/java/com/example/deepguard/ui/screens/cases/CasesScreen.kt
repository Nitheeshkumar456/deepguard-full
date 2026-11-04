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
import com.example.deepguard.network.ApiClient
import com.example.deepguard.network.CaseSummaryDto
import com.example.deepguard.network.CreateCaseRequest
import com.example.deepguard.network.WebSocketManager
import com.example.deepguard.ui.theme.*
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CasesScreen(
    tokenManager: TokenManager,
    onNavigateBack: () -> Unit,
    onCaseClick: (Int) -> Unit
) {
    val coroutineScope = rememberCoroutineScope()
    var cases by remember { mutableStateOf<List<CaseSummaryDto>>(emptyList()) }
    var isLoading by remember { mutableStateOf(true) }
    var errorMessage by remember { mutableStateOf<String?>(null) }
    var isCreateDialogOpen by remember { mutableStateOf(false) }

    // Dialog form state
    var newTitle by remember { mutableStateOf("") }
    var newDesc by remember { mutableStateOf("") }
    var newPriority by remember { mutableStateOf("MEDIUM") }
    var newTags by remember { mutableStateOf("") }
    var isSubmitting by remember { mutableStateOf(false) }

    val casesApi = remember { ApiClient.getCasesApi(tokenManager) }

    fun loadCases() {
        coroutineScope.launch {
            isLoading = true
            errorMessage = null
            try {
                val result = casesApi.getCases()
                cases = result
            } catch (e: Exception) {
                errorMessage = e.localizedMessage ?: "Failed to load cases"
            } finally {
                isLoading = false
            }
        }
    }

    LaunchedEffect(Unit) {
        loadCases()
    }

    // Auto-update when WebSocket receives case events
    LaunchedEffect(Unit) {
        WebSocketManager.events.collect { msg ->
            if (msg.event.startsWith("case.")) {
                loadCases()
            }
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text("Investigation Cases", fontWeight = FontWeight.Bold, fontSize = 18.sp)
                        Text(
                            "Correlate forensic evidence & notes",
                            style = MaterialTheme.typography.bodySmall,
                            color = Slate400
                        )
                    }
                },
                navigationIcon = {
                    IconButton(onClick = onNavigateBack) {
                        Icon(Icons.Default.ArrowBack, contentDescription = "Back", tint = Color.White)
                    }
                },
                actions = {
                    IconButton(onClick = { loadCases() }) {
                        Icon(Icons.Default.Refresh, contentDescription = "Refresh", tint = Color.White)
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = Slate900,
                    titleContentColor = Color.White
                )
            )
        },
        floatingActionButton = {
            FloatingActionButton(
                onClick = { isCreateDialogOpen = true },
                containerColor = Violet600,
                contentColor = Color.White
            ) {
                Icon(Icons.Default.Add, contentDescription = "New Case")
            }
        },
        containerColor = Background
    ) { paddingValues ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
        ) {
            when {
                isLoading && cases.isEmpty() -> {
                    CircularProgressIndicator(
                        modifier = Modifier.align(Alignment.Center),
                        color = Violet600
                    )
                }
                errorMessage != null && cases.isEmpty() -> {
                    Column(
                        modifier = Modifier
                            .align(Alignment.Center)
                            .padding(24.dp),
                        horizontalAlignment = Alignment.CenterHorizontally
                    ) {
                        Icon(Icons.Default.ErrorOutline, contentDescription = null, tint = ErrorColor, modifier = Modifier.size(48.dp))
                        Spacer(modifier = Modifier.height(12.dp))
                        Text(errorMessage ?: "", color = Slate400, fontSize = 14.sp)
                        Spacer(modifier = Modifier.height(16.dp))
                        Button(onClick = { loadCases() }, colors = ButtonDefaults.buttonColors(containerColor = Violet600)) {
                            Text("Retry")
                        }
                    }
                }
                cases.isEmpty() -> {
                    Column(
                        modifier = Modifier
                            .align(Alignment.Center)
                            .padding(24.dp),
                        horizontalAlignment = Alignment.CenterHorizontally
                    ) {
                        Icon(Icons.Default.Folder, contentDescription = null, tint = Slate400, modifier = Modifier.size(56.dp))
                        Spacer(modifier = Modifier.height(12.dp))
                        Text("No investigation cases yet", fontWeight = FontWeight.Bold, color = Color.White)
                        Spacer(modifier = Modifier.height(6.dp))
                        Text(
                            "Tap the + button below to create your first forensic case dossier.",
                            color = Slate400,
                            fontSize = 12.sp,
                            textAlign = androidx.compose.ui.text.style.TextAlign.Center
                        )
                    }
                }
                else -> {
                    LazyColumn(
                        modifier = Modifier.fillMaxSize(),
                        contentPadding = PaddingValues(16.dp),
                        verticalArrangement = Arrangement.spacedBy(12.dp)
                    ) {
                        items(cases) { c ->
                            CaseCard(case = c, onClick = { onCaseClick(c.id) })
                        }
                    }
                }
            }
        }
    }

    // Create Case Dialog
    if (isCreateDialogOpen) {
        AlertDialog(
            onDismissRequest = { if (!isSubmitting) isCreateDialogOpen = false },
            title = {
                Text("New Investigation Case", fontWeight = FontWeight.Bold, color = Color.White)
            },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    OutlinedTextField(
                        value = newTitle,
                        onValueChange = { newTitle = it },
                        label = { Text("Case Title *") },
                        placeholder = { Text("e.g. Suspected Executive Deepfake") },
                        modifier = Modifier.fillMaxWidth(),
                        singleLine = true
                    )
                    OutlinedTextField(
                        value = newDesc,
                        onValueChange = { newDesc = it },
                        label = { Text("Description / Brief") },
                        modifier = Modifier.fillMaxWidth(),
                        maxLines = 3
                    )
                    OutlinedTextField(
                        value = newTags,
                        onValueChange = { newTags = it },
                        label = { Text("Tags (comma-separated)") },
                        placeholder = { Text("audio, ceo, spoofing") },
                        modifier = Modifier.fillMaxWidth(),
                        singleLine = true
                    )
                }
            },
            confirmButton = {
                Button(
                    onClick = {
                        if (newTitle.isNotBlank()) {
                            coroutineScope.launch {
                                isSubmitting = true
                                try {
                                    casesApi.createCase(
                                        CreateCaseRequest(
                                            title = newTitle.trim(),
                                            description = newDesc.trim().ifEmpty { null },
                                            priority = newPriority,
                                            tags = newTags.trim().ifEmpty { null }
                                        )
                                    )
                                    isCreateDialogOpen = false
                                    newTitle = ""
                                    newDesc = ""
                                    newTags = ""
                                    loadCases()
                                } catch (e: Exception) {
                                    errorMessage = e.localizedMessage
                                } finally {
                                    isSubmitting = false
                                }
                            }
                        }
                    },
                    enabled = !isSubmitting && newTitle.isNotBlank(),
                    colors = ButtonDefaults.buttonColors(containerColor = Violet600)
                ) {
                    Text(if (isSubmitting) "Creating..." else "Create Case")
                }
            },
            dismissButton = {
                TextButton(
                    onClick = { isCreateDialogOpen = false },
                    enabled = !isSubmitting
                ) {
                    Text("Cancel", color = Slate400)
                }
            },
            containerColor = Surface
        )
    }
}

@Composable
fun CaseCard(case: CaseSummaryDto, onClick: () -> Unit) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick),
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
                    text = case.caseNumber,
                    fontFamily = androidx.compose.ui.text.font.FontFamily.Monospace,
                    fontSize = 11.sp,
                    fontWeight = FontWeight.Bold,
                    color = Violet400
                )
                Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    PriorityBadge(case.priority)
                    StatusBadge(case.status)
                }
            }

            Spacer(modifier = Modifier.height(8.dp))
            Text(
                text = case.title,
                fontWeight = FontWeight.Bold,
                fontSize = 15.sp,
                color = Color.White,
                maxLines = 1
            )

            if (!case.description.isNullOrBlank()) {
                Spacer(modifier = Modifier.height(4.dp))
                Text(
                    text = case.description,
                    fontSize = 12.sp,
                    color = Slate400,
                    maxLines = 2
                )
            }

            Spacer(modifier = Modifier.height(12.dp))
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                        Icon(Icons.Default.Layers, contentDescription = null, tint = Violet400, modifier = Modifier.size(14.dp))
                        Text("${case.analysesCount} items", fontSize = 11.sp, color = Slate400)
                    }
                    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                        Icon(Icons.Default.Notes, contentDescription = null, tint = Slate400, modifier = Modifier.size(14.dp))
                        Text("${case.notesCount} notes", fontSize = 11.sp, color = Slate400)
                    }
                }
                Icon(Icons.Default.ChevronRight, contentDescription = null, tint = Slate400, modifier = Modifier.size(18.dp))
            }
        }
    }
}

@Composable
fun PriorityBadge(priority: String) {
    val (bgColor, textColor) = when (priority.uppercase()) {
        "CRITICAL" -> ErrorColor.copy(alpha = 0.2f) to ErrorColor
        "HIGH" -> WarningColor.copy(alpha = 0.2f) to WarningColor
        "MEDIUM" -> Violet600.copy(alpha = 0.2f) to Violet400
        else -> Slate700 to Slate400
    }
    Box(
        modifier = Modifier
            .clip(RoundedCornerShape(6.dp))
            .background(bgColor)
            .padding(horizontal = 6.dp, vertical = 2.dp)
    ) {
        Text(text = priority, fontSize = 9.sp, fontWeight = FontWeight.Bold, color = textColor)
    }
}

@Composable
fun StatusBadge(status: String) {
    val (bgColor, textColor) = when (status.uppercase()) {
        "FLAGGED" -> ErrorColor.copy(alpha = 0.2f) to ErrorColor
        "IN_REVIEW" -> InfoColor.copy(alpha = 0.2f) to InfoColor
        "RESOLVED" -> SuccessColor.copy(alpha = 0.2f) to SuccessColor
        else -> Violet600.copy(alpha = 0.2f) to Violet400
    }
    Box(
        modifier = Modifier
            .clip(RoundedCornerShape(6.dp))
            .background(bgColor)
            .padding(horizontal = 6.dp, vertical = 2.dp)
    ) {
        Text(text = status.replace("_", " "), fontSize = 9.sp, fontWeight = FontWeight.Bold, color = textColor)
    }
}
