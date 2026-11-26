package ke.co.homescout.data.remote

import org.json.JSONArray
import org.json.JSONObject
import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL
import java.net.URLEncoder

data class ServiceOffering(
    val id: String,
    val providerId: String,
    val providerName: String,
    val verification: String,
    val title: String,
    val category: String,
    val description: String,
    val pricingModel: String,
    val priceKes: String?,
    val areas: List<String>,
    val rating: Double?,
    val reviewCount: Int,
    val availableDays: List<String>,
    val active: Boolean
) {
    companion object {
        fun parse(json: JSONObject) = ServiceOffering(
            id = json.optString("id"),
            providerId = json.optString("provider_user_id"),
            providerName = json.optString("provider_name", "Service provider"),
            verification = json.optString("provider_verification_status", "not_submitted"),
            title = json.optString("title"),
            category = json.optString("category"),
            description = json.optString("description"),
            pricingModel = json.optString("pricing_model"),
            priceKes = json.optString("price_amount").takeIf(String::isNotBlank),
            areas = json.optJSONArray("service_areas").strings("town_name", "county_name"),
            rating = if (json.isNull("average_rating")) null else json.optDouble("average_rating"),
            reviewCount = json.optInt("review_count"),
            availableDays = json.optJSONObject("availability_schedule")?.keys()?.asSequence()
                ?.map { it.replaceFirstChar(Char::uppercase) }?.toList().orEmpty(),
            active = json.optBoolean("is_active")
        )
    }
}

data class ServiceBooking(
    val id: String,
    val orderId: String?,
    val offeringId: String,
    val offeringTitle: String,
    val providerId: String,
    val providerName: String,
    val requestedAt: String,
    val proposedAt: String?,
    val status: String,
    val customer: Boolean,
    val details: String,
    val estimatedAmount: String?
) {
    companion object {
        fun parse(json: JSONObject) = ServiceBooking(
            id = json.optString("id"),
            orderId = json.optString("order_id").takeIf(String::isNotBlank),
            offeringId = json.optString("offering_id"),
            offeringTitle = json.optString("offering_title"),
            providerId = json.optString("provider_user_id"),
            providerName = json.optString("provider_name"),
            requestedAt = json.optString("requested_at"),
            proposedAt = json.optString("proposed_at").takeIf(String::isNotBlank),
            status = json.optString("status"),
            customer = json.optBoolean("is_customer"),
            details = json.optString("request_details"),
            estimatedAmount = json.optString("estimated_amount_kes").takeIf(String::isNotBlank)
        )
    }
}

data class MovePlanSummary(val id: String, val title: String, val moveDate: String?, val budget: String?) {
    companion object {
        fun parse(json: JSONObject) = MovePlanSummary(
            id = json.optString("id"),
            title = json.optString("title"),
            moveDate = json.optString("move_date").takeIf(String::isNotBlank),
            budget = json.optString("target_budget_kes").takeIf(String::isNotBlank)
        )
    }
}

data class ServiceLocation(val id: String, val name: String) {
    companion object {
        fun parse(json: JSONObject) = ServiceLocation(json.optString("id"), json.optString("name"))
    }
}

data class ResidentProperty(val id: String, val title: String, val location: String) {
    companion object {
        fun parse(json: JSONObject) = ResidentProperty(
            json.optString("id"), json.optString("title"), json.optString("location")
        )
    }
}

class ServicesApiException(message: String) : IOException(message)

/** Authenticated and public HomeScout services endpoints; URL configuration is centralized. */
class ServicesApi {
    private val versionedBase = ApiConfiguration.versionedBaseUrl
        ?: throw ServicesApiException("The HomeScout API address is not configured.")

    fun search(
        query: String,
        category: String?,
        minPrice: String,
        maxPrice: String?,
        countyId: String? = null,
        verifiedOnly: Boolean = false
    ): List<ServiceOffering> {
        val params = mutableListOf("limit=50")
        if (query.isNotBlank()) params += "query=${query.encode()}"
        category?.let { params += "category=${it.encode()}" }
        minPrice.toDoubleOrNull()?.let { params += "min_price=$it" }
        maxPrice?.toDoubleOrNull()?.let { params += "max_price=$it" }
        countyId?.let { params += "county_id=${it.encode()}" }
        if (verifiedOnly) params += "verified_only=true"
        return requestArray("services/offerings?${params.joinToString("&")}")
            .objects().map(ServiceOffering::parse)
    }

    fun compare(ids: List<String>): List<ServiceOffering> = requestArray(
        "services/offerings/compare?" + ids.joinToString("&") { "service_ids=${it.encode()}" }
    ).objects().map(ServiceOffering::parse)

    fun createBooking(
        token: String,
        offeringId: String,
        requestedAt: String,
        details: String,
        timezone: String = "Africa/Nairobi"
    ): ServiceBooking = ServiceBooking.parse(
        requestObject(
            "POST", "services/bookings",
            body = JSONObject().put("offering_id", offeringId).put("requested_at", requestedAt)
                .put("timezone", timezone).put("request_details", details).toString(),
            token = token
        )
    )

    fun bookings(token: String): List<ServiceBooking> =
        requestArray("services/bookings", token = token).objects().map(ServiceBooking::parse)

    fun orders(token: String): List<JSONObject> =
        requestArray("services/orders", token = token).objects()

    fun calendar(token: String, start: String, end: String): List<JSONObject> = requestArray(
        "services/move-calendar?start_date=${start.encode()}&end_date=${end.encode()}", token
    ).objects()

    fun bookingAction(token: String, bookingId: String, action: String): ServiceBooking =
        ServiceBooking.parse(
            requestObject(
                "PATCH", "services/bookings/${bookingId.encode()}",
                body = JSONObject().put("action", action).toString(), token = token
            )
        )

    fun proposeReschedule(token: String, bookingId: String, proposedAt: String): ServiceBooking =
        ServiceBooking.parse(
            requestObject(
                "PATCH", "services/bookings/${bookingId.encode()}",
                body = JSONObject().put("action", "propose_reschedule")
                    .put("proposed_at", proposedAt).toString(), token = token
            )
        )

    fun review(token: String, bookingId: String, rating: Int, review: String) = requestObject(
        "POST", "services/bookings/${bookingId.encode()}/review",
        JSONObject().put("rating", rating).put("review_text", review).toString(), token
    )

    fun plans(token: String): List<MovePlanSummary> =
        requestArray("services/move-plans", token = token).objects().map(MovePlanSummary::parse)

    fun createPlan(token: String, title: String, moveDate: String?, budget: String?): MovePlanSummary {
        val body = JSONObject().put("title", title)
        moveDate?.takeIf(String::isNotBlank)?.let { body.put("move_date", it) }
        budget?.toBigDecimalOrNull()?.let { body.put("target_budget_kes", it) }
        return MovePlanSummary.parse(requestObject("POST", "services/move-plans", body.toString(), token))
    }

    fun tasks(token: String, planId: String): List<JSONObject> = requestArray(
        "services/move-plans/${planId.encode()}/tasks", token = token
    ).objects()

    fun addTask(token: String, planId: String, title: String, category: String, date: String?): JSONObject {
        val body = JSONObject().put("title", title).put("category", category)
        date?.takeIf(String::isNotBlank)?.let { body.put("due_date", it) }
        return requestObject("POST", "services/move-plans/${planId.encode()}/tasks", body.toString(), token)
    }

    fun updateTask(token: String, taskId: String, status: String): JSONObject = requestObject(
        "PATCH", "services/move-tasks/${taskId.encode()}", JSONObject().put("status", status).toString(), token
    )

    fun updateRoomItem(token: String, itemId: String, status: String): JSONObject = requestObject(
        "PATCH", "services/room-setup/${itemId.encode()}", JSONObject().put("status", status).toString(), token
    )

    fun budgets(token: String, planId: String): List<JSONObject> = requestArray(
        "services/move-plans/${planId.encode()}/budget", token = token
    ).objects()

    fun addBudget(token: String, planId: String, title: String, amount: String): JSONObject =
        requestObject(
            "POST", "services/move-plans/${planId.encode()}/budget",
            JSONObject().put("title", title).put("amount_kes", amount.toBigDecimal()).toString(), token
        )

    fun roomSetup(token: String, planId: String): List<JSONObject> = requestArray(
        "services/move-plans/${planId.encode()}/room-setup", token = token
    ).objects()

    fun addRoomItem(token: String, planId: String, room: String, item: String, quantity: Int): JSONObject =
        requestObject(
            "POST", "services/move-plans/${planId.encode()}/room-setup",
            JSONObject().put("room_name", room).put("item_name", item).put("quantity", quantity).toString(), token
        )

    fun residentProperties(token: String): List<ResidentProperty> = requestArray(
        "services/resident-properties", token = token
    ).objects().map(ResidentProperty::parse)

    fun maintenance(token: String): List<JSONObject> =
        requestArray("services/maintenance", token = token).objects()

    fun createMaintenance(
        token: String,
        propertyId: String,
        category: String,
        description: String,
        photoDocumentIds: List<String> = emptyList()
    ) =
        requestObject(
            "POST", "services/maintenance",
            JSONObject().put("property_id", propertyId).put("category", category)
                .put("description", description).put("photo_document_ids", JSONArray(photoDocumentIds)).toString(), token
        )

    fun maintenanceAction(token: String, requestId: String, action: String, note: String? = null): JSONObject {
        val body = JSONObject().put("action", action)
        note?.let { body.put("note", it) }
        return requestObject("PATCH", "services/maintenance/${requestId.encode()}/actions", body.toString(), token)
    }

    fun providerProfile(token: String): JSONObject = requestObject(
        "GET", "services/providers/me", token = token
    )

    fun myOfferings(token: String): List<ServiceOffering> = requestArray(
        "services/providers/me/offerings", token = token
    ).objects().map(ServiceOffering::parse)

    fun publicProvider(providerId: String): JSONObject = requestObject(
        "GET", "services/providers/${providerId.encode()}"
    )

    fun saveProviderProfile(token: String, name: String, description: String, published: Boolean): JSONObject =
        requestObject(
            "PUT", "services/providers/me",
            JSONObject().put("public_name", name).put("description", description)
                .put("is_published", published).toString(), token
        )

    fun saveOffering(
        token: String,
        title: String,
        category: String,
        description: String,
        price: String,
        countyId: String
    ): ServiceOffering = ServiceOffering.parse(
        requestObject(
            "POST", "services/providers/me/offerings",
            JSONObject().put("title", title).put("category", category)
                .put("description", description).put("pricing_model", "from")
                .put("price_amount", price.toBigDecimal()).put("service_areas", org.json.JSONArray()
                    .put(JSONObject().put("county_id", countyId)))
                .toString(), token
        )
    )

    fun uploadProviderImage(token: String, filename: String, mime: String, bytes: ByteArray): JSONObject {
        val connection = (URL(versionedBase + "services/providers/me/images?filename=${filename.encode()}")
            .openConnection() as HttpURLConnection).apply {
            requestMethod = "POST"
            connectTimeout = 12_000
            readTimeout = 20_000
            doOutput = true
            setRequestProperty("Accept", "application/json")
            setRequestProperty("Authorization", "Bearer $token")
            setRequestProperty("Content-Type", mime)
        }
        try {
            connection.outputStream.use { it.write(bytes) }
            val status = connection.responseCode
            if (status !in 200..299) {
                val raw = connection.errorStream?.bufferedReader(Charsets.UTF_8)?.use { it.readText() }.orEmpty()
                val message = runCatching { JSONObject(raw).optJSONObject("error")?.optString("message") }
                    .getOrNull()?.takeIf(String::isNotBlank)
                throw ServicesApiException(message ?: "The HomeScout request failed ($status).")
            }
            return JSONObject(connection.inputStream.bufferedReader(Charsets.UTF_8).use { it.readText() })
        } finally {
            connection.disconnect()
        }
    }

    fun counties(): List<ServiceLocation> = requestArray("locations/counties")
        .objects().map { ServiceLocation(it.optString("id"), it.optString("name")) }

    private fun requestArray(path: String, token: String? = null): JSONArray =
        request("GET", path, token = token).let { it.optJSONArray("_items") ?: JSONArray() }

    private fun requestObject(
        method: String,
        path: String,
        body: String? = null,
        token: String? = null
    ): JSONObject = request(method, path, body, token)

    private fun request(method: String, path: String, body: String? = null, token: String? = null): JSONObject {
        val connection = (URL(versionedBase + path).openConnection() as HttpURLConnection).apply {
            requestMethod = method
            connectTimeout = 12_000
            readTimeout = 20_000
            setRequestProperty("Accept", "application/json")
            token?.let { setRequestProperty("Authorization", "Bearer $it") }
            body?.let {
                doOutput = true
                setRequestProperty("Content-Type", "application/json")
            }
        }
        try {
            body?.let { connection.outputStream.use { stream -> stream.write(it.toByteArray()) } }
            val status = connection.responseCode
            if (status !in 200..299) {
                val raw = connection.errorStream?.bufferedReader(Charsets.UTF_8)?.use { it.readText() }.orEmpty()
                val message = runCatching { JSONObject(raw).optJSONObject("error")?.optString("message") }
                    .getOrNull()?.takeIf(String::isNotBlank)
                throw ServicesApiException(message ?: "The HomeScout request failed ($status).")
            }
            val text = connection.inputStream.bufferedReader(Charsets.UTF_8).use { it.readText() }
            if (text.trimStart().startsWith("[")) return JSONObject().put("_items", JSONArray(text))
            if (text.trim() == "null" || text.isBlank()) return JSONObject()
            return JSONObject(text)
        } finally {
            connection.disconnect()
        }
    }
}

private fun String.encode(): String = URLEncoder.encode(this, Charsets.UTF_8.name())

private fun JSONArray?.strings(vararg keys: String): List<String> {
    if (this == null) return emptyList()
    return buildList {
        for (index in 0 until length()) {
            val item = optJSONObject(index) ?: continue
            keys.map { item.optString(it).takeIf(String::isNotBlank) }.filterNotNull()
                .joinToString(", ").takeIf(String::isNotBlank)?.let(::add)
        }
    }
}

private fun JSONArray.objects(): List<JSONObject> = buildList {
    for (index in 0 until length()) optJSONObject(index)?.let(::add)
}
