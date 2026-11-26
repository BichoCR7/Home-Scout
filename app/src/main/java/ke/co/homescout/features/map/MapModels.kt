package ke.co.homescout.features.map

import org.json.JSONObject
import java.net.URLEncoder

data class MapViewport(
    val south: Double,
    val west: Double,
    val north: Double,
    val east: Double
) {
    init {
        require(south in -90.0..90.0 && north in -90.0..90.0 && south < north)
        require(west in -180.0..180.0 && east in -180.0..180.0)
    }
}

data class MapFilters(
    val minRent: String = "",
    val maxRent: String = "",
    val propertyType: String? = null,
    val bedrooms: Int? = null,
    val bedroomsAtLeast: Boolean = false,
    val furnishing: String? = null,
    val verifiedOnly: Boolean = false
) {
    fun validated(): MapFilters {
        val min = minRent.toIntOrNull()
        val max = maxRent.toIntOrNull()
        require(minRent.isBlank() || min != null && min > 0) { "Enter a valid minimum rent." }
        require(maxRent.isBlank() || max != null && max > 0) { "Enter a valid maximum rent." }
        require(min == null || max == null || min <= max) { "Minimum rent must not exceed maximum rent." }
        return copy(minRent = min?.toString().orEmpty(), maxRent = max?.toString().orEmpty())
    }

    fun queryParameters(viewport: MapViewport): String {
        val filters = validated()
        val params = linkedMapOf(
            "south" to viewport.south.toString(),
            "west" to viewport.west.toString(),
            "north" to viewport.north.toString(),
            "east" to viewport.east.toString(),
            "limit" to "100"
        )
        filters.minRent.takeIf(String::isNotBlank)?.let { params["rent_min"] = it }
        filters.maxRent.takeIf(String::isNotBlank)?.let { params["rent_max"] = it }
        filters.propertyType?.let { params["property_type"] = it }
        filters.bedrooms?.let { params[if (filters.bedroomsAtLeast) "bedrooms_min" else "bedrooms"] = it.toString() }
        filters.furnishing?.let { params["furnishing"] = it }
        if (filters.verifiedOnly) params["verified_only"] = "true"
        return params.entries.joinToString("&") { (key, value) ->
            "${encode(key)}=${encode(value)}"
        }
    }

    companion object {
        private fun encode(value: String): String = URLEncoder.encode(value, Charsets.UTF_8.name())
    }
}

data class MapListing(
    val id: String,
    val title: String,
    val rentAmount: Int,
    val rentFrequency: String,
    val bedrooms: Int,
    val bathrooms: String,
    val furnishing: String,
    val propertyType: String,
    val townName: String,
    val neighbourhoodName: String?,
    val latitude: Double,
    val longitude: Double,
    val verified: Boolean
) {
    val locationLabel: String
        get() = listOfNotNull(neighbourhoodName, townName).distinct().joinToString(", ")

    companion object {
        fun fromJson(json: JSONObject): MapListing? {
            if (json.optBoolean("is_demo") || json.optString("listing_status") != "published") return null
            if (json.optString("availability_status") != "available") return null
            if (json.isNull("latitude") || json.isNull("longitude") || json.isNull("coordinate_source")) return null

            val location = json.optJSONObject("location") ?: return null
            val latitude = json.optString("latitude").toDoubleOrNull() ?: return null
            val longitude = json.optString("longitude").toDoubleOrNull() ?: return null
            if (latitude !in -90.0..90.0 || longitude !in -180.0..180.0) return null

            return MapListing(
                id = json.optString("id").takeIf(String::isNotBlank) ?: return null,
                title = json.optString("title").ifBlank { "Home listing" },
                rentAmount = json.optString("rent_amount").toDoubleOrNull()?.toInt() ?: return null,
                rentFrequency = json.optString("rent_frequency").ifBlank { "monthly" },
                bedrooms = json.optInt("bedrooms"),
                bathrooms = json.optString("bathrooms"),
                furnishing = json.optString("furnishing"),
                propertyType = json.optString("property_type"),
                townName = location.optString("town_name").ifBlank { "Kenya" },
                neighbourhoodName = location.optString("neighbourhood_name")
                    .takeIf { !location.isNull("neighbourhood_name") && it.isNotBlank() },
                latitude = latitude,
                longitude = longitude,
                verified = json.optString("verification_status") == "verified"
            )
        }
    }
}

data class NearbyPlace(val id: String, val name: String, val latitude: Double, val longitude: Double)

enum class NearbyCategory(val label: String, val placeTypes: List<String>) {
    Schools("Schools", listOf("school")),
    Healthcare("Healthcare", listOf("hospital", "pharmacy")),
    Transit("Transit", listOf("transit_station")),
    Shopping("Shopping", listOf("supermarket", "shopping_mall"))
}

fun openFreeMapStyleUrl(styleName: String): String {
    require(styleName in setOf("liberty", "bright", "positron", "dark")) {
        "Unsupported OpenFreeMap style."
    }
    return "https://tiles.openfreemap.org/styles/$styleName"
}

fun formatKes(amount: Int): String = "KSh ${"%,d".format(amount)}"
