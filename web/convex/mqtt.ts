"use node";

import { v } from "convex/values";
import mqtt from "mqtt";
import { internal } from "./_generated/api";
import { internalAction } from "./_generated/server";

const TOPIC_CMD = "garage/opener/cmd";
const TOPIC_PAIR_ACK = "garage/opener/pair/ack";
const PAIR_WAIT_MS = 60_000;
const LISTEN_SLICE_MS = 50_000;
const LISTEN_RETRY_MS = 5_000;

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

async function listenForPairAck(nonce: string, waitMs: number, publishPair: boolean) {
  const settings = mqttSettings();
  const mqttClient = await mqtt.connectAsync(settings.url, {
    username: settings.username,
    password: settings.password,
    clientId: `convex-pair-${nonce.slice(0, 12)}-${Date.now().toString(36)}`,
    rejectUnauthorized: true,
    connectTimeout: 8000,
  });
  try {
    await mqttClient.subscribeAsync(TOPIC_PAIR_ACK);
    return await new Promise<boolean>((resolve) => {
      const timer = setTimeout(() => resolve(false), waitMs);
      const onMessage = (_topic: string, payload: Buffer) => {
        const text = payload.toString().trim();
        if (text === nonce || text === `pair:${nonce}`) {
          clearTimeout(timer);
          mqttClient.off("message", onMessage);
          resolve(true);
        }
      };
      mqttClient.on("message", onMessage);
      if (!publishPair) {
        return;
      }
      void mqttClient.publishAsync(TOPIC_CMD, `pair:${nonce}`).catch(() => {
        clearTimeout(timer);
        resolve(false);
      });
    });
  } finally {
    await mqttClient.endAsync();
  }
}

export const runPairing = internalAction({
  args: { pairingId: v.id("pairings"), nonce: v.string() },
  handler: async (ctx, args) => {
    let confirmed = false;
    try {
      const matched = await listenForPairAck(args.nonce, PAIR_WAIT_MS, true);
      if (matched) {
        await ctx.runMutation(internal.door.confirmPairing, { nonce: args.nonce });
        confirmed = true;
      }
    } catch {
      // SoftAP pairing still uses this nonce after the phone leaves the internet.
    }
    if (!confirmed) {
      await ctx.scheduler.runAfter(0, internal.mqtt.waitForPairAck, {
        pairingId: args.pairingId,
        nonce: args.nonce,
      });
    }
  },
});

export const waitForPairAck = internalAction({
  args: { pairingId: v.id("pairings"), nonce: v.string() },
  handler: async (ctx, args) => {
    const pending = await ctx.runQuery(internal.door.getPendingPairing, {
      pairingId: args.pairingId,
    });
    if (!pending) {
      return;
    }
    const remaining = pending.expiresAt - Date.now();
    if (remaining <= 0) {
      return;
    }
    try {
      const matched = await listenForPairAck(
        args.nonce,
        Math.min(LISTEN_SLICE_MS, remaining),
        false,
      );
      if (matched) {
        await ctx.runMutation(internal.door.confirmPairing, { nonce: args.nonce });
        return;
      }
    } catch {
      await ctx.scheduler.runAfter(LISTEN_RETRY_MS, internal.mqtt.waitForPairAck, {
        pairingId: args.pairingId,
        nonce: args.nonce,
      });
      return;
    }
    const stillPending = await ctx.runQuery(internal.door.getPendingPairing, {
      pairingId: args.pairingId,
    });
    if (stillPending) {
      await ctx.scheduler.runAfter(0, internal.mqtt.waitForPairAck, {
        pairingId: args.pairingId,
        nonce: args.nonce,
      });
    }
  },
});
