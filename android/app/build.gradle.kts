plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
    id("org.jetbrains.kotlin.plugin.serialization")
    id("com.google.devtools.ksp")
    id("com.google.dagger.hilt.android")
}

android {
    namespace = "com.rrx.app"
    // PRD.md §12.1: "API 26 covers the low-end install base that is the
    // entire point of this project."
    compileSdk = 35

    defaultConfig {
        applicationId = "com.rrx.app"
        minSdk = 26
        targetSdk = 35
        versionCode = 1
        versionName = "0.1.0-scaffold"
    }

    buildFeatures {
        compose = true
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }

    buildTypes {
        release {
            isMinifyEnabled = false // R8 tuning deferred past this scaffold
        }
    }

    // core-detection's bundled .tflite must stay uncompressed in the APK --
    // the TFLite interpreter mmaps it directly (zero-copy), which a
    // compressed asset entry doesn't support.
    androidResources {
        noCompress += "tflite"
    }
}

dependencies {
    implementation(project(":core-sensing"))
    implementation(project(":core-detection"))
    implementation(project(":core-transport"))
    implementation(project(":core-data"))

    implementation(platform("androidx.compose:compose-bom:2024.09.03"))
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.ui:ui-tooling-preview")
    implementation("androidx.activity:activity-compose:1.9.2")
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.8.6")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.8.6")
    // DriveViewModel talks to core-sensing's DriveSensingBus (a StateFlow)
    // directly -- declared explicitly rather than relying on it resolving
    // transitively through Compose's own dependency graph.
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.9.0")

    implementation("com.google.dagger:hilt-android:2.52")
    ksp("com.google.dagger:hilt-android-compiler:2.52")
    implementation("androidx.hilt:hilt-navigation-compose:1.2.0")

    // PRD.md §12.1: Retrofit 2 + OkHttp 4 + kotlinx.serialization.
    implementation("com.squareup.retrofit2:retrofit:2.11.0")
    implementation("com.jakewharton.retrofit:retrofit2-kotlinx-serialization-converter:1.0.0")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("com.squareup.okhttp3:logging-interceptor:4.12.0")
    implementation("org.jetbrains.kotlinx:kotlinx-serialization-json:1.7.3")

    debugImplementation("androidx.compose.ui:ui-tooling")
}
