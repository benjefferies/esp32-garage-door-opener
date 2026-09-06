"use node";

import { v } from "convex/values";
import mqtt from "mqtt";
import { internal } from "./_generated/api";
import { internalAction } from "./_generated/server";

const TOPIC_CMD = "garage/opener/cmd";
const TOPIC_PAIR_ACK = "garage/opener/pair/ack";
const PAIR_WAIT_MS = 60_000;

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

export const runPairing = internalAction({
  args: { pairingId: v.id("pairings"), nonce: v.string() },
  handler: async (ctx, args) => {
    let client: mqtt.MqttClient | undefined;
    try {
      const settings = mqttSettings();
      const mqttClient = await mqtt.connectAsync(settings.url, {
        username: settings.username,
        password: settings.password,
        clientId: `convex-pair-${args.nonce.slice(0, 12)}`,
        rejectUnauthorized: true,
        connectTimeout: 8000,
      });
      client = mqttClient;
      await mqttClient.subscribeAsync(TOPIC_PAIR_ACK);
      const matched = await new Promise<boolean>((resolve) => {
        const timer = setTimeout(() => resolve(false), PAIR_WAIT_MS);
        const onMessage = (_topic: string, payload: Buffer) => {
          const text = payload.toString().trim();
          if (text === args.nonce || text === `pair:${args.nonce}`) {
            clearTimeout(timer);
            mqttClient.off("message", onMessage);
            resolve(true);
          }
        };
        mqttClient.on("message", onMessage);
        void mqttClient.publishAsync(TOPIC_CMD, `pair:${args.nonce}`).catch(() => {
          clearTimeout(timer);
          resolve(false);
        });
      });

      if (matched) {
        await ctx.runMutation(internal.door.confirmPairing, { nonce: args.nonce });
      }
    } catch {
      // SoftAP pairing still uses this nonce after the phone leaves the internet.
    } finally {
      if (client) {
        await client.endAsync();
      }
    }
  },
});
