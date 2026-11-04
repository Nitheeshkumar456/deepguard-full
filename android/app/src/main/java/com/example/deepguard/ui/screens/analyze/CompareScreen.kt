package com.example.deepguard.ui.screens.analyze

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.Compare
import androidx.compose.material.icons.filled.ErrorOutline
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
fun CompareScreen(
    tokenManager: TokenManager,
    onNavigateBack: () -> Unit
) {
    val coroutineScope = rememberCoroutineScope()
    val casesApi = remember { ApiClient.getCasesApi(tokenManager) }
    val analysisApi = remember { ApiClient.getAnalysisApi(tokenManager) }

    var historyItems by remember { mutableStateOf<List<AnalysisSummaryOut>>(emptyList()) }
    var selectedId1 by remember { mutableStateOf<Int?>(null) }
    var selectedId2 by remember { mutableStateOf<Int?>(null) }

    var comparisonResult by remember { mutableStateOf<ComparisonResponseDto?>(null) }
    var isLoading by remember { mutableStateOf(false) }
    var errorMessage by remember { mutableStateOf<String?>(null) }

    LaunchedEffect(Unit) {
        try {
            val res = analysisApi.getHistory(1, 50)
            val items = res.body()?.items ?: emptyList()
            val completed = items.filter { it.status == "completed" }
            historyItems = completed
            if (completed.size >= 2) {
                selectedId1 = completed[0].id
                selectedId2 = completed[1].id
            }
        } catch (e: Exception) {
            errorMessage = e.localizedMessage
        }
    }

    fun runComparison() {
        val id1 = selectedId1
        val id2 = selectedId2
        if (id1 == null || id2 == null || id1 == id2) return

        coroutineScope.launch {
            isLoading = true
            errorMessage = null
            try {
                val res = casesApi.compareAnalyses(id1, id2)
                comparisonResult = res
            } catch (e: Exception) {
                errorMessage = e.localizedMessage ?: "Comparison failed"
            } finally {
                isLoading = false
            }
        }
    }

    LaunchedEffect(selectedId1, selectedId2) {
        if (selectedId1 != null && selectedId2 != null && selectedId1 != selectedId2) {
            runComparison()
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Forensic Media Comparison", fontWeight = FontWeight.Bold, fontSize = 18.sp) },
                navigationIcon = {
                    IconButton(onClick = onNavigateBack) {
                        Icon(Icons.Default.ArrowBack, contentDescription = "Back", tint = Color.White)
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
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues),
            contentPadding = PaddingValues(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            // Selectors Card
            item {
                Card(
                    shape = RoundedCornerShape(16.dp),
                    colors = CardDefaults.cardColors(containerColor = Surface)
                ) {
                    Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                        Text("Select Two Media Artifacts to Compare", fontWeight = FontWeight.Bold, fontSize = 14.sp, color = Color.White)

                        // Artifact 1 Selector
                        Column {
                            Text("Specimen A:", fontSize = 11.sp, color = Violet400, fontWeight = FontWeight.Bold)
                            Spacer(modifier = Modifier.height(4.dp))
                            historyItems.take(4).forEach { item ->
                                Row(
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .clip(RoundedCornerShape(8.dp))
                                        .background(if (selectedId1 == item.id) Violet600.copy(alpha = 0.25f) else Color.Transparent)
                                        .clickable { if (item.id != selectedId2) selectedId1 = item.id }
                                        .padding(6.dp),
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    RadioButton(
                                        selected = selectedId1 == item.id,
                                        onClick = { if (item.id != selectedId2) selectedId1 = item.id },
                                        enabled = item.id != selectedId2
                                    )
                                    Spacer(modifier = Modifier.width(6.dp))
                                    Text(item.originalFilename, fontSize = 12.sp, color = Color.White, maxLines = 1)
                                }
                            }
                        }

                        Divider(color = Slate700)

                        // Artifact 2 Selector
                        Column {
                            Text("Specimen B:", fontSize = 11.sp, color = InfoColor, fontWeight = FontWeight.Bold)
                            Spacer(modifier = Modifier.height(4.dp))
                            historyItems.take(4).forEach { item ->
                                Row(
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .clip(RoundedCornerShape(8.dp))
                                        .background(if (selectedId2 == item.id) InfoColor.copy(alpha = 0.25f) else Color.Transparent)
                                        .clickable { if (item.id != selectedId1) selectedId2 = item.id }
                                        .padding(6.dp),
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    RadioButton(
                                        selected = selectedId2 == item.id,
                                        onClick = { if (item.id != selectedId1) selectedId2 = item.id },
                                        enabled = item.id != selectedId1
                                    )
                                    Spacer(modifier = Modifier.width(6.dp))
                                    Text(item.originalFilename, fontSize = 12.sp, color = Color.White, maxLines = 1)
                                }
                            }
                        }
                    }
                }
            }

            // Results Section
            when {
                isLoading -> {
                    item {
                        Box(modifier = Modifier.fillMaxWidth().height(120.dp), contentAlignment = Alignment.Center) {
                            CircularProgressIndicator(color = Violet600)
                        }
                    }
                }
                errorMessage != null -> {
                    item {
                        Card(
                            shape = RoundedCornerShape(12.dp),
                            colors = CardDefaults.cardColors(containerColor = ErrorColor.copy(alpha = 0.15f))
                        ) {
                            Row(modifier = Modifier.padding(14.dp), verticalAlignment = Alignment.CenterVertically) {
                                Icon(Icons.Default.ErrorOutline, contentDescription = null, tint = ErrorColor)
                                Spacer(modifier = Modifier.width(10.dp))
                                Text(errorMessage ?: "", color = ErrorColor, fontSize = 12.sp)
                            }
                        }
                    }
                }
                comparisonResult != null -> {
                    val cr = comparisonResult!!
                    val comp = cr.comparison

                    // Verdict Banner
                    item {
                        Card(
                            shape = RoundedCornerShape(16.dp),
                            colors = CardDefaults.cardColors(containerColor = Violet600.copy(alpha = 0.2f))
                        ) {
                            Column(modifier = Modifier.padding(16.dp)) {
                                Text("Comparative Verdict", fontWeight = FontWeight.Bold, color = Violet400, fontSize = 12.sp)
                                Spacer(modifier = Modifier.height(6.dp))
                                Text(comp.forensicVerdict, fontSize = 13.sp, color = Color.White, lineHeight = 18.sp)
                                Spacer(modifier = Modifier.height(10.dp))
                                Row(horizontalArrangement = Arrangement.spacedBy(16.dp)) {
                                    Text("Modality: ${if (comp.sameModality) "Matched" else "Cross-Modal"}", fontSize = 11.sp, color = Slate400)
                                    Text("Delta: ${(comp.confidenceDelta * 100).toInt()}%", fontSize = 11.sp, color = Slate400)
                                }
                            }
                        }
                    }

                    // Side-by-Side Cards
                    item {
                        Card(
                            shape = RoundedCornerShape(16.dp),
                            colors = CardDefaults.cardColors(containerColor = Surface)
                        ) {
                            Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                                Text("Specimen Comparison", fontWeight = FontWeight.Bold, color = Color.White, fontSize = 15.sp)

                                // Specimen A
                                Column(
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .clip(RoundedCornerShape(10.dp))
                                        .background(Slate900)
                                        .padding(12.dp)
                                ) {
                                    Text("Specimen A: ${cr.item1.originalFilename}", fontWeight = FontWeight.Bold, color = Color.White, fontSize = 13.sp)
                                    Text("Classification: ${(cr.item1.prediction ?: "unknown").uppercase()}", color = if (cr.item1.prediction == "synthetic") ErrorColor else SuccessColor, fontSize = 12.sp, fontWeight = FontWeight.Bold)
                                    Text("Confidence: ${((cr.item1.confidence ?: 0f) * 100).toInt()}%", color = Slate400, fontSize = 11.sp)
                                }

                                // Specimen B
                                Column(
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .clip(RoundedCornerShape(10.dp))
                                        .background(Slate900)
                                        .padding(12.dp)
                                ) {
                                    Text("Specimen B: ${cr.item2.originalFilename}", fontWeight = FontWeight.Bold, color = Color.White, fontSize = 13.sp)
                                    Text("Classification: ${(cr.item2.prediction ?: "unknown").uppercase()}", color = if (cr.item2.prediction == "synthetic") ErrorColor else SuccessColor, fontSize = 12.sp, fontWeight = FontWeight.Bold)
                                    Text("Confidence: ${((cr.item2.confidence ?: 0f) * 100).toInt()}%", color = Slate400, fontSize = 11.sp)
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
