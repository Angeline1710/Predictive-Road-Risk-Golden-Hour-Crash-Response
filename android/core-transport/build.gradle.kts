plugins {
    id("com.android.library")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.serialization")
}

android {
    namespace = "com.rrx.coretransport"
    compileSdk = 35
    defaultConfig { minSdk = 26 }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }
}

dependencies {
    // PRD.md §12.1: Retrofit 2 + OkHttp 4 + kotlinx.serialization -- matches
    // app/build.gradle.kts's versions exactly, since both talk to the same
    // backend contract.
    implementation("com.squareup.retrofit2:retrofit:2.11.0")
    implementation("com.jakewharton.retrofit:retrofit2-kotlinx-serialization-converter:1.0.0")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("org.jetbrains.kotlinx:kotlinx-serialization-json:1.7.3")

    // PRD.md §12.1: WorkManager 2.9 -- "the only reliable way to run
    // continuous sensing on modern Android" applies just as much to
    // guaranteed-delivery retry of a crash alert.
    implementation("androidx.work:work-runtime-ktx:2.9.1")

    implementation("androidx.core:core-ktx:1.13.1")

    testImplementation("junit:junit:4.13.2")
}
