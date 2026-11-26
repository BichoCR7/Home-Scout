package ke.co.homescout.data.remote

/**
 * App-scoped bridge used by authenticated API clients to renew an expired access token.
 * The callback is installed by AuthController and never exposes the refresh token to features.
 */
object AuthenticatedSession {
    @Volatile
    private var refresher: ((rejectedAccessToken: String) -> String?)? = null

    fun install(refresher: (rejectedAccessToken: String) -> String?) {
        this.refresher = refresher
    }

    fun uninstall(refresher: (rejectedAccessToken: String) -> String?) {
        if (this.refresher === refresher) this.refresher = null
    }

    fun refresh(rejectedAccessToken: String): String? = refresher?.invoke(rejectedAccessToken)
}
