package ke.co.homescout.features.map

import ke.co.homescout.data.remote.ApiConfiguration
import org.json.JSONObject
import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL

class MapApiException(message: String) : IOException(message)

class MapPropertyApi {
    fun search(viewport: MapViewport, filters: MapFilters): List<MapListing> {
        val baseUrl = ApiConfiguration.versionedBaseUrl
            ?: throw MapApiException("The HomeScout API address is not configured.")
        val connection = (URL("${baseUrl}properties?${filters.queryParameters(viewport)}")
            .openConnection() as HttpURLConnection).apply {
            requestMethod = "GET"
            connectTimeout = 12_000
            readTimeout = 12_000
            setRequestProperty("Accept", "application/json")
        }
        try {
            val status = connection.responseCode
            val stream = if (status in 200..299) connection.inputStream else connection.errorStream
            val body = stream?.bufferedReader(Charsets.UTF_8)?.use { it.readText() }.orEmpty()
            if (status !in 200..299) {
                val message = runCatching {
                    JSONObject(body).optJSONObject("error")?.optString("message")
                }.getOrNull()?.takeIf(String::isNotBlank)
                throw MapApiException(message ?: "Homes in this area could not be loaded.")
            }
            val items = JSONObject(body).optJSONArray("items") ?: return emptyList()
            return buildList {
                for (index in 0 until items.length()) {
                    MapListing.fromJson(items.optJSONObject(index) ?: continue)?.let(::add)
                }
            }
        } finally {
            connection.disconnect()
        }
    }
}
