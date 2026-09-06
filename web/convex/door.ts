import { v } from "convex/values";
import { internal } from "./_generated/api";
import { internalMutation, mutation, query } from "./_generated/server";

const DOOR_SLUG = "opener";
const PAIR_WINDOW_MS = 60_000;

type Identity = {
  tokenIdentifier: string;
  email?: string;
  subject: string;
};

async function requireIdentity(ctx: {
  auth: { getUserIdentity: () => Promise<Identity | null> };
}): Promise<Identity> {
  const identity = await ctx.auth.getUserIdentity();
  if (identity === null) {
    throw new Error("Not signed in");
  }
  return identity;
}

export const getStatus = query({
  args: {},
  handler: async (ctx) => {
    const identity = await requireIdentity(ctx);
    const owner = await ctx.db
      .query("owners")
      .withIndex("by_token", (q) => q.eq("tokenIdentifier", identity.tokenIdentifier))
      .unique();

    const pending = await ctx.db
      .query("pairings")
      .withIndex("by_token", (q) => q.eq("tokenIdentifier", identity.tokenIdentifier))
      .order("desc")
      .first();
    const pairing =
      pending && pending.status === "pending" && pending.expiresAt > Date.now()
        ? { expiresAt: pending.expiresAt }
        : null;

    if (!owner) {
      return {
        isOwner: false,
        pairing,
        door: null,
        lastCommand: null,
      };
    }

    const door = await ctx.db
      .query("doors")
      .withIndex("by_slug", (q) => q.eq("slug", DOOR_SLUG))
      .unique();
    const lastCommand = await ctx.db.query("commands").order("desc").first();
    return {
      isOwner: true,
      pairing: null,
      door: door ?? {
        slug: DOOR_SLUG,
        state: "unknown" as const,
        gatewayOnline: false,
        updatedAt: 0,
      },
      lastCommand,
    };
  },
});

export const requestPairing = mutation({
  args: {},
  handler: async (ctx) => {
    const identity = await requireIdentity(ctx);
    const now = Date.now();

    const pending = await ctx.db
      .query("pairings")
      .withIndex("by_status", (q) => q.eq("status", "pending"))
      .collect();
    for (const row of pending) {
      await ctx.db.patch(row._id, { status: "expired" });
    }

    const nonce = crypto.randomUUID().replaceAll("-", "");
    const pairingId = await ctx.db.insert("pairings", {
      nonce,
      tokenIdentifier: identity.tokenIdentifier,
      email: identity.email,
      status: "pending",
      expiresAt: now + PAIR_WINDOW_MS,
      createdAt: now,
    });
    await ctx.scheduler.runAfter(0, internal.mqtt.runPairing, {
      pairingId,
      nonce,
    });
    return { expiresAt: now + PAIR_WINDOW_MS };
  },
});

export const toggleDoor = mutation({
  args: {},
  handler: async (ctx) => {
    const identity = await requireIdentity(ctx);
    const owner = await ctx.db
      .query("owners")
      .withIndex("by_token", (q) => q.eq("tokenIdentifier", identity.tokenIdentifier))
      .unique();
    if (!owner) {
      throw new Error("Press SW1 on the gateway to claim this garage first");
    }
    const commandId = await ctx.db.insert("commands", {
      source: "web",
      status: "queued",
      requestedAt: Date.now(),
    });
    await ctx.scheduler.runAfter(0, internal.mqtt.publishToggle, { commandId });
    return commandId;
  },
});

export const confirmPairing = internalMutation({
  args: { nonce: v.string() },
  handler: async (ctx, args) => {
    const pairing = await ctx.db
      .query("pairings")
      .withIndex("by_nonce", (q) => q.eq("nonce", args.nonce))
      .unique();
    if (!pairing || pairing.status !== "pending" || pairing.expiresAt <= Date.now()) {
      return false;
    }

    await ctx.db.patch(pairing._id, { status: "confirmed" });
    const existing = await ctx.db
      .query("owners")
      .withIndex("by_token", (q) => q.eq("tokenIdentifier", pairing.tokenIdentifier))
      .unique();
    if (!existing) {
      await ctx.db.insert("owners", {
        tokenIdentifier: pairing.tokenIdentifier,
        email: pairing.email,
        createdAt: Date.now(),
      });
    }
    return true;
  },
});

export const expirePairing = internalMutation({
  args: { pairingId: v.id("pairings") },
  handler: async (ctx, args) => {
    const pairing = await ctx.db.get(args.pairingId);
    if (pairing && pairing.status === "pending") {
      await ctx.db.patch(args.pairingId, { status: "expired" });
    }
  },
});

export const markCommand = internalMutation({
  args: {
    commandId: v.id("commands"),
    status: v.union(v.literal("sent"), v.literal("failed")),
    error: v.optional(v.string()),
  },
  handler: async (ctx, args) => {
    await ctx.db.patch(args.commandId, {
      status: args.status,
      error: args.error,
    });
  },
});

export const recordState = internalMutation({
  args: {
    state: v.union(
      v.literal("open"),
      v.literal("closed"),
      v.literal("unknown"),
    ),
    gatewayOnline: v.optional(v.boolean()),
  },
  handler: async (ctx, args) => {
    const existing = await ctx.db
      .query("doors")
      .withIndex("by_slug", (q) => q.eq("slug", DOOR_SLUG))
      .unique();
    const fields = {
      slug: DOOR_SLUG,
      state: args.state,
      gatewayOnline: args.gatewayOnline ?? existing?.gatewayOnline ?? false,
      updatedAt: Date.now(),
    };
    if (existing) {
      await ctx.db.patch(existing._id, fields);
      return existing._id;
    }
    return await ctx.db.insert("doors", fields);
  },
});
