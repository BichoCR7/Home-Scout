package ke.co.homescout.features.finance

import ke.co.homescout.data.remote.PersonalHubApi
import org.json.JSONArray
import org.json.JSONObject

/** Small feature facade over the app's shared, build-configured authenticated API client. */
class SmartRentApi {
    private val api = PersonalHubApi()

    fun get(path: String, token: String): JSONObject = api.getObject("finance/$path", token)

    fun getList(path: String, token: String): JSONArray = api.getArray("finance/$path", token)

    fun send(
        path: String,
        token: String,
        method: String = "POST",
        body: JSONObject = JSONObject()
    ): JSONObject = api.send("finance/$path", method, token, body)

    fun delete(path: String, token: String): Unit = api.send(
        "finance/$path", "DELETE", token
    ).let { Unit }
}
