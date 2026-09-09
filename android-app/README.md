# ProcureFlow Android

This Android application securely wraps the live ProcureFlow PWA at
`https://procureflow-live-sih26032.alexusa273.chatgpt.site/`.

It supports Android back navigation, offline retry, media selection, voice-note
microphone permission, safe browsing, service-worker storage, HTTPS-only app
traffic, and safe spacing around Android status and navigation bars. External
links open in the user's default application.

Build on Windows with an installed Android SDK and JDK:

```powershell
.\build.ps1
```

The installable APK is written to `artifacts/ProcureFlow-Android-v1.0.1.apk`.
