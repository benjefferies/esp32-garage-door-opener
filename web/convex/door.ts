import { v } from "convex/values";
import { internal } from "./_generated/api";
import { internalMutation, mutation, query } from "./_generated/server";

const DOOR_SLUG = "opener";

async function requireIdentity(ctx: { auth: { getUserIdentity: () => Promise<unknown> } }) {
  const identity = await ctx.auth.getUserIdentity();
  if (identity === null) {
    throw new Error("Not signed in");
  }
  return identity;
}

export const getStatus = query({
  args: {},
  handler: async (ctx) => {
    await requireIdentity(ctx);
    const door = await ctx.db
      .query("doors")
      .withIndex("by_slug", (q) => q.eq("slug", DOOR_SLUG))
      .unique();
    const lastCommand = await ctx.db.query("commands").order("desc").first();
    return {
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

export const toggleDoor = mutation({
  args: {},
  handler: async (ctx) => {
    await requireIdentity(ctx);
    const commandId = await ctx.db.insert("commands", {
      source: "web",
      status: "queued",
      requestedAt: Date.now(),
    });
    await ctx.scheduler.runAfter(0, internal.mqtt.publishToggle, { commandId });
    return commandId;
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
