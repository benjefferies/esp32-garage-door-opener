import { httpRouter } from "convex/server";
import { httpAction } from "./_generated/server";
import { internal } from "./_generated/api";

const http = httpRouter();

function isAuthorized(request: Request): boolean {
  const expected = process.env.DOOR_WEBHOOK_SECRET;
  const header = request.headers.get("Authorization") ?? "";
  return Boolean(expected) && header === `Bearer ${expected}`;
}

http.route({
  path: "/door-state",
  method: "POST",
  handler: httpAction(async (ctx, request) => {
    if (!isAuthorized(request)) {
      return new Response("Unauthorized", { status: 401 });
    }

    let body: { state?: string; gatewayOnline?: boolean };
    try {
      body = await request.json();
    } catch {
      return new Response("Invalid JSON", { status: 400 });
    }

    const state = body.state;
    const online = body.gatewayOnline;
    if (state !== undefined && state !== "open" && state !== "closed" && state !== "unknown") {
      return new Response("Invalid state", { status: 400 });
    }
    if (online !== undefined && typeof online !== "boolean") {
      return new Response("Invalid gatewayOnline", { status: 400 });
    }

    if (state === "open" || state === "closed" || state === "unknown") {
      await ctx.runMutation(internal.door.recordState, {
        state,
        gatewayOnline: online,
      });
    } else if (typeof online === "boolean") {
      await ctx.runMutation(internal.door.recordHeartbeat, {
        online,
      });
    } else {
      return new Response("Expected state or gatewayOnline", { status: 400 });
    }
    return new Response("ok");
  }),
});

http.route({
  path: "/pair",
  method: "POST",
  handler: httpAction(async (ctx, request) => {
    if (!isAuthorized(request)) {
      return new Response("Unauthorized", { status: 401 });
    }

    let body: { nonce?: string };
    try {
      body = await request.json();
    } catch {
      return new Response("Invalid JSON", { status: 400 });
    }

    if (!body.nonce) {
      return new Response("Missing nonce", { status: 400 });
    }

    const ok = await ctx.runMutation(internal.door.confirmPairing, {
      nonce: body.nonce,
    });
    return new Response(ok ? "ok" : "expired", { status: ok ? 200 : 409 });
  }),
});

export default http;
