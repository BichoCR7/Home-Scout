package ke.co.homescout.data.remote

import org.json.JSONArray
import org.json.JSONObject
import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL
import java.net.URLEncoder

/** Authenticated HomeScout personal hub calls using the same configured API root as identity. */
class PersonalHubApi {
    fun getObject(path: String, token: String): JSONObject = JSONObject(request(path, "GET", token))

    fun getPublicObject(path: String): JSONObject = JSONObject(request(path, "GET", null))

    fun getArray(path: String, token: String): JSONArray = JSONArray(request(path, "GET", token))

    fun send(
        path: String,
        method: String,
        token: String,
        body: JSONObject? = null,
        headers: Map<String, String> = emptyMap()
    ): JSONObject {
        val response = request(path, method, token, body, extraHeaders = headers)
        return if (response.isBlank()) JSONObject() else JSONObject(response)
    }

    fun raw(path: String, token: String): String = request(path, "GET", token)

    fun upload(path: String, token: String, contents: ByteArray): String =
        request(path, "POST", token, bytes = contents)

    fun download(path: String, token: String): ByteArray {
        return withSessionRefresh(token) { currentToken ->
            val baseUrl = ApiConfiguration.versionedBaseUrl
                ?: throw AuthApiException(0, "api_not_configured", "Connect the HomeScout API to download this file.")
            val connection = (URL(baseUrl + path).openConnection() as HttpURLConnection).apply {
                requestMethod = "GET"
                connectTimeout = 12_000
                readTimeout = 20_000
                setRequestProperty("Authorization", "Bearer $currentToken")
            }
            try {
                val status = connection.responseCode
                if (status !in 200..299) {
                    val response = connection.errorStream?.bufferedReader()?.use { it.readText() }.orEmpty()
                    val error = runCatching { JSONObject(response).optJSONObject("error") }.getOrNull()
                    throw AuthApiException(
                        status,
                        error?.optString("code").orEmpty(),
                        error?.optString("message")?.takeIf(String::isNotBlank)
                            ?: "HomeScout could not download that file."
                    )
                }
                connection.inputStream.use { it.readBytes() }
            } finally {
                connection.disconnect()
            }
        }
    }

    private fun request(
        path: String,
        method: String,
        token: String?,
        body: JSONObject? = null,
        bytes: ByteArray? = null,
        extraHeaders: Map<String, String> = emptyMap()
    ): String = if (token.isNullOrBlank()) {
        requestRawOnce(path, method, token, body, bytes, extraHeaders)
    } else {
        withSessionRefresh(token) { currentToken ->
            requestRawOnce(path, method, currentToken, body, bytes, extraHeaders)
        }
    }

    private fun requestRawOnce(
        path: String,
        method: String,
        token: String?,
        body: JSONObject? = null,
        bytes: ByteArray? = null,
        extraHeaders: Map<String, String> = emptyMap()
    ): String {
        val baseUrl = ApiConfiguration.versionedBaseUrl
            ?: throw AuthApiException(0, "api_not_configured", "Connect the HomeScout API to use this account feature.")
        val connection = (URL(baseUrl + path).openConnection() as HttpURLConnection).apply {
            requestMethod = method
            connectTimeout = 12_000
            readTimeout = 20_000
            setRequestProperty("Accept", "application/json")
            if (!token.isNullOrBlank()) setRequestProperty("Authorization", "Bearer $token")
            if (body != null) setRequestProperty("Content-Type", "application/json; charset=utf-8")
            if (bytes != null) setRequestProperty("Content-Type", "application/octet-stream")
            extraHeaders.forEach { (name, value) -> setRequestProperty(name, value) }
            if (body != null || bytes != null) doOutput = true
        }
        try {
            if (body != null) connection.outputStream.use { it.write(body.toString().toByteArray()) }
            if (bytes != null) connection.outputStream.use { it.write(bytes) }
            val status = connection.responseCode
            val stream = if (status in 200..299) connection.inputStream else connection.errorStream
            val response = stream?.bufferedReader(Charsets.UTF_8)?.use { it.readText() }.orEmpty()
            if (status !in 200..299) {
                val error = runCatching { JSONObject(response).optJSONObject("error") }.getOrNull()
                throw AuthApiException(
                    status,
                    error?.optString("code").orEmpty(),
                    error?.optString("message")?.takeIf(String::isNotBlank)
                        ?: "HomeScout could not complete that request. Try again."
                )
            }
            return response
        } catch (error: AuthApiException) {
            throw error
        } catch (_: IOException) {
            throw IOException("HomeScout could not reach the account service. Check your connection and try again.")
        } finally {
            connection.disconnect()
        }
    }

    private fun <T> withSessionRefresh(token: String, request: (String) -> T): T {
        try {
            return request(token)
        } catch (failure: AuthApiException) {
            if (failure.statusCode != 401) throw failure
            val refreshed = AuthenticatedSession.refresh(token) ?: throw failure
            if (refreshed == token) throw failure
            return request(refreshed)
        }
    }

    companion object {
        fun query(value: String): String = URLEncoder.encode(value, Charsets.UTF_8.name())
    }
}
