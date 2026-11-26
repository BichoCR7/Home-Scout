# HomeScout Android local API

The current debug APK and Android Studio configuration use `http://127.0.0.1:8766`. The previous listener on port 8765 did not include the Phase 3 Finance API route, so the current HomeScout backend runs on 8766. Start it from the backend folder:

```powershell
cd backend
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8766
```

For the connected physical phone, forward the device port to the workstation:

```powershell
adb reverse tcp:8766 tcp:8766
```

The forwarding rule lasts for the current ADB connection and must be reapplied after reconnecting. To build another physical-phone debug APK with the same address:

```powershell
.\gradlew.bat --project-prop=homescout.apiBaseUrl=http://127.0.0.1:8766 :app:assembleDebug
```

For Android Studio builds, the ignored project `local.properties` contains `homescout.apiBaseUrl=http://127.0.0.1:8766`. Gradle checks explicit command-line properties first, then `HOMESCOUT_API_BASE_URL`, then this local setting. The URL is a development endpoint, not a credential. Android emulators should use `http://10.0.2.2:8766`.

The debug manifest permits local HTTP for this development route only; release builds do not opt into cleartext traffic. The app's password fields have a show/hide eye control and start hidden.

For local account verification and password reset without SMTP, set `HOMESCOUT_AUTH_DEV_EXPOSE_TOKENS=true` in the ignored `backend/.env`. The local app then displays one-time verification/reset codes and pre-fills the code field. This option is rejected for staging/production; real email delivery requires configured SMTP values. Never enable code exposure on a shared or deployed server.
