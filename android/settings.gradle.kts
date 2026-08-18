pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}

dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
    }
}

rootProject.name = "rrx-app"

// PRD.md §12.6's module layout. Only `app` and `core-data` have real code
// in this scaffold (task #18, MVP-PLAN.md §3.3) -- core-sensing,
// core-detection, and core-transport are declared now so the module
// boundaries are right from day one, but each is a placeholder until the
// ~21 person-days of sensing/TFLite/transport work in §3.3 happens.
include(":app")
include(":core-sensing")
include(":core-detection")
include(":core-transport")
include(":core-data")
