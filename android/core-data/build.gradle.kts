plugins {
    id("com.android.library")
    id("org.jetbrains.kotlin.android")
    id("com.google.devtools.ksp")
}

android {
    namespace = "com.rrx.coredata"
    compileSdk = 35
    defaultConfig { minSdk = 26 }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }
}

dependencies {
    // Emergency contacts -- a small ordered list of records is a natural
    // Room fit, not worth hand-rolling list (de)serialization for.
    implementation("androidx.room:room-runtime:2.6.1")
    implementation("androidx.room:room-ktx:2.6.1")
    ksp("androidx.room:room-compiler:2.6.1")

    // PRD.md §12.6: "EncryptedSharedPreferences-backed token/medical-info
    // storage." 1.1.0-alpha06 is the latest release of the 1.1 line PRD
    // names -- security-crypto has stayed pre-1.0-stable for years, this
    // is not a version typo.
    implementation("androidx.security:security-crypto:1.1.0-alpha06")

    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.9.0")
}
