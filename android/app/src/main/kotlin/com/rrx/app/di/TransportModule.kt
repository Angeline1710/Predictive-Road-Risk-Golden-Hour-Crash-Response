package com.rrx.app.di

import android.content.Context
import com.rrx.coretransport.AlertApi
import com.rrx.coretransport.AlertTransport
import com.rrx.coretransport.SmsSender
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import retrofit2.Retrofit
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object TransportModule {

    @Provides
    @Singleton
    fun provideAlertApi(retrofit: Retrofit): AlertApi = retrofit.create(AlertApi::class.java)

    @Provides
    @Singleton
    fun provideSmsSender(@ApplicationContext context: Context): SmsSender = SmsSender(context)

    @Provides
    @Singleton
    fun provideAlertTransport(
        @ApplicationContext context: Context,
        alertApi: AlertApi,
        smsSender: SmsSender,
    ): AlertTransport = AlertTransport(
        context = context,
        alertApi = alertApi,
        smsSender = smsSender,
        baseUrl = AppConfig.BASE_URL,
        smsDestination = AppConfig.SMS_DESTINATION_PLACEHOLDER,
    )
}
