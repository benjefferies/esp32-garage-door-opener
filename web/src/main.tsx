import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { ClerkProvider, useAuth } from "@clerk/react";
import { ConvexProviderWithClerk } from "convex/react-clerk";
import { ConvexReactClient } from "convex/react";
import App from "./App.tsx";
import "./index.css";

const convexUrl = import.meta.env.VITE_CONVEX_URL;
const clerkKey = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY ?? "";
if (!convexUrl) {
  throw new Error("VITE_CONVEX_URL is not set");
}

const convex = new ConvexReactClient(convexUrl);

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    {clerkKey ? (
      <ClerkProvider publishableKey={clerkKey} afterSignOutUrl="/">
        <ConvexProviderWithClerk client={convex} useAuth={useAuth}>
          <App />
        </ConvexProviderWithClerk>
      </ClerkProvider>
    ) : (
      <main className="page">
        <h1>Garage</h1>
        <p>Set VITE_CLERK_PUBLISHABLE_KEY and redeploy.</p>
      </main>
    )}
  </StrictMode>,
);
