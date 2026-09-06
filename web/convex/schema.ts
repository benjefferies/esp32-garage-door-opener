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
});
