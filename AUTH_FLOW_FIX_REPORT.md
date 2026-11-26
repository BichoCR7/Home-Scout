# HomeScout Authentication Entry Flow Fix

**Date:** 2026-11-24  
**Scope:** Repair the existing splash-to-authentication entry flow. No new product phase started.

## Changes

- Kept the existing HomeScoutSplash unchanged.
- Added a branded authentication entry screen with the existing HomeScout logo and two actions: Log in and Create account.
- Changed the navigation start destination from Home to the auth entry after the existing splash.
- Added a session restoration gate. The app waits until encrypted refresh-token restoration is checked before rendering the app routes. A valid backend session routes to Home; absent, expired, or invalid credentials route to authentication.
- Kept the existing Profile sign-in/registration/verification/password-reset forms and API integration. Auth routes use those same screens, not a duplicate registration implementation.
- Added an accessible show/hide eye button to password inputs, including sign-in, registration, and password reset. Passwords start hidden; the control can reveal or mask the typed value.
- Successful login loads /auth/me, persists rotated/session tokens using the existing encrypted session store, and routes to Home.
- Registration remains server-backed. Backend registration, Argon2 password hashing, tenant default assignment, email verification, and password reset were already implemented. Registration proceeds to verification and does not pretend an email was sent where delivery is unavailable.
- Signing out clears the saved session and returns the app to the authentication entry on the next navigation state update.

## Verification

- Android `:app:testDebugUnitTest` and `:app:assembleDebug`: BUILD SUCCESSFUL. The phone-specific build used `homescout.apiBaseUrl=http://127.0.0.1:8765` (Gradle diagnostic report generation disabled due to a Windows report-file collision).
- Backend authentication and authorization tests: 8 passed, one upstream Starlette/httpx deprecation warning.
- Installed updated debug APK on the connected Samsung SM-S938B (Android 17) with adb install -r; Android returned Success.
- Launched ke.co.homescout.debug; process and resumed MainActivity were confirmed. No fatal exception appeared in the process-filtered log.
- Forwarded port 8765 with ADB reverse and opened `/api/v1/health/ready` from the phone; it returned `{"status":"ready","database":"ok"}`. The password eye control was tapped on the installed registration screen and the password became masked.
- Existing APK is at app/build/outputs/apk/debug/app-debug.apk.

## Limits

- This installed debug APK targets `http://127.0.0.1:8765` through ADB reverse. Keep the backend running on the workstation and reapply `adb reverse tcp:8765 tcp:8765` after the phone reconnects. The health connection is confirmed; an account registration was not submitted during this repair.
- The login UI accepts email, matching the existing backend's email-based login contract.
- Email delivery still depends on backend SMTP configuration. The existing development token behavior is environment-gated and not a production email substitute.
- HomeScout branding was retained according to the owner's standing naming/logo decision.

## Crash reported and repaired — 2026-11-24

The owner's screenshot showed Android's “HomeScout Kenya keeps stopping” alert. Reproducing on the connected device produced a main-thread NullPointerException while NavHost registered destinations using a dynamically captured Destination value. Replaced the dynamic placeholder-route loop with an explicit Neighbourhoods route. After rebuild, the updated APK installed successfully, MainActivity stayed resumed, no new crash-buffer entry appeared, and a device screenshot showed the HomeScout authentication entry with Log in/Create account.

## Local verification and password recovery — 2026-11-24

- The generic registration and reset messages preserve account privacy. With SMTP unconfigured, however, no email code could reach the user; development code exposure had also been disabled.
- Enabled `HOMESCOUT_AUTH_DEV_EXPOSE_TOKENS=true` only in the ignored local `backend/.env`. The backend restricts this setting to development/test; it must stay disabled outside local development.
- Updated the Android feedback to say what to do when a local registration/reset code is available. The one-time code is shown in the local development UI and prefilled in the appropriate code field. Production responses remain generic for privacy.
- Created and verified a synthetic local account, signed in, requested a reset code, changed its password, and signed in again using the new password. No mail was sent to an external inbox.
- Rebuilt and installed the app on the Samsung phone. Gradle Android unit tests and assembly passed; the configured API base was confirmed as `http://127.0.0.1:8765`. Backend authentication tests passed (5).

The test-only sign-in used for the local account is provided to the owner in the completion message; it is not a real Gmail account and must not be used in production.
