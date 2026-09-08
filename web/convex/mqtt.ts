"use node";

import { v } from "convex/values";
import mqtt from "mqtt";
import { internal } from "./_generated/api";
import { internalAction } from "./_generated/server";

const TOPIC_CMD = "garage/opener/cmd";

function mqttSettings() {
  const host = process.env.MQTT_HOST;
  const username = process.env.MQTT_USER;
  const password = process.env.MQTT_PASSWORD;
  const port = Number(process.env.MQTT_PORT ?? "8883");
  if (!host || !username || !password) {
    throw new Error("MQTT env vars are not set");
  }
  return { url: `mqtts://${host}:${port}`, username, password };
}

async function publishCommand(payload: string) {
  const settings = mqttSettings();
  const client = await mqtt.connectAsync(settings.url, {
    username: settings.username,
    password: settings.password,
    clientId: `convex-pub-${Date.now().toString(36)}`,
    rejectUnauthorized: true,
    connectTimeout: 8000,
  });
  try {
    await client.publishAsync(TOPIC_CMD, payload);
  } finally {
    await client.endAsync();
  }
}

export const publishToggle = internalAction({
  args: { commandId: v.id("commands") },
  handler: async (ctx, args) => {
    try {
      await publishCommand("toggle");
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

export const runPairing = internalAction({
  args: { nonce: v.string() },
  handler: async (_ctx, args) => {
    try {
      await publishCommand(`pair:${args.nonce}`);
    } catch {
      // SoftAP pairing still confirms this nonce with POST /api/pair.
    }
  },
});
