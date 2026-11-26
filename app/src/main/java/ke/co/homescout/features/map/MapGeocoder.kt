package ke.co.homescout.features.map

import ke.co.homescout.data.remote.ApiConfiguration
import org.json.JSONArray
import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL
import java.net.URLEncoder

data class GeocodedPlace(
    val id: String,
    val name: String,
    val label: String,
    val latitude: Double,
    val longitude: Double
)

/** Uses the backend's switchable low-volume provider and caches recent user-submitted searches in memory. */
class MapGeocoder {
    fun searchKenya(input: String): List<GeocodedPlace> {
        val query = input.trim().take(120)
        require(query.length >= 2) { "Enter a county, town, or neighbourhood to search." }
        val key = query.lowercase()
        synchronized(cache) { cache[key]?.let { return it } }

        val baseUrl = ApiConfiguration.versionedBaseUrl
            ?: throw IOException("The HomeScout API address is not configured for area search.")
        val encoded = URLEncoder.encode(query, Charsets.UTF_8.name())
        val connection = (URL("${baseUrl}locations/map-search?q=$encoded")
            .openConnection() as HttpURLConnection).apply {
            requestMethod = "GET"
            connectTimeout = 10_000
            readTimeout = 12_000
            setRequestProperty("Accept", "application/json")
        }
        try {
            val status = connection.responseCode
            val body = (if (status in 200..299) connection.inputStream else connection.errorStream)
                ?.bufferedReader(Charsets.UTF_8)?.use { it.readText() }.orEmpty()
            if (status !in 200..299) {
                val detail = runCatching {
                    org.json.JSONObject(body).optJSONObject("error")?.optString("message")
                }.getOrNull()?.takeIf(String::isNotBlank)
                throw IOException(detail ?: "Area search is unavailable. Check your connection and try again.")
            }
            val rows = JSONArray(body)
            val results = buildList {
                for (index in 0 until rows.length()) {
                    val row = rows.optJSONObject(index) ?: continue
                    val latitude = row.optString("latitude").toDoubleOrNull() ?: continue
                    val longitude = row.optString("longitude").toDoubleOrNull() ?: continue
                    if (latitude !in -90.0..90.0 || longitude !in -180.0..180.0) continue
                    val display = row.optString("label").trim()
                    add(
                        GeocodedPlace(
                            id = row.optString("id").ifBlank { "$latitude:$longitude" },
                            name = row.optString("name").ifBlank { display.substringBefore(',').ifBlank { "Kenyan location" } },
                            label = display,
                            latitude = latitude,
                            longitude = longitude
                        )
                    )
                }
            }
            synchronized(cache) {
                cache[key] = results
                while (cache.size > CACHE_LIMIT) cache.remove(cache.keys.first())
            }
            return results
        } finally {
            connection.disconnect()
        }
    }

    private companion object {
        const val CACHE_LIMIT = 40
        val cache = LinkedHashMap<String, List<GeocodedPlace>>()
    }
}
