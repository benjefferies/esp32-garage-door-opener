import { useEffect, useState } from "react";
import { SignInButton, UserButton } from "@clerk/react";
import { Authenticated, AuthLoading, Unauthenticated, useMutation, useQuery } from "convex/react";
import { api } from "../convex/_generated/api";

export default function App() {
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
      </AuthLoading>
      <Unauthenticated>
        <section className="card">
          <p className="lede">
            Sign in to continue. New accounts are invite-only; then press SW1 on the
            gateway to prove you own the door.
          </p>
          <SignInButton mode="modal">
            <button type="button" className="primary">
              Sign in
            </button>
          </SignInButton>
        </section>
      </Unauthenticated>
      <Authenticated>
        <GarageHome />
      </Authenticated>
    </main>
  );
}

function GarageHome() {
  const status = useQuery(api.door.getStatus);
  if (status === undefined) {
    return <p>Loading…</p>;
  }
  if (!status.isOwner) {
    return <ClaimPanel expiresAt={status.pairing?.expiresAt ?? null} />;
  }
  return <DoorPanel />;
}

function ClaimPanel({ expiresAt }: { expiresAt: number | null }) {
  const requestPairing = useMutation(api.door.requestPairing);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const remaining = useCountdown(expiresAt);

  return (
    <section className="card">
      <p className="lede">
        This account cannot move the door until you prove you are at the gateway.
        Start pairing, then press <strong>SW1</strong> within 60 seconds.
      </p>
      {remaining > 0 ? (
        <p className="state state-unknown">
          Press SW1 now — <strong>{remaining}s</strong> left
        </p>
      ) : (
        <p className="meta">No pairing window is open.</p>
      )}
      {error ? <p className="error">{error}</p> : null}
      <button
        className="primary"
        disabled={busy || remaining > 0}
        onClick={() => {
          setBusy(true);
          setError(null);
          void requestPairing()
            .catch((err: Error) => setError(err.message))
            .finally(() => setBusy(false));
        }}
      >
        {busy ? "Starting…" : remaining > 0 ? "Waiting for SW1…" : "Start pairing"}
      </button>
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
