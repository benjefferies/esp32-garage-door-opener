# Garage web app

Clerk-authenticated Convex app. **Toggle garage** publishes `toggle` to HiveMQ topic `garage/opener/cmd`.

## Clerk setup

1. Create an app at [dashboard.clerk.com](https://dashboard.clerk.com).
2. Enable the **Convex** integration (creates a JWT template named `convex`).
3. Copy the **Frontend API URL** (`https://verb-noun-00.clerk.accounts.dev`) and set it on the Convex **dev** deployment:

   `npx convex env set CLERK_JWT_ISSUER_DOMAIN https://YOUR.clerk.accounts.dev`

4. Put the publishable key in `web/.env.local`:

   `VITE_CLERK_PUBLISHABLE_KEY=pk_test_...`

5. Add `http://localhost:5173` and `https://marvelous-herring-626.eu-west-1.convex.site` as allowed origins / redirects in Clerk.

Production URL after `npm run deploy`:

https://marvelous-herring-626.eu-west-1.convex.site

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

Create the first account with **Need an account?** on the sign-in screen.

Door open/closed stays `unknown` until the gateway reports reed state. The button still sends MQTT.
