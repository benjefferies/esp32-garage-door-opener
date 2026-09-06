import { StrictMode, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { ClerkProvider, useAuth } from "@clerk/react";
import { ConvexProviderWithClerk } from "convex/react-clerk";
import { ConvexReactClient } from "convex/react";
import App from "./App.tsx";
import { SetupPage } from "./SetupPage.tsx";
import { precacheAppShell } from "./precache.ts";
import "./index.css";

const convexUrl = import.meta.env.VITE_CONVEX_URL;
const clerkKey = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY ?? "";
if (!convexUrl) {
  throw new Error("VITE_CONVEX_URL is not set");
}

const convex = new ConvexReactClient(convexUrl);

if (import.meta.env.PROD && "serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    void navigator.serviceWorker.register("/sw.js").then(() => precacheAppShell());
  });
}

function isSetupHash() {
  return window.location.hash.replace(/^#/, "") === "setup";
}

function Root() {
  const [setup, setSetup] = useState(isSetupHash);

  useEffect(() => {
    const onHash = () => setSetup(isSetupHash());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  if (setup) {
    return (
      <SetupPage
        onCancel={() => {
          window.location.hash = "";
        }}
      />
    );
  }

  if (!clerkKey) {
    return (
      <main className="page">
        <h1>Garage</h1>
        <p>Set VITE_CLERK_PUBLISHABLE_KEY and redeploy.</p>
      </main>
    );
  }

  return (
    <ClerkProvider publishableKey={clerkKey} afterSignOutUrl="/">
      <ConvexProviderWithClerk client={convex} useAuth={useAuth}>
        <App
          onStartSetup={() => {
            window.location.hash = "setup";
          }}
        />
      </ConvexProviderWithClerk>
    </ClerkProvider>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <Root />
  </StrictMode>,
);
