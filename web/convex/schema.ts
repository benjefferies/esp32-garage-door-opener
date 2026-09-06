import { defineSchema, defineTable } from "convex/server";
import { v } from "convex/values";

export default defineSchema({
  doors: defineTable({
    slug: v.string(),
    state: v.union(
      v.literal("open"),
      v.literal("closed"),
      v.literal("unknown"),
    ),
    gatewayOnline: v.boolean(),
    updatedAt: v.number(),
    lastHeartbeatAt: v.optional(v.number()),
    lastStateAt: v.optional(v.number()),
  }).index("by_slug", ["slug"]),
  commands: defineTable({
    source: v.string(),
    status: v.union(
      v.literal("queued"),
      v.literal("sent"),
      v.literal("failed"),
    ),
    error: v.optional(v.string()),
    requestedAt: v.number(),
  }).index("by_requestedAt", ["requestedAt"]),
  owners: defineTable({
    tokenIdentifier: v.string(),
    email: v.optional(v.string()),
    createdAt: v.number(),
  }).index("by_token", ["tokenIdentifier"]),
  pairings: defineTable({
    nonce: v.string(),
    tokenIdentifier: v.string(),
    email: v.optional(v.string()),
    status: v.union(
      v.literal("pending"),
      v.literal("confirmed"),
      v.literal("expired"),
    ),
    expiresAt: v.number(),
    createdAt: v.number(),
  })
    .index("by_nonce", ["nonce"])
    .index("by_status", ["status"])
    .index("by_token", ["tokenIdentifier"]),
});
