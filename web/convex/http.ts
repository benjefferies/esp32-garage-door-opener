import { httpRouter } from "convex/server";
import { httpAction } from "./_generated/server";
import { internal } from "./_generated/api";

const http = httpRouter();

http.route({
  path: "/door-state",
  method: "POST",
  handler: httpAction(async (ctx, request) => {
    const expected = process.env.DOOR_WEBHOOK_SECRET;
    const header = request.headers.get("Authorization") ?? "";
    if (!expected || header !== `Bearer ${expected}`) {
      return new Response("Unauthorized", { status: 401 });
    }

    let body: { state?: string; gatewayOnline?: boolean };
    try {
      body = await request.json();
    } catch {
      return new Response("Invalid JSON", { status: 400 });
    }

    if (body.state !== "open" && body.state !== "closed" && body.state !== "unknown") {
      return new Response("Invalid state", { status: 400 });
    }

    await ctx.runMutation(internal.door.recordState, {
      state: body.state,
      gatewayOnline: body.gatewayOnline,
    });
    return new Response("ok");
  }),
});

http.route({
  path: "/pair",
  method: "POST",
  handler: httpAction(async (ctx, request) => {
    const expected = process.env.DOOR_WEBHOOK_SECRET;
    const header = request.headers.get("Authorization") ?? "";
    if (!expected || header !== `Bearer ${expected}`) {
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
