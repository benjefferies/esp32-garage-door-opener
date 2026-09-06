import { useEffect, useRef, useState } from "react";
import {
  GATEWAY_AP_SSID,
  GATEWAY_ORIGIN,
  fetchGatewayStatus,
  fetchInternetReachable,
  postGatewayWifi,
  type GatewayStatus,
} from "./gatewayApi";
import { readPairing } from "./pairingStorage";
import { precacheAppShell } from "./precache";

type Props = {
  onCancel: () => void;
};

export function SetupPage({ onCancel }: Props) {
  const pairing = readPairing();
  const [status, setStatus] = useState<GatewayStatus | null>(null);
  const [online, setOnline] = useState<boolean | null>(null);
  const [ssid, setSsid] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [useFormPost, setUseFormPost] = useState(false);
  const [offlineReady, setOfflineReady] = useState(false);
  const formRef = useRef<HTMLFormElement>(null);
  const remaining = useCountdown(pairing?.expiresAt ?? null);

  useEffect(() => {
    void precacheAppShell().then(() => setOfflineReady(true));
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
  const onGarageGw = onGateway || (leftInternet && !saved);
  const nonce = pairing?.nonce ?? "";
  const pairingStarted = Boolean(nonce);
  const sw1 = Boolean(status?.sw1);
  const showForm = onGarageGw && !saved && remaining > 0;

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
    setError(result.error === "press_sw1" ? "Press SW1 on the gateway, then save again." : (result.error ?? "Save failed"));
    setBusy(false);
  }

  const steps = [
    { done: pairingStarted, label: "Pairing started on this phone" },
    { done: offlineReady, label: "Offline copy of this tab is ready" },
    {
      done: onGarageGw,
      label: onGateway
        ? `Connected to ${GATEWAY_AP_SSID}`
        : leftInternet
          ? `No internet — join ${GATEWAY_AP_SSID} if you have not already`
          : `Join ${GATEWAY_AP_SSID} in Wi-Fi settings, then return here`,
    },
    { done: sw1, label: "Press SW1 on the gateway" },
    { done: saved, label: "Save home Wi-Fi to the gateway" },
    {
      done: saved && online === true,
      label: saved ? "Rejoin home Wi-Fi or cellular" : "Back on the internet",
    },
  ];

  return (
    <main className="page">
      <header className="top">
        <h1>Garage</h1>
        <button type="button" className="link" onClick={onCancel}>
          Back
        </button>
      </header>
      <section className="card">
        <p className="lede">
          The browser cannot read the Wi-Fi name. This list watches for the
          gateway at {GATEWAY_ORIGIN} and whether this site can reach the
          internet again.
        </p>
        <ul className="checklist">
          {steps.map((step) => (
            <li key={step.label} className={step.done ? "done" : "todo"}>
              <span className="mark" aria-hidden="true">
                {step.done ? "✓" : ""}
              </span>
              <span>{step.label}</span>
            </li>
          ))}
        </ul>
        {remaining > 0 ? (
          <p className="meta">{formatRemaining(remaining)} left to finish pairing.</p>
        ) : (
          <p className="error">Pairing window expired. Go back online and start again.</p>
        )}
        {error ? <p className="error">{error}</p> : null}
        {saved ? (
          <button type="button" className="primary" onClick={onCancel} disabled={online !== true}>
            {online === true ? "I'm back on the internet" : "Waiting for internet…"}
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
            <button className="primary" disabled={busy || remaining <= 0 || (onGateway && !sw1)} type="submit">
              {busy ? "Sending…" : "Save to gateway"}
            </button>
          </form>
        ) : (
          <p className="meta">
            Open Wi-Fi settings, join <strong>{GATEWAY_AP_SSID}</strong> (no
            password), then come back to this tab.
          </p>
        )}
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
