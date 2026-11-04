package com.example.deepguard.data

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow
import kotlinx.coroutines.flow.map

val Context.dataStore: DataStore<Preferences> by preferencesDataStore(name = "auth_prefs")

open class TokenManager(protected val context: Context?) {
    
    companion object {
        private val ACCESS_TOKEN_KEY = stringPreferencesKey("access_token")
        private val REFRESH_TOKEN_KEY = stringPreferencesKey("refresh_token")
    }

    open val accessToken: Flow<String?> = context?.dataStore?.data?.map { preferences ->
        preferences[ACCESS_TOKEN_KEY]
    } ?: kotlinx.coroutines.flow.flowOf(null)

    open val refreshToken: Flow<String?> = context?.dataStore?.data?.map { preferences ->
        preferences[REFRESH_TOKEN_KEY]
    } ?: kotlinx.coroutines.flow.flowOf(null)

    open suspend fun saveTokens(accessToken: String, refreshToken: String) {
        context?.dataStore?.edit { preferences ->
            preferences[ACCESS_TOKEN_KEY] = accessToken
            preferences[REFRESH_TOKEN_KEY] = refreshToken
        }
    }

    open suspend fun clearTokens() {
        context?.dataStore?.edit { preferences ->
            preferences.remove(ACCESS_TOKEN_KEY)
            preferences.remove(REFRESH_TOKEN_KEY)
        }
    }
}
