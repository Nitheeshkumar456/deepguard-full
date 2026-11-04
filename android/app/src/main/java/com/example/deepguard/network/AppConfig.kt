package com.example.deepguard.network

/**
 * AppConfig — Centralized network and environment configuration for DeepGuard AI Android App.
 *
 * Switch the active BASE_URL here depending on your development or deployment target:
 *
 * 1. Android Emulator:
 *    Use "http://10.0.2.2:8000/" (10.0.2.2 maps to host machine's 127.0.0.1 in Android Studio emulator)
 *
 * 2. Real Physical Android Device (over same Wi-Fi LAN):
 *    Use "http://<YOUR_PC_LAN_IP>:8000/" (e.g., "http://192.168.1.7:8000/")
 *    Make sure FastAPI backend is started with: uvicorn app.main:app --host 0.0.0.0 --port 8000
 *
 * 3. Production Deployment:
 *    Use "https://api.yourdomain.com/" (HTTPS production endpoint)
 */
object AppConfig {

    /** Android Studio Emulator Loopback URL */
    const val EMULATOR_BASE_URL = "http://10.0.2.2:8000/"

    /** Physical Device LAN URL (Current PC Wi-Fi IP address) */
    const val PHYSICAL_DEVICE_BASE_URL = "http://192.168.1.4:8000/"

    /** Production Secure HTTPS URL */
    const val PRODUCTION_BASE_URL = "https://api.deepguard.ai/"

    /**
     * Active Base URL used by Retrofit and network services across the app.
     * Change this single line to switch between Emulator, Physical Phone, or Production.
     */
    var BASE_URL: String = PHYSICAL_DEVICE_BASE_URL

    /**
     * Helper to dynamically update the BASE_URL at runtime if needed.
     */
    fun updateBaseUrl(newUrl: String) {
        BASE_URL = if (newUrl.endsWith("/")) newUrl else "$newUrl/"
        ApiClient.resetRetrofitClients()
    }
}
