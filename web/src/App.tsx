import { useState } from "react";
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
          <p className="lede">Sign in with Clerk to send a toggle to the door.</p>
          <SignInButton mode="modal">
            <button type="button" className="primary">
              Sign in
            </button>
          </SignInButton>
        </section>
      </Unauthenticated>
      <Authenticated>
        <DoorPanel />
      </Authenticated>
    </main>
  );
}

function DoorPanel() {
  const status = useQuery(api.door.getStatus);
  const toggleDoor = useMutation(api.door.toggleDoor);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const doorState = status?.door.state ?? "unknown";
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
