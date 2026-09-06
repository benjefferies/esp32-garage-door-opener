import { useEffect, useState } from "react";
import { SignInButton, UserButton } from "@clerk/react";
import { Authenticated, AuthLoading, Unauthenticated, useMutation, useQuery } from "convex/react";
import { api } from "../convex/_generated/api";
import { GATEWAY_AP_PASSWORD, GATEWAY_AP_SSID } from "./gatewayApi";
import { NetworkPills, useNetworkProbe } from "./NetworkStatus";
import {
  clearPairing,
  pairingWifiSaved,
  readPairing,
  saveStartedPairing,
  writePairing,
  type StoredPairing,
} from "./pairingStorage";

type Props = {
  onStartSetup: (pairing?: StoredPairing) => void;
};

export default function App({ onStartSetup }: Props) {
  const stored = readPairing();
  return (
    <main className="page">
      <header className="top">
        <h1>Garage</h1>
        <Authenticated>
          <UserButton />
        </Authenticated>
      </header>
      <AuthLoading>
        <p>Loading…</p>
        {stored ? (
          <button type="button" className="primary" onClick={() => onStartSetup(stored)}>
            Continue pairing
          </button>
        ) : null}
      </AuthLoading>
      <Unauthenticated>
        <section className="card">
          <p className="lede">
            Sign in to continue. New accounts are invite-only; then pair at the
            gateway over its setup Wi-Fi.
          </p>
          <SignInButton mode="modal">
            <button type="button" className="primary">
              Sign in
            </button>
          </SignInButton>
          {stored ? (
            <button type="button" className="link" onClick={() => onStartSetup(readPairing() ?? undefined)}>
              Continue on {GATEWAY_AP_SSID}
            </button>
          ) : null}
        </section>
      </Unauthenticated>
      <Authenticated>
        <GarageHome onStartSetup={onStartSetup} />
      </Authenticated>
    </main>
  );
}

function GarageHome({ onStartSetup }: Props) {
  const status = useQuery(api.door.getStatus);
  const stored = readPairing();
  const [waited, setWaited] = useState(false);
  useEffect(() => {
    const id = setTimeout(() => setWaited(true), 2000);
    return () => clearTimeout(id);
  }, []);
  useEffect(() => {
    if (status?.isOwner) {
      clearPairing();
    }
  }, [status?.isOwner]);
  if (status === undefined) {
    if (waited && stored) {
      return (
        <section className="card">
          <p className="lede">The app cannot reach the internet. Continue pairing on the gateway network.</p>
          <button type="button" className="primary" onClick={() => onStartSetup(stored)}>
            Continue pairing
          </button>
        </section>
      );
    }
    return <p>Loading…</p>;
  }
  if (!status.isOwner) {
    return (
      <ClaimPanel
        expiresAt={status.pairing?.expiresAt ?? null}
        nonce={status.pairing?.nonce ?? null}
        onStartSetup={onStartSetup}
      />
    );
  }
  return <DoorPanel />;
}

function ClaimPanel({
  expiresAt,
  nonce,
  onStartSetup,
}: {
  expiresAt: number | null;
  nonce: string | null;
  onStartSetup: (pairing?: StoredPairing) => void;
}) {
  const requestPairing = useMutation(api.door.requestPairing);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const remaining = useCountdown(expiresAt);
  const wifiSaved = pairingWifiSaved();
  const { onGateway, online } = useNetworkProbe();

  useEffect(() => {
    if (nonce && expiresAt) {
      const current = readPairing();
      writePairing({
        nonce,
        expiresAt,
        wifiSaved: current?.nonce === nonce ? current.wifiSaved : undefined,
      });
    }
  }, [nonce, expiresAt]);

  return (
    <>
      <NetworkPills onGateway={onGateway} online={online} />
      <section className="card">
        {wifiSaved && remaining > 0 ? (
          <p className="lede">
            Home Wi-Fi is saved on the gateway. Pairing finishes when that board
            comes back online — stay on this page.
          </p>
        ) : (
          <p className="lede">
            Pair from this phone while you can still reach the internet. This page
            is cached, so after you join <strong>{GATEWAY_AP_SSID}</strong> (password{" "}
            <strong>{GATEWAY_AP_PASSWORD}</strong>) you can come back here and send
            Wi-Fi to the gateway.
          </p>
        )}
        {wifiSaved && remaining > 0 ? (
          <p className="state state-unknown">
            Waiting for the gateway — <strong>{formatRemaining(remaining)}</strong> left
          </p>
        ) : remaining > 0 ? (
          <p className="state state-unknown">
            Pairing open — <strong>{formatRemaining(remaining)}</strong> left
          </p>
        ) : (
          <p className="meta">No pairing window is open.</p>
        )}
        {error ? <p className="error">{error}</p> : null}
        {wifiSaved && remaining > 0 ? (
          <p className="meta">Rejoin home Wi-Fi if you have not already.</p>
        ) : remaining > 0 ? (
          <button
            className="primary"
            type="button"
            onClick={() => {
              if (nonce && expiresAt) {
                onStartSetup(saveStartedPairing({ nonce, expiresAt }));
                return;
              }
              onStartSetup();
            }}
          >
            I&apos;m ready to join {GATEWAY_AP_SSID}
          </button>
        ) : (
          <button
            className="primary"
            disabled={busy}
            type="button"
            onClick={() => {
              setBusy(true);
              setError(null);
              void requestPairing({ nonce: crypto.randomUUID().replaceAll("-", "") })
                .then((result) => {
                  onStartSetup(saveStartedPairing(result));
                })
                .catch((err: Error) => setError(err.message))
                .finally(() => setBusy(false));
            }}
          >
            {busy ? "Starting…" : "Start pairing"}
          </button>
        )}
      </section>
    </>
  );
}

function DoorPanel() {
  const status = useQuery(api.door.getStatus);
  const toggleDoor = useMutation(api.door.toggleDoor);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const doorState = status?.door?.state ?? "unknown";
  const last = status?.lastCommand;

  return (
    <section className="card">
      <p className={`state state-${doorState}`}>
        Door is <strong>{doorState}</strong>
      </p>
      {last ? (
        <p className="meta">
          Last command {last.status}
          {last.error ? `: ${last.error}` : ""}
        </p>
      ) : (
        <p className="meta">No commands yet. Reed state updates when the gateway is online.</p>
      )}
      {error ? <p className="error">{error}</p> : null}
      <button
        className="primary"
        disabled={busy}
        onClick={() => {
          setBusy(true);
          setError(null);
          void toggleDoor()
            .catch((err: Error) => setError(err.message))
            .finally(() => setBusy(false));
        }}
      >
        {busy ? "Sending…" : "Toggle garage"}
      </button>
    </section>
  );
}

function formatRemaining(totalSeconds: number) {
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return minutes > 0 ? `${minutes}m ${seconds}s` : `${seconds}s`;
}

function useCountdown(expiresAt: number | null) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (!expiresAt) {
      return;
    }
    const id = setInterval(() => setNow(Date.now()), 250);
    return () => clearInterval(id);
  }, [expiresAt]);
  if (!expiresAt) {
    return 0;
  }
  return Math.max(0, Math.ceil((expiresAt - now) / 1000));
}
