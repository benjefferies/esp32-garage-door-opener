"use node";

import { v } from "convex/values";
import mqtt from "mqtt";
import { internal } from "./_generated/api";
import { internalAction } from "./_generated/server";

const TOPIC_CMD = "garage/opener/cmd";

export const publishToggle = internalAction({
  args: { commandId: v.id("commands") },
  handler: async (ctx, args) => {
    const host = process.env.MQTT_HOST;
    const username = process.env.MQTT_USER;
    const password = process.env.MQTT_PASSWORD;
    const port = Number(process.env.MQTT_PORT ?? "8883");

    if (!host || !username || !password) {
      await ctx.runMutation(internal.door.markCommand, {
        commandId: args.commandId,
        status: "failed",
        error: "MQTT env vars are not set",
      });
      return;
    }

    const url = `mqtts://${host}:${port}`;
    try {
      const client = await mqtt.connectAsync(url, {
        username,
        password,
        clientId: `convex-publisher-${Date.now()}`,
        rejectUnauthorized: true,
        connectTimeout: 8000,
      });
      await client.publishAsync(TOPIC_CMD, "toggle");
      await client.endAsync();
      await ctx.runMutation(internal.door.markCommand, {
        commandId: args.commandId,
        status: "sent",
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : "MQTT publish failed";
      await ctx.runMutation(internal.door.markCommand, {
        commandId: args.commandId,
        status: "failed",
        error: message,
      });
    }
  },
});
