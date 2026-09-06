import { StrictMode, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { ClerkProvider, useAuth } from "@clerk/react";
import { ConvexProviderWithClerk } from "convex/react-clerk";
import { ConvexReactClient } from "convex/react";
import App from "./App.tsx";
import { SetupPage } from "./SetupPage.tsx";
import { fetchGatewayStatus, fetchInternetReachable } from "./gatewayApi.ts";
import { precacheAppShell } from "./precache.ts";
import { readPairing, type StoredPairing } from "./pairingStorage.ts";
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
  const [hashSetup, setHashSetup] = useState(isSetupHash);
  const [pairing, setPairing] = useState<StoredPairing | null>(readPairing);
  const [onGateway, setOnGateway] = useState(false);
  const [online, setOnline] = useState<boolean | null>(null);
  const [stayInApp, setStayInApp] = useState(false);

  useEffect(() => {
    const onHash = () => {
      const next = isSetupHash();
      setHashSetup(next);
      if (next) {
        setStayInApp(false);
        setPairing((current) => current ?? readPairing());
      }
    };
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  useEffect(() => {
    let cancelled = false;
    const poll = async () => {
      const [status, reachable] = await Promise.all([
        fetchGatewayStatus(),
        fetchInternetReachable(),
      ]);
      if (cancelled) {
        return;
      }
      setOnGateway(status !== null);
      setOnline(reachable);
      if (status !== null) {
        setStayInApp(false);
      }
    };
    void poll();
    const id = setInterval(() => {
      void poll();
    }, 1500);
    const onWake = () => {
      void poll();
    };
    document.addEventListener("visibilitychange", onWake);
    window.addEventListener("focus", onWake);
    return () => {
      cancelled = true;
      clearInterval(id);
      document.removeEventListener("visibilitychange", onWake);
      window.removeEventListener("focus", onWake);
    };
  }, []);

  const startSetup = (next?: StoredPairing) => {
    if (next) {
      setPairing(next);
    } else {
      setPairing((current) => current ?? readPairing());
    }
    setStayInApp(false);
    window.location.hash = "setup";
    setHashSetup(true);
  };

  const setup =
    !stayInApp && (hashSetup || onGateway || (pairing !== null && online !== true));

  if (setup) {
    return (
      <SetupPage
        pairing={pairing}
        onCancel={() => {
          if (onGateway) {
            return;
          }
          setStayInApp(true);
          setHashSetup(false);
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
        <App onStartSetup={startSetup} />
      </ConvexProviderWithClerk>
    </ClerkProvider>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <Root />
  </StrictMode>,
);
