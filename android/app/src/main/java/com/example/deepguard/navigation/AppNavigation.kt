package com.example.deepguard.navigation

import android.net.Uri
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Analytics
import androidx.compose.material.icons.filled.History
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.Person
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavDestination.Companion.hierarchy
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.example.deepguard.data.AnalysisRepository
import com.example.deepguard.data.AuthRepository
import com.example.deepguard.data.TokenManager
import com.example.deepguard.network.ApiClient
import com.example.deepguard.network.AnalysisDetailOut
import com.example.deepguard.presentation.AnalysisViewModel
import com.example.deepguard.presentation.AppViewModelFactory
import com.example.deepguard.presentation.AuthViewModel
import com.example.deepguard.presentation.HistoryViewModel
import com.example.deepguard.ui.screens.ForgotPasswordScreen
import com.example.deepguard.ui.screens.LoginScreen
import com.example.deepguard.ui.screens.OnboardingScreen
import com.example.deepguard.ui.screens.HelpScreen
import com.example.deepguard.ui.screens.NotificationsScreen
import com.example.deepguard.ui.screens.OtpVerificationScreen
import com.example.deepguard.ui.screens.ProfileScreen
import com.example.deepguard.ui.screens.ReportsScreen
import com.example.deepguard.ui.screens.SettingsScreen
import com.example.deepguard.ui.screens.SignupScreen
import com.example.deepguard.ui.screens.SplashScreen
import com.example.deepguard.ui.screens.analyze.AnalyzeScreen
import com.example.deepguard.ui.screens.analyze.MediaUploadScreen
import com.example.deepguard.ui.screens.analyze.ResultScreen
import com.example.deepguard.ui.screens.history.HistoryScreen
import com.example.deepguard.ui.screens.home.HomeScreen
import com.example.deepguard.data.SyncRepository
import com.example.deepguard.presentation.NotificationViewModel
import com.example.deepguard.presentation.SettingsViewModel

sealed class Screen(val route: String) {
    object Splash : Screen("splash")
    object Onboarding : Screen("onboarding")
    object Login : Screen("login")
    object Signup : Screen("signup")
    object OtpVerification : Screen("otp_verification")
    object ForgotPassword : Screen("forgot_password")
    
    // Main authenticated flow
    object Main : Screen("main")
    object Settings : Screen("settings")
    object Notifications : Screen("notifications")
    object Help : Screen("help")
    object Reports : Screen("reports")
    object UploadMedia : Screen("upload_media/{mediaType}") {
        fun createRoute(mediaType: String) = "upload_media/$mediaType"
    }
    object AnalysisResult : Screen("analysis_result/{analysisId}") {
        fun createRoute(analysisId: Int) = "analysis_result/$analysisId"
    }
    object Cases : Screen("cases")
    object CaseDetail : Screen("case_detail/{caseId}") {
        fun createRoute(caseId: Int) = "case_detail/$caseId"
    }
    object Compare : Screen("compare")
}

sealed class BottomNavScreen(val route: String, val title: String, val icon: ImageVector) {
    object Home : BottomNavScreen("home", "Home", Icons.Default.Home)
    object Analyze : BottomNavScreen("analyze", "Analyze", Icons.Default.Analytics)
    object History : BottomNavScreen("history", "History", Icons.Default.History)
    object Profile : BottomNavScreen("profile", "Profile", Icons.Default.Person)
}

@Composable
fun AppNavigation() {
    val navController = rememberNavController()
    val context = LocalContext.current
    
    val tokenManager = remember { TokenManager(context) }
    val authRepository = remember { AuthRepository(ApiClient.getAuthApi(tokenManager), tokenManager) }
    val analysisRepository = remember { AnalysisRepository(ApiClient.getAnalysisApi(tokenManager)) }
    val syncRepository = remember { SyncRepository(ApiClient.getSyncApi(tokenManager)) }
    val factory = remember { AppViewModelFactory(authRepository, analysisRepository, syncRepository) }
    
    val authViewModel: AuthViewModel = viewModel(factory = factory)
    val analysisViewModel: AnalysisViewModel = viewModel(factory = factory)
    val historyViewModel: HistoryViewModel = viewModel(factory = factory)
    val settingsViewModel: SettingsViewModel = viewModel(factory = factory)
    val notificationViewModel: NotificationViewModel = viewModel(factory = factory)

    NavHost(navController = navController, startDestination = Screen.Splash.route) {
        
        composable(Screen.Splash.route) {
            SplashScreen(
                viewModel = authViewModel,
                onDecision = { isLoggedIn ->
                    if (isLoggedIn) {
                        navController.navigate(Screen.Main.route) {
                            popUpTo(Screen.Splash.route) { inclusive = true }
                        }
                    } else {
                        navController.navigate(Screen.Onboarding.route) {
                            popUpTo(Screen.Splash.route) { inclusive = true }
                        }
                    }
                }
            )
        }

        composable(Screen.Onboarding.route) {
            OnboardingScreen(
                onNavigateToLogin = { navController.navigate(Screen.Login.route) },
                onNavigateToSignup = { navController.navigate(Screen.Signup.route) }
            )
        }

        composable(Screen.Login.route) {
            LoginScreen(
                viewModel = authViewModel,
                onNavigateToSignup = { navController.navigate(Screen.Signup.route) },
                onNavigateToForgotPassword = { navController.navigate(Screen.ForgotPassword.route) },
                onLoginSuccess = { 
                    navController.navigate(Screen.Main.route) {
                        popUpTo(0) { inclusive = true }
                    }
                }
            )
        }

        composable(Screen.Signup.route) {
            SignupScreen(
                viewModel = authViewModel,
                onNavigateToLogin = { navController.navigate(Screen.Login.route) },
                onSignupSuccess = { navController.navigate(Screen.OtpVerification.route) }
            )
        }

        composable(Screen.OtpVerification.route) {
            OtpVerificationScreen(
                viewModel = authViewModel,
                onVerificationSuccess = { purpose ->
                    if (purpose == "reset") {
                        navController.navigate(Screen.ForgotPassword.route)
                    } else {
                        navController.navigate(Screen.Login.route) {
                            popUpTo(Screen.Signup.route) { inclusive = true }
                        }
                    }
                }
            )
        }

        composable(Screen.ForgotPassword.route) {
            ForgotPasswordScreen(
                viewModel = authViewModel,
                onNavigateToOtp = { navController.navigate(Screen.OtpVerification.route) },
                onNavigateBack = { navController.navigateUp() }
            )
        }

        // Main authenticated flow with Bottom Nav
        composable(Screen.Main.route) {
            MainScreen(
                authViewModel = authViewModel,
                historyViewModel = historyViewModel,
                onNavigateToUpload = { mediaType ->
                    navController.navigate(Screen.UploadMedia.createRoute(mediaType))
                },
                onNavigateToResult = { analysisId ->
                    navController.navigate(Screen.AnalysisResult.createRoute(analysisId))
                },
                onNavigateToCases = {
                    navController.navigate(Screen.Cases.route)
                },
                onNavigateToCompare = {
                    navController.navigate(Screen.Compare.route)
                },
                onLogout = {
                    navController.navigate(Screen.Login.route) {
                        popUpTo(0) { inclusive = true }
                    }
                }
            )
        }

        composable(Screen.Settings.route) {
            SettingsScreen(viewModel = settingsViewModel)
        }

        composable(Screen.Notifications.route) {
            NotificationsScreen(viewModel = notificationViewModel)
        }

        composable(Screen.Help.route) {
            HelpScreen()
        }

        composable(Screen.Reports.route) {
            ReportsScreen()
        }

        composable(
            route = Screen.UploadMedia.route,
            arguments = listOf(navArgument("mediaType") { type = NavType.StringType })
        ) { backStackEntry ->
            val mediaType = backStackEntry.arguments?.getString("mediaType") ?: "image"
            analysisViewModel.resetState()
            MediaUploadScreen(
                mediaType = mediaType,
                viewModel = analysisViewModel,
                onNavigateToResult = { resultData ->
                    navController.navigate(Screen.AnalysisResult.createRoute(resultData.id)) {
                        popUpTo(Screen.Main.route) { inclusive = false }
                    }
                }
            )
        }

        composable(
            route = Screen.AnalysisResult.route,
            arguments = listOf(navArgument("analysisId") { type = NavType.IntType })
        ) { backStackEntry ->
            val analysisId = backStackEntry.arguments?.getInt("analysisId") ?: 0
            ResultScreen(
                analysisId = analysisId,
                viewModel = analysisViewModel,
                onNavigateBack = {
                    navController.navigate(Screen.Main.route) {
                        popUpTo(Screen.Main.route) { inclusive = true }
                    }
                }
            )
        }

        composable(Screen.Cases.route) {
            com.example.deepguard.ui.screens.cases.CasesScreen(
                tokenManager = tokenManager,
                onNavigateBack = { navController.popBackStack() },
                onCaseClick = { caseId ->
                    navController.navigate(Screen.CaseDetail.createRoute(caseId))
                }
            )
        }

        composable(
            route = Screen.CaseDetail.route,
            arguments = listOf(navArgument("caseId") { type = NavType.IntType })
        ) { backStackEntry ->
            val caseId = backStackEntry.arguments?.getInt("caseId") ?: 0
            com.example.deepguard.ui.screens.cases.CaseDetailScreen(
                caseId = caseId,
                tokenManager = tokenManager,
                onNavigateBack = { navController.popBackStack() },
                onNavigateToAnalysis = { analysisId ->
                    navController.navigate(Screen.AnalysisResult.createRoute(analysisId))
                }
            )
        }

        composable(Screen.Compare.route) {
            com.example.deepguard.ui.screens.analyze.CompareScreen(
                tokenManager = tokenManager,
                onNavigateBack = { navController.popBackStack() }
            )
        }
    }
}

@Composable
fun MainScreen(
    authViewModel: AuthViewModel,
    historyViewModel: HistoryViewModel,
    onNavigateToUpload: (String) -> Unit,
    onNavigateToResult: (Int) -> Unit = {},
    onNavigateToCases: () -> Unit = {},
    onNavigateToCompare: () -> Unit = {},
    onLogout: () -> Unit
) {
    val navController = rememberNavController()
    val items = listOf(
        BottomNavScreen.Home,
        BottomNavScreen.Analyze,
        BottomNavScreen.History,
        BottomNavScreen.Profile
    )

    Scaffold(
        bottomBar = {
            NavigationBar {
                val navBackStackEntry by navController.currentBackStackEntryAsState()
                val currentDestination = navBackStackEntry?.destination
                items.forEach { screen ->
                    NavigationBarItem(
                        icon = { Icon(screen.icon, contentDescription = null) },
                        label = { Text(screen.title) },
                        selected = currentDestination?.hierarchy?.any { it.route == screen.route } == true,
                        onClick = {
                            navController.navigate(screen.route) {
                                popUpTo(navController.graph.findStartDestination().id) {
                                    saveState = true
                                }
                                launchSingleTop = true
                                restoreState = true
                            }
                        }
                    )
                }
            }
        }
    ) { innerPadding ->
        NavHost(
            navController = navController,
            startDestination = BottomNavScreen.Home.route,
            modifier = Modifier.padding(innerPadding)
        ) {
            composable(BottomNavScreen.Home.route) { 
                HomeScreen(
                    authViewModel = authViewModel,
                    historyViewModel = historyViewModel,
                    onNavigateToAnalyze = {
                        navController.navigate(BottomNavScreen.Analyze.route) {
                            popUpTo(navController.graph.findStartDestination().id) { saveState = true }
                            launchSingleTop = true
                            restoreState = true
                        }
                    },
                    onNavigateToDetail = onNavigateToResult,
                    onNavigateToProfile = {
                        navController.navigate(BottomNavScreen.Profile.route) {
                            popUpTo(navController.graph.findStartDestination().id) { saveState = true }
                            launchSingleTop = true
                            restoreState = true
                        }
                    },
                    onNavigateToHistory = {
                        navController.navigate(BottomNavScreen.History.route) {
                            popUpTo(navController.graph.findStartDestination().id) { saveState = true }
                            launchSingleTop = true
                            restoreState = true
                        }
                    },
                    onNavigateToCases = onNavigateToCases,
                    onNavigateToCompare = onNavigateToCompare
                ) 
            }
            composable(BottomNavScreen.Analyze.route) { AnalyzeScreen(onNavigateToUpload) }
            composable(BottomNavScreen.History.route) { 
                HistoryScreen(
                    viewModel = historyViewModel,
                    onNavigateToDetail = onNavigateToResult
                ) 
            }
            composable(BottomNavScreen.Profile.route) { ProfileScreen(authViewModel, onLogout) }
        }
    }
}

