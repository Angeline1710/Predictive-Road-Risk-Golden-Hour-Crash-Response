plugins {
    id("com.android.library")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "com.rrx.coredetection"
    compileSdk = 35
    defaultConfig { minSdk = 26 }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }
}

dependencies {
    // PRD.md §12.1 pins TensorFlow Lite 2.16 for the on-device runtime.
    implementation("org.tensorflow:tensorflow-lite:2.16.1")

    testImplementation("junit:junit:4.13.2")
}
