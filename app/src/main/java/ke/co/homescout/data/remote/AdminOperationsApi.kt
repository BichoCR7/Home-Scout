package ke.co.homescout.data.remote

import org.json.JSONObject

/** Staff operations use the build-configured API root; no server URL or secret is embedded here. */
class AdminOperationsApi(private val api: PersonalHubApi = PersonalHubApi()) {
    fun objectRows(path: String, token: String): JSONObject = api.getObject(path, token)

    fun rows(path: String, token: String) = api.getArray(path, token)

    fun send(path: String, method: String, token: String, body: JSONObject): JSONObject =
        api.send(path, method, token, body)
}
