package ke.co.homescout.data.auth

import android.content.Context
import android.os.Handler
import android.os.Looper
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import ke.co.homescout.data.remote.AdminUser
import ke.co.homescout.data.remote.AuthApi
import ke.co.homescout.data.remote.AuthApiException
import ke.co.homescout.data.remote.AuthNotice
import ke.co.homescout.data.remote.AuthTokens
import ke.co.homescout.data.remote.AuthUser
import ke.co.homescout.data.remote.AuthenticatedSession
import ke.co.homescout.data.remote.DeviceSession
import ke.co.homescout.data.remote.RoleOption
import java.io.IOException
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors

data class AuthUiState(
    val isLoading: Boolean = false,
    val sessionChecked: Boolean = false,
    val user: AuthUser? = null,
    val message: String? = null,
    val error: String? = null,
    val developmentToken: String? = null,
    val sessions: List<DeviceSession> = emptyList(),
    val adminUsers: List<AdminUser> = emptyList(),
    val roleOptions: List<RoleOption> = emptyList()
)

private data class RegistrationResult(
    val notice: AuthNotice,
    val tokens: AuthTokens? = null,
    val user: AuthUser? = null
)

/** Keeps identity requests off the Compose thread and publishes immutable UI snapshots. */
class AuthController(context: Context) : AutoCloseable {
    private val api = AuthApi()
    private val store = EncryptedSessionStore(context.applicationContext)
    private val executor: ExecutorService = Executors.newSingleThreadExecutor()
    private val mainHandler = Handler(Looper.getMainLooper())
    private val tokenLock = Any()
    @Volatile private var tokens: AuthTokens? = null
    private val sessionRefresher: (String) -> String? = ::refreshAfterUnauthorized

    init {
        AuthenticatedSession.install(sessionRefresher)
    }

    var state by mutableStateOf(AuthUiState())
        private set

    fun accessToken(): String? = tokens?.accessToken

    fun restoreSession() {
        if (tokens != null || state.isLoading) return
        val saved = store.read() ?: run { state = state.copy(sessionChecked = true); return }
        runRequest(
            request = {
                val rotated = api.refresh(saved.refreshToken)
                store.save(rotated)
                rotated to api.currentUser(rotated.accessToken)
            },
            onSuccess = { (newTokens, user) ->
                synchronized(tokenLock) { tokens = newTokens }
                state = state.copy(user = user, error = null, sessionChecked = true)
            },
            onFailure = { error ->
                store.clear()
                synchronized(tokenLock) { tokens = null }
                state = state.copy(user = null, error = null, sessionChecked = true)
            }
        )
    }

    fun signIn(email: String, password: String) {
        runRequest(
            request = {
                val pair = api.login(email, password)
                store.save(pair)
                pair to api.currentUser(pair.accessToken)
            },
            onSuccess = { (pair, user) ->
                synchronized(tokenLock) { tokens = pair }
                state = state.copy(user = user, message = "Welcome back, ${user.givenName}.")
            }
        )
    }

    fun register(email: String, password: String, givenName: String, familyName: String, role: String) {
        runRequest(
            request = { client ->
                val notice = client.register(email, password, givenName, familyName, role)
                val developmentCode = notice.developmentToken
                if (developmentCode.isNullOrBlank()) {
                    RegistrationResult(notice)
                } else {
                    // The backend only returns this single-use code in development/test.
                    // Verify through the normal endpoint, then sign in with the submitted credentials.
                    client.verifyEmail(developmentCode)
                    val pair = client.login(email, password)
                    val user = client.currentUser(pair.accessToken)
                    store.save(pair)
                    RegistrationResult(notice, pair, user)
                }
            },
            onSuccess = { result ->
                val pair = result.tokens
                val user = result.user
                if (pair != null && user != null) {
                    synchronized(tokenLock) { tokens = pair }
                    state = state.copy(
                        user = user,
                        message = "Account created and signed in.",
                        developmentToken = null,
                        error = null,
                        sessionChecked = true
                    )
                } else {
                    showNotice(
                        result.notice,
                        "Account created. Enter the verification code shown below to finish setup."
                    )
                }
            }
        )
    }

    fun verifyEmail(actionToken: String) {
        runRequest(
            request = { api.verifyEmail(actionToken) },
            onSuccess = { notice ->
                state = state.copy(
                    message = notice.message,
                    developmentToken = null,
                    error = null
                )
            }
        )
    }

    fun resendVerification(email: String) {
        runRequest(
            request = { api.resendVerification(email) },
            onSuccess = { showNotice(it, "A new local verification code is ready below.") }
        )
    }

    fun requestPasswordReset(email: String) {
        runRequest(
            request = { api.requestPasswordReset(email) },
            onSuccess = { showNotice(it, "Reset code ready. Enter it below, then choose a new password.") }
        )
    }

    fun confirmPasswordReset(actionToken: String, password: String) {
        runRequest(
            request = { api.confirmPasswordReset(actionToken, password) },
            onSuccess = { notice ->
                state = state.copy(
                    message = notice.message,
                    developmentToken = null,
                    error = null,
                    user = null,
                    sessions = emptyList()
                )
            }
        )
    }

    fun loadSessions() {
        val currentTokens = tokens ?: return
        runRequest(
            request = { api.listSessions(currentTokens.accessToken) },
            onSuccess = { sessions -> state = state.copy(sessions = sessions) }
        )
    }

    fun revokeSession(session: DeviceSession) {
        val currentTokens = tokens ?: return
        runRequest(
            request = { api.revokeSession(currentTokens.accessToken, session.id) },
            onSuccess = {
                if (session.current) {
                    store.clear()
                    synchronized(tokenLock) { tokens = null }
                    state = state.copy(user = null, sessions = emptyList(), message = "This device was signed out.")
                } else {
                    state = state.copy(message = "Device session signed out.")
                    loadSessions()
                }
            }
        )
    }

    fun loadRoleOptions() {
        val currentTokens = tokens ?: return
        runRequest(
            request = { api.listRoles(currentTokens.accessToken) },
            onSuccess = { options -> state = state.copy(roleOptions = options) }
        )
    }

    fun searchAdminUsers(query: String) {
        val currentTokens = tokens ?: return
        runRequest(
            request = { api.searchUsers(currentTokens.accessToken, query) },
            onSuccess = { users -> state = state.copy(adminUsers = users) }
        )
    }

    fun assignRole(userId: String, roleCode: String, scopeType: String, scopeId: String, password: String) {
        val currentTokens = tokens ?: return
        runRequest(
            request = {
                api.assignRole(currentTokens.accessToken, userId, roleCode, scopeType, scopeId, password)
                api.currentUser(currentTokens.accessToken)
            },
            onSuccess = { user -> state = state.copy(user = user, message = "Role assignment saved.") }
        )
    }

    fun signOut() {
        val currentTokens = tokens
        executor.execute {
            if (currentTokens != null) runCatching { api.logout(currentTokens.refreshToken) }
            store.clear()
            synchronized(tokenLock) { tokens = null }
            mainHandler.post {
                state = AuthUiState(message = "You have been signed out.", sessionChecked = true)
            }
        }
    }

    fun dismissMessage() {
        state = state.copy(message = null, error = null, developmentToken = null)
    }

    private fun showNotice(notice: AuthNotice, developmentMessage: String) {
        state = state.copy(
            message = if (notice.developmentToken != null) developmentMessage else notice.message,
            developmentToken = notice.developmentToken,
            error = null
        )
    }

    /** Refreshes once after an API 401; concurrent requests reuse the rotated token. */
    private fun refreshAfterUnauthorized(rejectedAccessToken: String): String? = synchronized(tokenLock) {
        val current = tokens ?: store.read()?.also { tokens = it } ?: return@synchronized null
        if (current.accessToken != rejectedAccessToken) return@synchronized current.accessToken

        try {
            val rotated = api.refresh(current.refreshToken)
            store.save(rotated)
            tokens = rotated
            mainHandler.post {
                if (tokens?.accessToken == rotated.accessToken) {
                    // Trigger Compose to pass the renewed access token to any later feature requests.
                    state = state.copy(error = null, sessionChecked = true)
                }
            }
            rotated.accessToken
        } catch (failure: AuthApiException) {
            if (failure.statusCode !in setOf(401, 403)) throw failure
            store.clear()
            tokens = null
            mainHandler.post {
                if (tokens == null) {
                    state = state.copy(user = null, sessions = emptyList(), sessionChecked = true)
                }
            }
            null
        }
    }

    private fun <T> runRequest(request: (AuthApi) -> T, onSuccess: (T) -> Unit, onFailure: ((Throwable) -> Unit)? = null) {
        state = state.copy(isLoading = true, error = null)
        executor.execute {
            val result = runCatching { request(api) }
            mainHandler.post {
                state = state.copy(isLoading = false)
                result.fold(
                    onSuccess = onSuccess,
                    onFailure = { error ->
                        if (error is AuthApiException && error.statusCode == 401) {
                            store.clear()
                            tokens = null
                            state = state.copy(user = null, sessions = emptyList())
                        }
                        val message = when (error) {
                            is AuthApiException -> error.message
                            is IOException -> "Could not reach the HomeScout service. Check your connection and try again."
                            else -> "Something went wrong. Please try again."
                        }
                        if (onFailure != null) onFailure(error) else state = state.copy(error = message)
                    }
                )
            }
        }
    }

    override fun close() {
        AuthenticatedSession.uninstall(sessionRefresher)
        executor.shutdown()
    }
}
