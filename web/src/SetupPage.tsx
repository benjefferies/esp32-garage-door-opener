import { useEffect, useRef, useState } from "react";
import {
  GATEWAY_AP_PASSWORD,
  GATEWAY_AP_SSID,
  GATEWAY_ORIGIN,
  fetchGatewayStatus,
  fetchInternetReachable,
  postGatewayWifi,
  type GatewayStatus,
} from "./gatewayApi";
import { type StoredPairing } from "./pairingStorage";
import { precacheAppShell } from "./precache";

type Props = {
  pairing: StoredPairing | null;
  onCancel: () => void;
};

export function SetupPage({ pairing, onCancel }: Props) {
  const [status, setStatus] = useState<GatewayStatus | null>(null);
  const [online, setOnline] = useState<boolean | null>(null);
  const [ssid, setSsid] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [useFormPost, setUseFormPost] = useState(false);
  const [joinedAp, setJoinedAp] = useState(false);
  const formRef = useRef<HTMLFormElement>(null);
  const remaining = useCountdown(pairing?.expiresAt ?? null);

  useEffect(() => {
    void precacheAppShell();
  }, []);

  useEffect(() => {
    let cancelled = false;
    const poll = async () => {
      const [nextStatus, nextOnline] = await Promise.all([
        fetchGatewayStatus(),
        fetchInternetReachable(),
      ]);
      if (!cancelled) {
        setStatus(nextStatus);
        setOnline(nextOnline);
      }
    };
    const onWake = () => {
      void poll();
    };
    void poll();
    const id = setInterval(() => {
      void poll();
    }, 1500);
    document.addEventListener("visibilitychange", onWake);
    window.addEventListener("focus", onWake);
    return () => {
      cancelled = true;
      clearInterval(id);
      document.removeEventListener("visibilitychange", onWake);
      window.removeEventListener("focus", onWake);
    };
  }, []);

  const onGateway = status !== null;
  const leftInternet = online === false;
  const onGarageGw = onGateway || joinedAp || (leftInternet && !saved);
  const nonce = pairing?.nonce ?? "";
  const ready = Boolean(pairing?.nonce);
  const pressedPair = Boolean(status?.sw1) || saved;
  const backOnline = saved && online === true;
  const showForm = onGarageGw && !saved && remaining > 0 && (pressedPair || !onGateway);

  const steps = [
    { done: ready, label: "Ready to start pairing" },
    { done: onGarageGw, label: `Connect to WiFi called ${GATEWAY_AP_SSID}` },
    { done: pressedPair, label: "Press pair button" },
    { done: saved, label: "Setup WiFi on gateway" },
    { done: backOnline, label: "Back online" },
  ];
  const currentIndex = steps.findIndex((step) => !step.done);

  async function saveWifi(event: React.FormEvent) {
    event.preventDefault();
    if (!ssid.trim()) {
      setError("Enter the home Wi-Fi name");
      return;
    }
    setBusy(true);
    setError(null);
    const result = await postGatewayWifi({
      ssid: ssid.trim(),
      password,
      nonce,
    });
    if (result.ok) {
      setSaved(true);
      setBusy(false);
      return;
    }
    if (result.unreachable) {
      setUseFormPost(true);
      setBusy(false);
      queueMicrotask(() => formRef.current?.submit());
      return;
    }
    setError(result.error === "press_sw1" ? "Press the pair button, then save again." : (result.error ?? "Save failed"));
    setBusy(false);
  }

  return (
    <main className="page">
      <header className="top">
        <h1>Garage</h1>
        <button type="button" className="link" onClick={onCancel}>
          Back
        </button>
      </header>
      <section className="card">
        <ul className="checklist">
          {steps.map((step, index) => {
            const current = index === currentIndex;
            return (
              <li key={step.label} className={step.done ? "done" : current ? "active" : "todo"}>
                <span className="mark" aria-hidden="true">
                  {step.done ? "✓" : ""}
                </span>
                <span>{step.label}</span>
              </li>
            );
          })}
        </ul>
        {pairing && remaining > 0 ? (
          <p className="meta">{formatRemaining(remaining)} left.</p>
        ) : pairing ? (
          <p className="error">Pairing expired. Go back online and start again.</p>
        ) : (
          <p className="error">Go back and tap Start pairing again.</p>
        )}
        {error ? <p className="error">{error}</p> : null}
        {saved ? (
          <button type="button" className="primary" onClick={onCancel} disabled={!backOnline}>
            {backOnline ? "Continue" : "Waiting for internet…"}
          </button>
        ) : showForm ? (
          <form
            ref={formRef}
            className="wifi-form"
            method="post"
            action={`${GATEWAY_ORIGIN}/api/wifi`}
            onSubmit={useFormPost ? undefined : saveWifi}
          >
            <input type="hidden" name="n" value={nonce} />
            <label>
              Home SSID
              <input
                name="ssid"
                value={ssid}
                autoComplete="off"
                autoCapitalize="none"
                onChange={(event) => setSsid(event.target.value)}
              />
            </label>
            <label>
              Password
              <input
                name="password"
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
              />
            </label>
            <button className="primary" disabled={busy || remaining <= 0 || (onGateway && !pressedPair)} type="submit">
              {busy ? "Sending…" : "Save to gateway"}
            </button>
          </form>
        ) : currentIndex === 1 ? (
          <>
            <p className="meta">
              Open Wi-Fi settings, join <strong>{GATEWAY_AP_SSID}</strong>,
              password <strong>{GATEWAY_AP_PASSWORD}</strong>. If a Wi-Fi login
              page opens, close it and come back to this Garage tab.
            </p>
            <p className="meta">
              Gateway {onGateway ? "reached" : "not reached"} · Internet{" "}
              {online === true ? "yes" : online === false ? "no" : "checking"}
            </p>
            <button type="button" className="primary" onClick={() => setJoinedAp(true)}>
              I&apos;m on {GATEWAY_AP_SSID}
            </button>
          </>
        ) : currentIndex === 2 ? (
          <p className="meta">Press the pair button (SW1) on the gateway.</p>
        ) : currentIndex === 3 ? (
          <p className="meta">Enter the home Wi-Fi name and password to save on the gateway.</p>
        ) : null}
      </section>
    </main>
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
