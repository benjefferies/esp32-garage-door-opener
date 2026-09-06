import { StrictMode, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { ClerkProvider, useAuth } from "@clerk/react";
import { ConvexProviderWithClerk } from "convex/react-clerk";
import { ConvexReactClient } from "convex/react";
import App from "./App.tsx";
import { SetupPage } from "./SetupPage.tsx";
import { fetchGatewayStatus, fetchInternetReachable } from "./gatewayApi.ts";
import { precacheAppShell } from "./precache.ts";
import {
  markSetupHidden,
  markWifiSaved,
  readPairing,
  resumeAfterCaptive,
  type StoredPairing,
} from "./pairingStorage.ts";
import { parseSetupHash } from "./setupHash.ts";
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
  return parseSetupHash().isSetup;
}

function Root() {
  const [hashSetup, setHashSetup] = useState(isSetupHash);
  const [pairing, setPairing] = useState<StoredPairing | null>(() => {
    if (parseSetupHash().wifiSaved) {
      return markWifiSaved() ?? readPairing();
    }
    return readPairing();
  });
  const [onGateway, setOnGateway] = useState(false);
  const [online, setOnline] = useState<boolean | null>(null);
  const [stayInApp, setStayInApp] = useState(false);

  useEffect(() => {
    const onHash = () => {
      const next = isSetupHash();
      setHashSetup(next);
      if (next) {
        setStayInApp(false);
        if (parseSetupHash().wifiSaved) {
          const stored = markWifiSaved();
          setPairing(stored ?? readPairing());
        } else {
          setPairing((current) => readPairing() ?? current);
        }
      }
    };
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  useEffect(() => {
    let cancelled = false;
    const poll = async () => {
      const [status, reachable] = await Promise.all([
        fetchGatewayStatus(readPairing()?.nonce),
        fetchInternetReachable(),
      ]);
      if (cancelled) {
        return;
      }
      setOnGateway(status !== null);
      setOnline(reachable);
      const resumed = resumeAfterCaptive({
        online: reachable,
        onGateway: status !== null,
      });
      if (resumed) {
        setPairing(resumed);
      }
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

  useEffect(() => {
    const onHide = () => {
      markSetupHidden();
    };
    const onShow = () => {
      void (async () => {
        const [status, reachable] = await Promise.all([
          fetchGatewayStatus(readPairing()?.nonce),
          fetchInternetReachable(),
        ]);
        const resumed = resumeAfterCaptive({
          online: reachable,
          onGateway: status !== null,
        });
        setOnGateway(status !== null);
        setOnline(reachable);
        if (resumed) {
          setPairing(resumed);
        }
      })();
    };
    const onVisibility = () => {
      if (document.visibilityState === "hidden") {
        onHide();
      } else {
        onShow();
      }
    };
    document.addEventListener("visibilitychange", onVisibility);
    window.addEventListener("pagehide", onHide);
    window.addEventListener("pageshow", onShow);
    return () => {
      document.removeEventListener("visibilitychange", onVisibility);
      window.removeEventListener("pagehide", onHide);
      window.removeEventListener("pageshow", onShow);
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

  const wifiSaved = pairing?.wifiSaved === true;
  const backInApp = wifiSaved && online === true;
  const setup =
    !stayInApp &&
    !backInApp &&
    (hashSetup || onGateway || (pairing !== null && online !== true));

  if (setup) {
    return (
      <SetupPage
        pairing={pairing}
        onPairingChange={setPairing}
        onCancel={() => {
          if (onGateway && !wifiSaved) {
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
