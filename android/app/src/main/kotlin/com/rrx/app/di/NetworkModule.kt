package com.rrx.app.di

import com.jakewharton.retrofit2.converter.kotlinx.serialization.asConverterFactory
import com.rrx.app.network.RrxApi
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import kotlinx.serialization.json.Json
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object NetworkModule {

    // 10.0.2.2 is the standard Android emulator alias for the host
    // machine's localhost -- backend/docker-compose.yml publishes the API
    // on host port 8000. A physical device on the demo Wi-Fi needs the
    // host's real LAN IP instead, same "companion-phone on the same
    // network" pattern MVP-PLAN.md §2② already established for SMS.
    private const val BASE_URL = "http://10.0.2.2:8000/"

    @Provides
    @Singleton
    fun provideJson(): Json = Json { ignoreUnknownKeys = true }

    @Provides
    @Singleton
    fun provideOkHttpClient(): OkHttpClient =
        OkHttpClient.Builder()
            .addInterceptor(HttpLoggingInterceptor().apply { level = HttpLoggingInterceptor.Level.BASIC })
            .build()

    @Provides
    @Singleton
    fun provideRetrofit(client: OkHttpClient, json: Json): Retrofit =
        Retrofit.Builder()
            .baseUrl(BASE_URL)
            .client(client)
            .addConverterFactory(json.asConverterFactory("application/json".toMediaType()))
            .build()

    @Provides
    @Singleton
    fun provideRrxApi(retrofit: Retrofit): RrxApi = retrofit.create(RrxApi::class.java)
}
