# Garage web app

Clerk-authenticated Convex app. **Toggle garage** publishes `toggle` to HiveMQ topic `garage/opener/cmd`.

## Clerk setup

1. Create an app at [dashboard.clerk.com](https://dashboard.clerk.com).
2. Enable the **Convex** integration (creates a JWT template named `convex`).
3. Copy the **Frontend API URL** (`https://verb-noun-00.clerk.accounts.dev`) and set it on the Convex **dev** deployment:

   `npx convex env set CLERK_JWT_ISSUER_DOMAIN https://ready-caiman-9399.clerk.accounts.dev`

4. Put the publishable key in `web/.env.local`:

   `VITE_CLERK_PUBLISHABLE_KEY=pk_test_...`

5. Add these as allowed origins / redirects in Clerk:
   - `http://localhost:5173`
   - `https://garage-opener-rose.vercel.app`
   - `https://marvelous-herring-626.eu-west-1.convex.site`

## CI deploy

Every push runs `.github/workflows/deploy.yml`: Convex production first, then Vercel production. Vercel’s own git builds are skipped (`ignoreCommand`) so only this workflow ships.

Set these GitHub Actions secrets:

| Secret | Where to get it |
|------|--------|
| `CONVEX_DEPLOY_KEY` | Convex dashboard → project **garage-opener** → Production → Deploy key |
| `VERCEL_TOKEN` | https://vercel.com/account/tokens |
| `VERCEL_ORG_ID` | `team_YdzCRmL3rTmP7y4IHSLMrnBk` |
| `VERCEL_PROJECT_ID` | `prj_etXJPQ9ANb89gjjidzsKaHubHMBi` |

## Vercel (frontend)

Production: https://garage-opener-rose.vercel.app

The UI is a Vite SPA. Convex stays the backend. The Git repo is a monorepo, so the Vercel **Root Directory** must be `web`.

```bash
cd web
vercel link --yes --project garage-opener
vercel env add VITE_CONVEX_URL production --value https://marvelous-herring-626.eu-west-1.convex.cloud --yes
vercel env add VITE_CONVEX_URL preview --value https://marvelous-herring-626.eu-west-1.convex.cloud --yes
vercel env add VITE_CLERK_PUBLISHABLE_KEY production --value pk_test_... --yes
vercel env add VITE_CLERK_PUBLISHABLE_KEY preview --value pk_test_... --yes
vercel git connect https://github.com/benjefferies/esp32-garage-door-opener.git
vercel --prod --yes
```

Add `https://garage-opener-rose.vercel.app` in Clerk as an allowed origin / redirect.

Convex HTTP site (optional fallback): https://marvelous-herring-626.eu-west-1.convex.site

## Run locally

```bash
cd web
npx convex dev
npm run dev             # http://localhost:5173
```

Set these on the Convex deployment (**Environment Variables**), not Wi‑Fi:

| Name | Value |
|------|--------|
| `MQTT_HOST` | `6976bf6995e243d6be6c1f3634bb4f10.s1.eu.hivemq.cloud` |
| `MQTT_PORT` | `8883` |
| `MQTT_USER` | HiveMQ user that **may publish** (not subscribe-only) |
| `MQTT_PASSWORD` | that user's password |
| `SITE_URL` | `http://localhost:5173` while developing |
| `DOOR_WEBHOOK_SECRET` | optional; for later `POST /door-state` from the gateway |

Sign-up is **restricted** in Clerk. After you sign in, **Start pairing** stores a nonce in the browser and caches this app with a service worker. Join the gateway AP **`garage-gw`** (password **`garage-gw`**), reopen this tab offline, press **SW1**, and save home Wi-Fi to `http://192.168.4.1/api/wifi`. After you rejoin home Wi-Fi the app waits for the gateway to come online and confirm that nonce. That confirm is what adds your Clerk user as an owner; `toggleDoor` rejects everyone else.

Door open/closed stays `unknown` until the gateway reports reed state. The owner view shows the last gateway heartbeat (`garage/opener/gateway`) and the last reed reading (`garage/opener/state`). The button still sends MQTT.
