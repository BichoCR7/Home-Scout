package ke.co.homescout.data.remote

import ke.co.homescout.BuildConfig

/** Central, build-configured API address. No credentials belong in this client configuration. */
object ApiConfiguration {
    val baseUrl: String = BuildConfig.API_BASE_URL.trimEnd('/')

    val versionedBaseUrl: String?
        get() = baseUrl.takeIf(String::isNotBlank)?.let { "$it/api/v1/" }

    val isConfigured: Boolean
        get() = baseUrl.isNotBlank()
}
