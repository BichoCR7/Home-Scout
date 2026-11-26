package ke.co.homescout.data.remote

import org.json.JSONArray
import org.json.JSONObject
import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL
import java.net.URLEncoder

data class MarketplacePhoto(
    val url: String,
    val description: String?,
    val illustrative: Boolean,
    val position: Int
)

data class MarketplaceProperty(
    val id: String,
    val title: String,
    val description: String,
    val propertyType: String,
    val unitType: String,
    val rentAmount: String,
    val rentFrequency: String,
    val depositAmount: String?,
    val bedrooms: Int,
    val bathrooms: String,
    val sizeSqm: String?,
    val furnishing: String,
    val petPolicy: String,
    val amenities: List<String>,
    val securityFeatures: List<String>,
    val waterAvailability: String,
    val electricityAvailable: Boolean?,
    val internetAvailable: Boolean?,
    val location: String,
    val neighbourhood: String?,
    val countyId: String,
    val townId: String,
    val neighbourhoodId: String?,
    val latitude: String?,
    val longitude: String?,
    val verificationStatus: String,
    val availabilityStatus: String,
    val listingStatus: String,
    val demo: Boolean,
    val demoDisclaimer: String?,
    val photos: List<MarketplacePhoto>
) {
    val primaryPhoto: MarketplacePhoto?
        get() = photos.firstOrNull { !it.illustrative } ?: photos.firstOrNull()

    companion object {
        fun parse(value: JSONObject, baseUrl: String): MarketplaceProperty {
            val location = value.optJSONObject("location") ?: JSONObject()
            val items = value.optJSONArray("media") ?: JSONArray()
            val photos = buildList {
                for (index in 0 until items.length()) {
                    val item = items.optJSONObject(index) ?: continue
                    if (item.optString("media_type") != "image") continue
                    val rawUrl = item.optString("url").takeIf(String::isNotBlank) ?: continue
                    add(
                        MarketplacePhoto(
                            url = if (rawUrl.startsWith("/")) baseUrl.trimEnd('/') + rawUrl else rawUrl,
                            description = item.optString("alt_text").takeIf(String::isNotBlank),
                            illustrative = item.optBoolean("is_illustrative", false),
                            position = item.optInt("position", index)
                        )
                    )
                }
            }.sortedBy(MarketplacePhoto::position)
            val amenities = value.optJSONArray("amenities").asStringList()
            val security = value.optJSONArray("security_features").asStringList()
            val neighbourhood = location.optString("neighbourhood_name").takeIf(String::isNotBlank)
            val town = location.optString("town_name")
            val county = location.optString("county_name")
            return MarketplaceProperty(
                id = value.optString("id"),
                title = value.optString("title"),
                description = value.optString("description"),
                propertyType = value.optString("property_type"),
                unitType = value.optString("unit_type"),
                rentAmount = value.optString("rent_amount"),
                rentFrequency = value.optString("rent_frequency", "monthly"),
                depositAmount = value.optString("deposit_amount").takeIf(String::isNotBlank),
                bedrooms = value.optInt("bedrooms"),
                bathrooms = value.optString("bathrooms"),
                sizeSqm = value.optString("size_sqm").takeIf(String::isNotBlank),
                furnishing = value.optString("furnishing"),
                petPolicy = value.optString("pet_policy", "unknown"),
                amenities = amenities,
                securityFeatures = security,
                waterAvailability = value.optString("water_availability", "unknown"),
                electricityAvailable = value.nullableBoolean("electricity_available"),
                internetAvailable = value.nullableBoolean("internet_available"),
                location = listOfNotNull(neighbourhood, town, county).distinct().joinToString(", "),
                neighbourhood = neighbourhood,
                countyId = location.optString("county_id"),
                townId = location.optString("town_id"),
                neighbourhoodId = location.optString("neighbourhood_id").takeIf(String::isNotBlank),
                latitude = value.optString("latitude").takeIf(String::isNotBlank),
                longitude = value.optString("longitude").takeIf(String::isNotBlank),
                verificationStatus = value.optString("verification_status"),
                availabilityStatus = value.optString("availability_status"),
                listingStatus = value.optString("listing_status"),
                demo = value.optBoolean("is_demo", false),
                demoDisclaimer = value.optString("demo_disclaimer").takeIf(String::isNotBlank),
                photos = photos
            )
        }
    }
}

data class MarketplaceFilters(
    val query: String = "",
    val countyId: String? = null,
    val townId: String? = null,
    val neighbourhoodId: String? = null,
    val rentMin: String = "",
    val rentMax: String = "",
    val bedrooms: Int? = null,
    val bedroomsMin: Int? = null,
    val propertyType: String? = null,
    val furnishing: String? = null,
    val amenities: List<String> = emptyList(),
    val verifiedOnly: Boolean = false,
    val sortBy: String = "newest",
    val includeDemo: Boolean = false
) {
    fun queryString(): String = buildList {
        if (query.isNotBlank()) add("query=" + query.encode())
        countyId?.takeIf(String::isNotBlank)?.let { add("county_id=" + it.encode()) }
        townId?.takeIf(String::isNotBlank)?.let { add("town_id=" + it.encode()) }
        neighbourhoodId?.takeIf(String::isNotBlank)?.let { add("neighbourhood_id=" + it.encode()) }
        rentMin.toIntOrNull()?.takeIf { it > 0 }?.let { add("rent_min=" + it) }
        rentMax.toIntOrNull()?.takeIf { it > 0 }?.let { add("rent_max=" + it) }
        bedrooms?.let { add("bedrooms=" + it) }
        bedroomsMin?.let { add("bedrooms_min=" + it) }
        propertyType?.let { add("property_type=" + it.encode()) }
        furnishing?.let { add("furnishing=" + it.encode()) }
        amenities.filter(String::isNotBlank).forEach { add("amenities=" + it.encode()) }
        if (verifiedOnly) add("verified_only=true")
        if (includeDemo) add("include_demo=true")
        add("sort_by=" + sortBy.encode())
        add("limit=30")
    }.joinToString("&")

    fun asJson(): JSONObject = JSONObject().apply {
        if (query.isNotBlank()) put("query", query.trim())
        countyId?.takeIf(String::isNotBlank)?.let { put("county_id", it) }
        townId?.takeIf(String::isNotBlank)?.let { put("town_id", it) }
        neighbourhoodId?.takeIf(String::isNotBlank)?.let { put("neighbourhood_id", it) }
        rentMin.toIntOrNull()?.takeIf { it > 0 }?.let { put("rent_min", it) }
        rentMax.toIntOrNull()?.takeIf { it > 0 }?.let { put("rent_max", it) }
        bedrooms?.let { put("bedrooms", it) }
        bedroomsMin?.let { put("bedrooms_min", it) }
        propertyType?.let { put("property_type", it) }
        furnishing?.let { put("furnishing", it) }
        put("amenities", JSONArray(amenities.filter(String::isNotBlank)))
        put("verified_only", verifiedOnly)
        put("sort_by", sortBy)
    }
}

data class MarketplaceLocation(
    val id: String,
    val kind: String,
    val name: String,
    val countyId: String,
    val countyName: String,
    val townId: String?,
    val townName: String?,
    val neighbourhoodId: String?
)

data class MarketplaceCounty(val id: String, val code: String, val name: String)
data class MarketplaceTown(val id: String, val countyId: String, val name: String, val kind: String)
data class MarketplaceNeighbourhood(val id: String, val townId: String, val name: String)

class MarketplaceApiException(message: String) : IOException(message)

/** REST access for marketplace data. Addresses stay centralized and credentials stay runtime-only. */
class MarketplaceApi {
    private val versionedBase = ApiConfiguration.versionedBaseUrl
        ?: throw MarketplaceApiException("The HomeScout API address is not configured.")

    private val apiOrigin = ApiConfiguration.baseUrl

    fun search(filters: MarketplaceFilters): List<MarketplaceProperty> {
        val response = request("GET", "properties?" + filters.queryString())
        val items = response.optJSONArray("items") ?: JSONArray()
        return buildList {
            for (index in 0 until items.length()) {
                items.optJSONObject(index)?.let { add(MarketplaceProperty.parse(it, apiOrigin)) }
            }
        }
    }

    fun property(propertyId: String, includeDemo: Boolean = false): MarketplaceProperty =
        MarketplaceProperty.parse(
            request(
                "GET",
                "properties/" + propertyId.encode() + if (includeDemo) "?include_demo=true" else ""
            ),
            apiOrigin
        )

    fun preview(propertyId: String, token: String): MarketplaceProperty =
        MarketplaceProperty.parse(
            request("GET", "properties/" + propertyId.encode() + "/preview", token = token),
            apiOrigin
        )

    fun similar(propertyId: String): List<MarketplaceProperty> {
        val items = request("GET", "properties/" + propertyId.encode() + "/similar?limit=6")
            .optJSONArray("items") ?: JSONArray()
        return buildList {
            for (index in 0 until items.length()) {
                items.optJSONObject(index)?.let { add(MarketplaceProperty.parse(it, apiOrigin)) }
            }
        }
    }

    fun save(propertyId: String, token: String, saved: Boolean) {
        request(
            if (saved) "PUT" else "DELETE",
            "marketplace/saved/" + propertyId.encode(),
            token = token,
            expectJson = false
        )
    }

    fun compare(propertyIds: List<String>, token: String, includeDemo: Boolean = false): List<MarketplaceProperty> {
        val items = request(
            "POST",
            "marketplace/compare" + if (includeDemo) "?include_demo=true" else "",
            token = token,
            body = JSONArray(propertyIds).toString()
        ).asJsonArray()
        return buildList {
            for (index in 0 until items.length()) {
                items.optJSONObject(index)?.let { add(MarketplaceProperty.parse(it, apiOrigin)) }
            }
        }
    }

    fun createEnquiry(propertyId: String, token: String, message: String): String =
        request(
            "POST",
            "marketplace/properties/" + propertyId.encode() + "/enquiries",
            token = token,
            body = JSONObject().put("message", message).toString()
        ).optString("id")

    fun report(propertyId: String, token: String, reason: String, details: String): String {
        val body = JSONObject().put("reason", reason)
        if (details.isNotBlank()) body.put("details", details)
        return request(
            "POST",
            "marketplace/properties/" + propertyId.encode() + "/reports",
            token = token,
            body = body.toString()
        ).optString("status")
    }

    fun saveSearchAlert(filters: MarketplaceFilters, token: String) {
        request(
            "POST",
            "marketplace/alerts",
            token = token,
            body = JSONObject().put("filters", filters.asJson()).toString()
        )
    }

    fun recordSearch(filters: MarketplaceFilters, resultCount: Int, token: String) {
        request(
            "POST",
            "marketplace/search-history",
            token = token,
            body = JSONObject()
                .put("filters", filters.asJson())
                .put("result_count", resultCount)
                .toString()
        )
    }

    fun myListings(token: String): List<MarketplaceProperty> {
        val items = request("GET", "properties/mine", token = token).asJsonArray()
        return buildList {
            for (index in 0 until items.length()) {
                items.optJSONObject(index)?.let { add(MarketplaceProperty.parse(it, apiOrigin)) }
            }
        }
    }

    fun savedPropertyIds(token: String): Set<String> {
        val items = request("GET", "marketplace/saved", token = token).optJSONArray("items")
            ?: return emptySet()
        return buildSet {
            for (index in 0 until items.length()) {
                items.optJSONObject(index)?.optString("id")?.takeIf(String::isNotBlank)?.let(::add)
            }
        }
    }

    fun savedProperties(token: String): List<MarketplaceProperty> {
        val items = request("GET", "marketplace/saved", token = token).optJSONArray("items")
            ?: return emptyList()
        return buildList {
            for (index in 0 until items.length()) {
                items.optJSONObject(index)?.let { add(MarketplaceProperty.parse(it, apiOrigin)) }
            }
        }
    }

    fun searchLocations(query: String): List<MarketplaceLocation> {
        val items = request("GET", "locations/search?q=" + query.encode()).asJsonArray()
        return buildList {
            for (index in 0 until items.length()) {
                val item = items.optJSONObject(index) ?: continue
                add(
                    MarketplaceLocation(
                        id = item.optString("id"),
                        kind = item.optString("kind"),
                        name = item.optString("name"),
                        countyId = item.optString("county_id"),
                        countyName = item.optString("county_name"),
                        townId = item.optString("town_id").takeIf(String::isNotBlank)
                            ?: item.optString("id").takeIf { item.optString("kind") == "town" },
                        townName = item.optString("town_name").takeIf(String::isNotBlank),
                        neighbourhoodId = item.optString("neighbourhood_id").takeIf(String::isNotBlank)
                            ?: item.optString("id").takeIf { item.optString("kind") == "neighbourhood" }
                    )
                )
            }
        }
    }

    fun counties(): List<MarketplaceCounty> {
        val rows = request("GET", "locations/counties").asJsonArray()
        return buildList {
            for (index in 0 until rows.length()) {
                val row = rows.optJSONObject(index) ?: continue
                val county = MarketplaceCounty(row.optString("id"), row.optString("code"), row.optString("name"))
                if (county.id.isNotBlank() && county.name.isNotBlank()) add(county)
            }
        }
    }

    fun towns(countyId: String): List<MarketplaceTown> {
        val rows = request("GET", "locations/counties/" + countyId.encode() + "/towns").asJsonArray()
        return buildList {
            for (index in 0 until rows.length()) {
                val row = rows.optJSONObject(index) ?: continue
                val town = MarketplaceTown(row.optString("id"), row.optString("county_id", countyId), row.optString("name"), row.optString("kind"))
                if (town.id.isNotBlank() && town.name.isNotBlank()) add(town)
            }
        }
    }

    fun neighbourhoods(townId: String): List<MarketplaceNeighbourhood> {
        val rows = request("GET", "locations/towns/" + townId.encode() + "/neighbourhoods").asJsonArray()
        return buildList {
            for (index in 0 until rows.length()) {
                val row = rows.optJSONObject(index) ?: continue
                val neighbourhood = MarketplaceNeighbourhood(row.optString("id"), row.optString("town_id", townId), row.optString("name"))
                if (neighbourhood.id.isNotBlank() && neighbourhood.name.isNotBlank()) add(neighbourhood)
            }
        }
    }

    fun updateDraft(propertyId: String, token: String, title: String, description: String, rent: String) {
        request(
            "PATCH",
            "properties/" + propertyId.encode(),
            token = token,
            body = JSONObject()
                .put("title", title)
                .put("description", description)
                .put("rent_amount", rent)
                .toString()
        )
    }

    fun createDraft(token: String, body: JSONObject): MarketplaceProperty =
        MarketplaceProperty.parse(request("POST", "properties", token = token, body = body.toString()), apiOrigin)

    fun updateAvailability(propertyId: String, token: String, available: Boolean) {
        request(
            "PATCH",
            "properties/" + propertyId.encode() + "/availability",
            token = token,
            body = JSONObject()
                .put("availability_status", if (available) "available" else "unavailable")
                .toString()
        )
    }

    fun publish(propertyId: String, token: String) {
        request("POST", "properties/" + propertyId.encode() + "/publish", token = token)
    }

    fun archive(propertyId: String, token: String) {
        request("POST", "properties/" + propertyId.encode() + "/archive", token = token)
    }

    fun uploadImage(propertyId: String, token: String, mimeType: String, image: ByteArray) {
        request(
            "POST",
            "properties/" + propertyId.encode() + "/media",
            token = token,
            bodyBytes = image,
            contentType = mimeType
        )
    }

    fun deleteDraft(propertyId: String, token: String) {
        request("DELETE", "properties/" + propertyId.encode(), token = token, expectJson = false)
    }

    private fun request(
        method: String,
        path: String,
        token: String? = null,
        body: String? = null,
        bodyBytes: ByteArray? = null,
        contentType: String = "application/json",
        expectJson: Boolean = true
    ): JSONObject {
        val connection = (URL(versionedBase + path).openConnection() as HttpURLConnection).apply {
            requestMethod = method
            connectTimeout = 12_000
            readTimeout = 20_000
            setRequestProperty("Accept", "application/json")
            token?.let { setRequestProperty("Authorization", "Bearer " + it) }
            if (body != null || bodyBytes != null) {
                doOutput = true
                setRequestProperty("Content-Type", contentType)
            }
        }
        try {
            if (body != null || bodyBytes != null) {
                connection.outputStream.use { stream ->
                    if (bodyBytes != null) stream.write(bodyBytes) else stream.write(body!!.toByteArray())
                }
            }
            val status = connection.responseCode
            if (status !in 200..299) {
                val error = connection.errorStream?.bufferedReader(Charsets.UTF_8)?.use { it.readText() }.orEmpty()
                val message = runCatching {
                    JSONObject(error).optJSONObject("error")?.optString("message")
                }.getOrNull()?.takeIf(String::isNotBlank)
                throw MarketplaceApiException(message ?: "The HomeScout request failed (" + status + ").")
            }
            if (!expectJson || status == HttpURLConnection.HTTP_NO_CONTENT) return JSONObject()
            val response = connection.inputStream.bufferedReader(Charsets.UTF_8).use { it.readText() }
            return if (response.trimStart().startsWith("[")) {
                JSONObject().put("_array", JSONArray(response))
            } else {
                JSONObject(response)
            }
        } finally {
            connection.disconnect()
        }
    }

    private fun JSONObject.asJsonArray(): JSONArray = optJSONArray("_array") ?: JSONArray()
}

private fun String.encode(): String = URLEncoder.encode(this, Charsets.UTF_8.name())

private fun JSONArray?.asStringList(): List<String> {
    if (this == null) return emptyList()
    return buildList {
        for (index in 0 until length()) optString(index).takeIf(String::isNotBlank)?.let(::add)
    }
}

private fun JSONObject.nullableBoolean(name: String): Boolean? =
    if (isNull(name)) null else optBoolean(name)
