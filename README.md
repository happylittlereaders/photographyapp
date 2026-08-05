# Golden Number — Turning your Streamlit app into a phone app

Your OpenCV/Streamlit logic doesn't need to be rewritten. It keeps running
exactly where it already runs (Streamlit Community Cloud, `goldennumber.streamlit.app`).
What you're adding is a **native shell** around it using a tool called
[Capacitor](https://capacitorjs.com/).

This folder has two parts:

```
streamlit-src/     <- your existing Streamlit app (with camera capture added)
mobile-app/        <- the Capacitor wrapper that becomes the real app
```

---

## Step 0 — Update your live Streamlit app (do this first)

1. Replace your repo's `streamlit_app.py` and `photo_mentor.py` with the
   versions in `streamlit-src/` here. The main change: I added a
   **"📷 Take Photo"** tab using `st.camera_input`, so people don't have to
   dig through their photo library — they can shoot directly in the app.
   Also added a **download button** for the corrected photo.
2. Commit and push to your GitHub repo (`happylittlereaders/photographyapp`).
   Streamlit Cloud auto-redeploys from your `main` branch — no other config needed.
3. Confirm `https://goldennumber.streamlit.app` reflects the update before
   moving on, since the mobile app just loads that URL.

---

## Path A — Free installable app (PWA), no app store

This gets you an icon on the home screen, full-screen (no browser bar),
works on iPhone and Android, zero cost, no review process.

1. Streamlit Cloud lets you serve static files from a `static/` folder if you
   enable it in `.streamlit/config.toml`:

   ```toml
   [server]
   enableStaticServing = true
   ```

2. Copy `mobile-app/www/manifest.json` and `mobile-app/www/sw.js` into a
   `static/` folder in your Streamlit repo, and add two icon images
   (192×192 and 512×512 PNG, your logo) into `static/icons/`.

3. Add this to the top of `streamlit_app.py` so the manifest gets linked in
   the page `<head>`:

   ```python
   st.markdown(
       """
       <link rel="manifest" href="/app/static/manifest.json">
       <meta name="theme-color" content="#dcc86f">
       """,
       unsafe_allow_html=True,
   )
   ```

4. Push to GitHub, wait for redeploy. Then on a phone:
   - **iPhone (Safari):** open the site → Share icon → "Add to Home Screen"
   - **Android (Chrome):** open the site → menu (⋮) → "Install app"

That's it — free, and live in minutes.

---

## Path B — Real App Store / Google Play listing

This uses the `mobile-app/` folder to produce an actual `.apk` (Android)
and Xcode project (iOS) that you submit for store review.

### Prerequisites
- Node.js installed (18+)
- For Android: [Android Studio](https://developer.android.com/studio)
- For iOS: a Mac with Xcode (Apple doesn't allow iOS builds elsewhere)
- Developer accounts: Google Play ($25 one-time), Apple Developer Program ($99/yr)

### 1. Install dependencies

```bash
cd mobile-app
npm install
```

### 2. Add the native platforms

```bash
npm run add:android
npm run add:ios     # only if you're on a Mac and want the App Store too
```

This generates `android/` and `ios/` project folders. `capacitor.config.json`
is already set so the app's `webDir` loads `https://goldennumber.streamlit.app`
directly — you don't need to bundle the Streamlit UI locally.

### 3. Add your app icon + splash screen

Drop your logo into the generated `android/app/src/main/res/` (Android
Studio's Image Asset tool will do this for you: right-click `res` →
New → Image Asset) and `ios/App/App/Assets.xcassets/AppIcon.appiconset/`
(drag images into Xcode's asset catalog).

### 4. Build & test on a device/emulator

```bash
npm run open:android   # opens Android Studio, hit Run
npm run open:ios       # opens Xcode, hit Run (Mac only)
```

### 5. Submit

- **Google Play:** In Android Studio, `Build > Generate Signed Bundle/APK`,
  create a keystore, upload the resulting `.aab` to the
  [Play Console](https://play.google.com/console).
- **App Store:** In Xcode, `Product > Archive`, then use the Organizer
  window to upload to **App Store Connect**. Apple's review is stricter
  about privacy disclosures — since this app uses the camera, you'll need
  to fill in the camera-usage purpose string (already stubbed in
  `ios/App/App/Info.plist` as `NSCameraUsageDescription` — customize the text).

### Why this approach instead of rewriting in Kivy

Your original plan doc mentions Kivy/Buildozer — that's the right call if
you're running OpenCV *on the phone itself*. But you already built a working
Streamlit app that runs OpenCV *on a server* and just displays results in a
browser. Rebuilding that in Kivy means re-writing the whole UI and hosting
architecture from scratch. Capacitor reuses 100% of what you already shipped
and just gives it a native shell — much less work for the same "app in
the App Store" outcome for your portfolio.

**Tradeoff to know:** because the CV processing happens on Streamlit's free
tier server, there's a cold-start delay (~10-30s) if the app hasn't been
used recently, and Streamlit Community Cloud has usage limits. If this
starts getting real traffic, moving the backend to a small paid host
(Render, Railway, Fly.io) removes that limit — happy to help with that
when you get there.
