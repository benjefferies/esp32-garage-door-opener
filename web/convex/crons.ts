import { cronJobs } from "convex/server";
import { internal } from "./_generated/api";

const crons = cronJobs();
crons.interval("watch gateway mqtt", { seconds: 60 }, internal.mqtt.watchGateway);

export default crons;
