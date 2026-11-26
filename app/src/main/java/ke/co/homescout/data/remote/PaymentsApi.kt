package ke.co.homescout.data.remote

import ke.co.homescout.features.finance.SmartRentApi
import org.json.JSONObject

/** Daraja credentials stay on the backend. This client sends only a payer-entered number. */
class PaymentsApi {
    private val api = PersonalHubApi()
    private val financeApi = SmartRentApi()

    fun configuration(): JSONObject = api.getPublicObject("payments/configuration")

    fun history(token: String): List<JSONObject> = api.getArray("payments/me", token).objects()

    fun requestServicePayment(
        token: String,
        serviceOrderId: String,
        phoneNumber: String,
        idempotencyKey: String
    ): JSONObject = api.send(
        path = "payments/service-bookings",
        method = "POST",
        token = token,
        body = JSONObject()
            .put("service_order_id", serviceOrderId)
            .put("phone_number", phoneNumber),
        headers = mapOf("Idempotency-Key" to idempotencyKey)
    )

    fun reconcile(token: String, transactionId: String): JSONObject = api.send(
        path = "payments/${transactionId.encodePaymentSegment()}/reconcile",
        method = "POST",
        token = token
    )

    fun rentObligations(token: String): List<JSONObject> =
        financeApi.getList("rent-obligations", token).objects()

    fun createRentObligation(token: String, body: JSONObject): JSONObject =
        financeApi.send("rent-obligations", token, body = body)

    fun updateRentObligation(token: String, id: String, body: JSONObject): JSONObject =
        financeApi.send("rent-obligations/$id", token, method = "PUT", body = body)

    fun deleteRentObligation(token: String, id: String) =
        financeApi.delete("rent-obligations/$id", token)

    fun reportRentPayment(token: String, obligationId: String, body: JSONObject): JSONObject =
        financeApi.send("rent-obligations/$obligationId/payments", token, body = body)

    fun deleteRentPayment(token: String, recordId: String) =
        financeApi.delete("rent-payments/$recordId", token)
}

private fun org.json.JSONArray.objects(): List<JSONObject> = buildList {
    for (index in 0 until length()) optJSONObject(index)?.let(::add)
}

private fun String.encodePaymentSegment(): String =
    java.net.URLEncoder.encode(this, Charsets.UTF_8.name())
