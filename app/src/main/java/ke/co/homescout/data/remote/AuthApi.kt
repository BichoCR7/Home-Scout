package ke.co.homescout.data.remote

import org.json.JSONArray
import org.json.JSONObject
import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL
import java.net.URLEncoder

data class AuthTokens(val accessToken: String, val refreshToken: String, val expiresIn: Int)

data class AuthNotice(val message: String, val developmentToken: String?)

data class AuthUser(
    val id: String,
    val email: String,
    val status: String,
    val emailVerified: Boolean,
    val givenName: String,
    val familyName: String,
    val requestedRole: String?,
    val roles: List<String>,
    val permissions: List<String>
)

data class DeviceSession(val id: String, val createdAt: String, val current: Boolean)

data class AdminUser(
    val id: String,
    val email: String,
    val status: String,
    val roles: List<String>,
    val requestedRole: String?
)

data class RoleOption(val code: String, val name: String)

class AuthApiException(
    val statusCode: Int,
    val errorCode: String,
    message: String
) : IOException(message)

/** Versioned HomeScout identity API. Request bodies and bearer values are never logged. */
class AuthApi {
    fun register(
        email: String,
        password: String,
        givenName: String,
        familyName: String,
        role: String
    ): AuthNotice {
        val response = request(
            "auth/register",
            "POST",
            JSONObject()
                .put("email", email.trim())
                .put("password", password)
                .put("given_name", givenName.trim())
                .put("family_name", familyName.trim().ifBlank { JSONObject.NULL })
                .put("requested_role_code", role)
        )
        return notice(response)
    }

    fun verifyEmail(token: String): AuthNotice = notice(
        request("auth/email/verify", "POST", JSONObject().put("token", token.trim()))
    )

    fun resendVerification(email: String): AuthNotice = notice(
        request("auth/email/resend", "POST", JSONObject().put("email", email.trim()))
    )

    fun login(email: String, password: String): AuthTokens = tokens(
        request(
            "auth/login",
            "POST",
            JSONObject().put("email", email.trim()).put("password", password)
        )
    )

    fun refresh(refreshToken: String): AuthTokens = tokens(
        request(
            "auth/refresh",
            "POST",
            JSONObject().put("refresh_token", refreshToken)
        )
    )

    fun logout(refreshToken: String) {
        request("auth/logout", "POST", JSONObject().put("refresh_token", refreshToken))
    }

    fun requestPasswordReset(email: String): AuthNotice = notice(
        request("auth/password-reset/request", "POST", JSONObject().put("email", email.trim()))
    )

    fun confirmPasswordReset(token: String, newPassword: String): AuthNotice = notice(
        request(
            "auth/password-reset/confirm",
            "POST",
            JSONObject().put("token", token.trim()).put("new_password", newPassword)
        )
    )

    fun currentUser(accessToken: String): AuthUser {
        val response = request("auth/me", "GET", accessToken = accessToken)
        val profile = response.optJSONObject("profile")
        return AuthUser(
            id = response.optString("id"),
            email = response.optString("email"),
            status = response.optString("status"),
            emailVerified = response.optBoolean("email_verified"),
            givenName = profile?.optString("given_name").orEmpty(),
            familyName = profile?.optString("family_name").orEmpty(),
            requestedRole = profile?.nullableString("requested_role_code"),
            roles = response.stringList("roles"),
            permissions = response.stringList("permissions")
        )
    }

    fun listSessions(accessToken: String): List<DeviceSession> {
        return requestArray("auth/sessions", accessToken).asSessionList()
    }

    fun revokeSession(accessToken: String, sessionId: String) {
        request("auth/sessions/${segment(sessionId)}", "DELETE", accessToken = accessToken)
    }

    fun searchUsers(accessToken: String, query: String): List<AdminUser> {
        val encoded = URLEncoder.encode(query.trim(), Charsets.UTF_8.name())
        return request("admin/users?q=$encoded", "GET", accessToken = accessToken)
            .optJSONArray("items")
            .asAdminUserList()
    }

    fun listRoles(accessToken: String): List<RoleOption> =
        requestArray("admin/roles", accessToken).asRoleList()

    fun assignRole(
        accessToken: String,
        userId: String,
        roleCode: String,
        scopeType: String,
        scopeId: String,
        password: String
    ) {
        request(
            "admin/users/${segment(userId)}/roles",
            "POST",
            JSONObject()
                .put("role_code", roleCode)
                .put("scope_type", scopeType)
                .put("scope_id", scopeId)
                .put("current_password", password),
            accessToken
        )
    }

    private fun requestArray(path: String, accessToken: String): JSONArray =
        requestRaw(path, "GET", null, accessToken).let(::JSONArray)

    private fun request(
        path: String,
        method: String,
        body: JSONObject? = null,
        accessToken: String? = null
    ): JSONObject {
        val response = requestRaw(path, method, body, accessToken)
        return if (response.isBlank()) JSONObject() else JSONObject(response)
    }

    private fun requestRaw(
        path: String,
        method: String,
        body: JSONObject? = null,
        accessToken: String? = null
    ): String = if (accessToken.isNullOrBlank()) {
        requestRawOnce(path, method, body, accessToken)
    } else {
        withSessionRefresh(accessToken) { refreshed ->
            requestRawOnce(path, method, body, refreshed)
        }
    }

    private fun requestRawOnce(
        path: String,
        method: String,
        body: JSONObject? = null,
        accessToken: String? = null
    ): String {
        val baseUrl = ApiConfiguration.versionedBaseUrl
            ?: throw AuthApiException(0, "api_not_configured", "The HomeScout API address is not configured.")
        val connection = (URL(baseUrl + path).openConnection() as HttpURLConnection).apply {
            requestMethod = method
            connectTimeout = 12_000
            readTimeout = 12_000
            setRequestProperty("Accept", "application/json")
            if (body != null) setRequestProperty("Content-Type", "application/json; charset=utf-8")
            if (accessToken != null) setRequestProperty("Authorization", "Bearer $accessToken")
            if (body != null) doOutput = true
        }
        try {
            if (body != null) {
                connection.outputStream.use { stream ->
                    stream.write(body.toString().toByteArray(Charsets.UTF_8))
                }
            }
            val status = connection.responseCode
            val stream = if (status in 200..299) connection.inputStream else connection.errorStream
            val responseText = stream?.bufferedReader(Charsets.UTF_8)?.use { it.readText() }.orEmpty()
            if (status !in 200..299) {
                val error = runCatching { JSONObject(responseText).optJSONObject("error") }.getOrNull()
                val message = error?.optString("message")
                    ?.takeIf(String::isNotBlank)
                    ?: "The request could not be completed. Please try again."
                throw AuthApiException(status, error?.optString("code").orEmpty(), message)
            }
            return responseText
        } finally {
            connection.disconnect()
        }
    }

    private fun withSessionRefresh(accessToken: String, request: (String) -> String): String {
        try {
            return request(accessToken)
        } catch (failure: AuthApiException) {
            if (failure.statusCode != 401) throw failure
            val refreshed = AuthenticatedSession.refresh(accessToken) ?: throw failure
            if (refreshed == accessToken) throw failure
            return request(refreshed)
        }
    }

    private fun segment(value: String): String = URLEncoder.encode(value, Charsets.UTF_8.name())

    private fun notice(json: JSONObject) = AuthNotice(
        message = json.optString("message"),
        developmentToken = json.nullableString("development_token")
    )

    private fun tokens(json: JSONObject) = AuthTokens(
        accessToken = json.optString("access_token"),
        refreshToken = json.optString("refresh_token"),
        expiresIn = json.optInt("expires_in")
    )

    private fun JSONObject.stringList(name: String): List<String> =
        optJSONArray(name).asStringList()

    private fun JSONObject.nullableString(name: String): String? =
        if (isNull(name)) null else optString(name).takeIf(String::isNotBlank)

    private fun JSONArray?.asStringList(): List<String> = buildList {
        if (this@asStringList != null) {
            for (index in 0 until length()) add(optString(index))
        }
    }

    private fun JSONArray.asSessionList(): List<DeviceSession> = buildList {
        for (index in 0 until length()) {
            val item = optJSONObject(index) ?: continue
            add(
                DeviceSession(
                    id = item.optString("id"),
                    createdAt = item.optString("created_at"),
                    current = item.optBoolean("current")
                )
            )
        }
    }

    private fun JSONArray?.asAdminUserList(): List<AdminUser> = buildList {
        if (this@asAdminUserList != null) {
            for (index in 0 until length()) {
                val item = optJSONObject(index) ?: continue
                add(
                    AdminUser(
                        id = item.optString("id"),
                        email = item.optString("email"),
                        status = item.optString("status"),
                        roles = item.optJSONArray("roles").asStringList(),
                        requestedRole = if (item.isNull("requested_role_code")) null
                        else item.optString("requested_role_code")
                    )
                )
            }
        }
    }

    private fun JSONArray.asRoleList(): List<RoleOption> = buildList {
        for (index in 0 until length()) {
            val item = optJSONObject(index) ?: continue
            add(RoleOption(item.optString("code"), item.optString("name")))
        }
    }
}
