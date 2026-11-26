package ke.co.homescout.data.remote

import org.json.JSONArray
import org.json.JSONObject

/** HomeScout Assistant requests use the same build-configured API root as other account features. */
class AssistantApi(private val api: PersonalHubApi = PersonalHubApi()) {
    fun configuration(): JSONObject = api.getPublicObject("assistant/configuration")

    fun privacy(token: String): JSONObject = api.getObject("assistant/privacy", token)

    fun updatePrivacy(token: String, allowed: Boolean): JSONObject =
        api.send(
            "assistant/privacy",
            "PUT",
            token,
            JSONObject().put("provider_processing_allowed", allowed)
        )

    fun conversations(token: String): List<JSONObject> =
        api.getArray("assistant/conversations", token).objects()

    fun conversation(token: String, id: String): JSONObject =
        api.getObject("assistant/conversations/$id", token)

    fun send(
        token: String,
        text: String,
        conversationId: String?,
        intent: String,
        propertyId: String?,
        includeFinance: Boolean,
        includeSaved: Boolean,
        includeSchedule: Boolean,
        includeWork: Boolean,
        groupId: String?
    ): JSONObject {
        val body = JSONObject()
            .put("text", text)
            .put("intent", intent)
            .put("include_finance_context", includeFinance)
            .put("include_saved_properties", includeSaved)
            .put("include_schedule_context", includeSchedule)
            .put("include_work_context", includeWork)
            .put("conversation_id", conversationId ?: JSONObject.NULL)
            .put("property_id", propertyId ?: JSONObject.NULL)
            .put("shared_group_id", groupId ?: JSONObject.NULL)
            .put("compare_property_ids", JSONArray())
        return api.send("assistant/messages", "POST", token, body)
    }

    fun rename(token: String, id: String, title: String): JSONObject =
        api.send(
            "assistant/conversations/$id",
            "PATCH",
            token,
            JSONObject().put("title", title)
        )

    fun delete(token: String, id: String) {
        api.send("assistant/conversations/$id", "DELETE", token)
    }

    fun groups(token: String): List<JSONObject> =
        api.getArray("collaboration/groups", token).objects()

    private fun JSONArray.objects(): List<JSONObject> =
        (0 until length()).mapNotNull { optJSONObject(it) }
}
