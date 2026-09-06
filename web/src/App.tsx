import { useEffect, useState } from "react";
import { SignInButton, UserButton } from "@clerk/react";
import { Authenticated, AuthLoading, Unauthenticated, useMutation, useQuery } from "convex/react";
import { api } from "../convex/_generated/api";
import { GATEWAY_AP_SSID } from "./gatewayApi";
import { clearPairing, readPairing, writePairing } from "./pairingStorage";

type Props = {
  onStartSetup: () => void;
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
          <button type="button" className="primary" onClick={onStartSetup}>
            Continue on {GATEWAY_AP_SSID}
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
            <button type="button" className="link" onClick={onStartSetup}>
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
  useEffect(() => {
    if (status?.isOwner) {
      clearPairing();
    }
  }, [status?.isOwner]);
  if (status === undefined) {
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
  onStartSetup: () => void;
}) {
  const requestPairing = useMutation(api.door.requestPairing);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const remaining = useCountdown(expiresAt);

  useEffect(() => {
    if (nonce && expiresAt) {
      writePairing({ nonce, expiresAt });
    }
  }, [nonce, expiresAt]);

  return (
    <section className="card">
      <p className="lede">
        Pair from this phone while you can still reach the internet. This page
        is cached, so after you join <strong>{GATEWAY_AP_SSID}</strong> you can
        come back here and send Wi-Fi to the gateway.
      </p>
      {remaining > 0 ? (
        <p className="state state-unknown">
          Pairing open — <strong>{formatRemaining(remaining)}</strong> left
        </p>
      ) : (
        <p className="meta">No pairing window is open.</p>
      )}
      {error ? <p className="error">{error}</p> : null}
      {remaining > 0 ? (
        <button className="primary" type="button" onClick={onStartSetup}>
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
            void requestPairing()
              .then((result) => {
                writePairing(result);
                onStartSetup();
              })
              .catch((err: Error) => setError(err.message))
              .finally(() => setBusy(false));
          }}
        >
          {busy ? "Starting…" : "Start pairing"}
        </button>
      )}
    </section>
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
