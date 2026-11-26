import org.jetbrains.kotlin.gradle.dsl.JvmTarget

import java.io.File
import java.net.URI
import java.util.Properties

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
}

val developerLocalProperties = Properties().apply {
    rootProject.file("local.properties")
        .takeIf(File::isFile)
        ?.inputStream()
        ?.use(::load)
}
val configuredApiBaseUrl = providers.gradleProperty("homescout.apiBaseUrl")
    .orElse(providers.environmentVariable("HOMESCOUT_API_BASE_URL"))
    .orElse(developerLocalProperties.getProperty("homescout.apiBaseUrl") ?: "")
    .get()
val versionCodeText = providers.gradleProperty("homescout.versionCode")
    .orElse(providers.environmentVariable("HOMESCOUT_VERSION_CODE"))
    .orElse("1")
    .get()
val homeScoutVersionCode = versionCodeText.toIntOrNull()
    ?.takeIf { it in 1..2_100_000_000 }
    ?: throw GradleException("HomeScout versionCode must be a positive Android version code.")
val homeScoutVersionName = providers.gradleProperty("homescout.versionName")
    .orElse(providers.environmentVariable("HOMESCOUT_VERSION_NAME"))
    .orElse("0.1.0")
    .get()
    .trim()
    .ifEmpty { throw GradleException("HomeScout versionName must not be blank.") }

val releaseSigning = mapOf(
    "HOMESCOUT_RELEASE_STORE_FILE" to providers.environmentVariable("HOMESCOUT_RELEASE_STORE_FILE").orNull,
    "HOMESCOUT_RELEASE_STORE_PASSWORD" to providers.environmentVariable("HOMESCOUT_RELEASE_STORE_PASSWORD").orNull,
    "HOMESCOUT_RELEASE_KEY_ALIAS" to providers.environmentVariable("HOMESCOUT_RELEASE_KEY_ALIAS").orNull,
    "HOMESCOUT_RELEASE_KEY_PASSWORD" to providers.environmentVariable("HOMESCOUT_RELEASE_KEY_PASSWORD").orNull,
)
val releaseSigningConfigured = releaseSigning.values.all { !it.isNullOrBlank() }

android {
    namespace = "ke.co.homescout"
    compileSdk = 37
    buildToolsVersion = "36.0.0"

    defaultConfig {
        applicationId = "ke.co.homescout"
        minSdk = 26
        targetSdk = 36
        versionCode = homeScoutVersionCode
        versionName = homeScoutVersionName

        val escapedApiBaseUrl = configuredApiBaseUrl
            .replace("\\", "\\\\")
            .replace("\"", "\\\"")
        buildConfigField("String", "API_BASE_URL", "\"$escapedApiBaseUrl\"")

    }

    if (releaseSigningConfigured) {
        signingConfigs {
            create("release") {
                storeFile = File(requireNotNull(releaseSigning["HOMESCOUT_RELEASE_STORE_FILE"]))
                storePassword = requireNotNull(releaseSigning["HOMESCOUT_RELEASE_STORE_PASSWORD"])
                keyAlias = requireNotNull(releaseSigning["HOMESCOUT_RELEASE_KEY_ALIAS"])
                keyPassword = requireNotNull(releaseSigning["HOMESCOUT_RELEASE_KEY_PASSWORD"])
            }
        }
    }

    buildTypes {
        debug {
            // Keep new side-by-side installs distinct from earlier preview builds.
            applicationIdSuffix = ".latest2"
            // The installed development build talks to the local API over adb reverse.
            // Production stays on HTTPS and never enables Android cleartext traffic.
            manifestPlaceholders["usesCleartextTraffic"] = "true"
            manifestPlaceholders["appLabel"] = "HomeScout Kenya Latest"
        }
        getByName("release") {
            manifestPlaceholders["usesCleartextTraffic"] = "false"
            manifestPlaceholders["appLabel"] = "HomeScout Kenya"
            if (releaseSigningConfigured) {
                signingConfig = signingConfigs.getByName("release")
            }
        }
    }

    buildFeatures {
        compose = true
        buildConfig = true
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}

val releasePreflight = tasks.register("preflightRelease") {
    group = "verification"
    description = "Rejects release packaging without signing and production API configuration."
    doLast {
        val missing = mutableListOf<String>()
        releaseSigning.filterValues { it.isNullOrBlank() }.keys.forEach(missing::add)
        val storePath = releaseSigning["HOMESCOUT_RELEASE_STORE_FILE"]
        if (!storePath.isNullOrBlank()) {
            val keystore = File(storePath)
            val keystorePath = keystore.canonicalFile.toPath()
            val checkoutPath = rootDir.canonicalFile.toPath()
            if (!keystore.isAbsolute || !keystore.isFile || keystorePath.startsWith(checkoutPath)) {
                missing += "HOMESCOUT_RELEASE_STORE_FILE (must be an existing absolute path outside the repository)"
            }
        }

        val apiUri = runCatching { URI(configuredApiBaseUrl) }.getOrNull()
        if (apiUri?.scheme != "https" || apiUri.host.isNullOrBlank() || apiUri.userInfo != null ||
            apiUri.query != null || apiUri.fragment != null
        ) {
            missing += "HOMESCOUT_API_BASE_URL (HTTPS origin/path required)"
        }

        if (missing.isNotEmpty()) {
            throw GradleException(
                "Release packaging blocked. Configure these values securely: ${missing.joinToString()}. " +
                    "No secret values were logged."
            )
        }
    }
}

tasks.configureEach {
    if (name in setOf("assembleRelease", "packageRelease", "bundleRelease")) {
        dependsOn(releasePreflight)
    }
}

kotlin {
    compilerOptions {
        jvmTarget.set(JvmTarget.JVM_17)
    }
}

dependencies {
    implementation("androidx.core:core-ktx:1.15.0")
    implementation("androidx.core:core-splashscreen:1.0.1")
    implementation("androidx.activity:activity-compose:1.10.0")
    implementation(platform("androidx.compose:compose-bom:2024.12.01"))
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.ui:ui-tooling-preview")
    implementation("androidx.compose.foundation:foundation")
    implementation("androidx.compose.animation:animation")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.material:material-icons-extended")
    implementation("androidx.navigation:navigation-compose:2.8.5")
    implementation("org.maplibre.gl:android-sdk:13.5.4")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("com.google.android.gms:play-services-location:21.3.0")
    testImplementation("junit:junit:4.13.2")
    testImplementation("org.json:json:20240303")
    debugImplementation("androidx.compose.ui:ui-tooling")
}
