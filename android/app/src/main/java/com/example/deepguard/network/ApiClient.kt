package com.example.deepguard.network

import com.example.deepguard.data.TokenManager
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit

object ApiClient {
    private val loggingInterceptor = HttpLoggingInterceptor().apply {
        level = HttpLoggingInterceptor.Level.BASIC
    }

    private val unauthenticatedHttpClient by lazy {
        OkHttpClient.Builder()
            .addInterceptor(loggingInterceptor)
            .connectTimeout(30, TimeUnit.SECONDS)
            .readTimeout(30, TimeUnit.SECONDS)
            .build()
    }

    private var _unauthenticatedRetrofit: Retrofit? = null

    private fun getUnauthenticatedRetrofit(): Retrofit {
        if (_unauthenticatedRetrofit == null) {
            _unauthenticatedRetrofit = Retrofit.Builder()
                .baseUrl(AppConfig.BASE_URL)
                .client(unauthenticatedHttpClient)
                .addConverterFactory(GsonConverterFactory.create())
                .build()
        }
        return _unauthenticatedRetrofit!!
    }

    val authApi: AuthApi
        get() = getUnauthenticatedRetrofit().create(AuthApi::class.java)

    private var authenticatedRetrofit: Retrofit? = null

    @Synchronized
    fun resetRetrofitClients() {
        _unauthenticatedRetrofit = null
        authenticatedRetrofit = null
    }

    private fun getAuthenticatedRetrofit(tokenManager: TokenManager): Retrofit {
        if (authenticatedRetrofit == null) {
            val authClient = OkHttpClient.Builder()
                .addInterceptor(AuthInterceptor(tokenManager))
                .addInterceptor(loggingInterceptor)
                .connectTimeout(60, TimeUnit.SECONDS)
                .readTimeout(60, TimeUnit.SECONDS)
                .writeTimeout(60, TimeUnit.SECONDS)
                .build()

            authenticatedRetrofit = Retrofit.Builder()
                .baseUrl(AppConfig.BASE_URL)
                .client(authClient)
                .addConverterFactory(GsonConverterFactory.create())
                .build()
        }
        return authenticatedRetrofit!!
    }

    fun getAuthApi(tokenManager: TokenManager): AuthApi {
        return getAuthenticatedRetrofit(tokenManager).create(AuthApi::class.java)
    }

    fun getAnalysisApi(tokenManager: TokenManager): AnalysisApi {
        return getAuthenticatedRetrofit(tokenManager).create(AnalysisApi::class.java)
    }

    fun getSyncApi(tokenManager: TokenManager): SyncApi {
        return getAuthenticatedRetrofit(tokenManager).create(SyncApi::class.java)
    }

    fun getCasesApi(tokenManager: TokenManager): CasesApi {
        return getAuthenticatedRetrofit(tokenManager).create(CasesApi::class.java)
    }
}

