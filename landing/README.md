# Traffix submission frontend

Responsive static HTML/CSS/JavaScript. No API keys, backend dependency, analytics, CDN or package installation is needed. Assets are served locally. The junction playground is an illustration, not SUMO. The operator screenshot comes from the reviewed unified build; the phone panel is an interface illustration.

## Local preview

From the repository root:

```powershell
python -m http.server 8080 --directory landing
```

## Vercel

Import the repository and select branch `feat/kush-demo-polish`. Set **Root Directory** to `landing`, **Framework Preset** to Other, leave Build Command empty and use `.` as the output directory. Deploy.

Or, from this directory using an authenticated Vercel CLI:

```powershell
npx vercel --prod
```

Deploy only this directory. Do not upload virtual environments, Android builds, run recordings or private host settings. SUMO is a persistent local worker and is not deployed by this frontend.
