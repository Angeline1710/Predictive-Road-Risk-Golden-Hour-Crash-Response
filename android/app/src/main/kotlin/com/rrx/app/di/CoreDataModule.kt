package com.rrx.app.di

import android.content.Context
import androidx.room.Room
import com.rrx.coredata.EmergencyContactDao
import com.rrx.coredata.OnboardingStore
import com.rrx.coredata.RrxDatabase
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

/** core-data has no Hilt dependency of its own -- same pattern as
 * core-sensing/core-detection/core-transport, all plain Kotlin/Android
 * libraries wired up from `app`'s DI layer instead. */
@Module
@InstallIn(SingletonComponent::class)
object CoreDataModule {

    @Provides
    @Singleton
    fun provideRrxDatabase(@ApplicationContext context: Context): RrxDatabase =
        Room.databaseBuilder(context, RrxDatabase::class.java, "rrx.db").build()

    @Provides
    @Singleton
    fun provideEmergencyContactDao(database: RrxDatabase): EmergencyContactDao =
        database.emergencyContactDao()

    @Provides
    @Singleton
    fun provideOnboardingStore(@ApplicationContext context: Context): OnboardingStore =
        OnboardingStore(context)
}
