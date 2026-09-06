import { useEffect, useRef, useState } from "react";
import {
  GATEWAY_AP_PASSWORD,
  GATEWAY_AP_SSID,
  GATEWAY_ORIGIN,
  postGatewayWifi,
} from "./gatewayApi";
import { NetworkPills, useNetworkProbe } from "./NetworkStatus";
import { markWifiSaved, pairingWifiSaved, type StoredPairing } from "./pairingStorage";
import { precacheAppShell } from "./precache";
import { parseSetupHash } from "./setupHash";

type Props = {
  pairing: StoredPairing | null;
  onCancel: () => void;
};

export function SetupPage({ pairing, onCancel }: Props) {
  const { status, online, onGateway, probe } = useNetworkProbe(pairing?.nonce);
  const [ssid, setSsid] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(
    () => parseSetupHash().wifiSaved || pairing?.wifiSaved === true || pairingWifiSaved(),
  );
  const [error, setError] = useState<string | null>(null);
  const [useFormPost, setUseFormPost] = useState(false);
  const formRef = useRef<HTMLFormElement>(null);
  const remaining = useCountdown(pairing?.expiresAt ?? null);

  useEffect(() => {
    void precacheAppShell();
  }, []);

  useEffect(() => {
    if (parseSetupHash().wifiSaved) {
      markWifiSaved();
      setSaved(true);
    }
  }, []);

  const onGarageGw = saved || onGateway;
  const nonce = pairing?.nonce ?? "";
  const ready = Boolean(pairing?.nonce);
  const pressedPair = Boolean(status?.sw1) || saved;
  const backOnline = saved && online === true;
  const showForm = onGateway && !saved && remaining > 0 && pressedPair;

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
      markWifiSaved();
      setSaved(true);
      setBusy(false);
      return;
    }
    if (result.unreachable) {
      // HTTPS pages cannot fetch http://192.168.4.1. Do not treat that as
      // a successful write — the last attempt never created wifi.json.
      setUseFormPost(true);
      setError(
        "The app could not confirm a save. Stay on garage-gw and try again, or open http://192.168.4.1",
      );
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
      <NetworkPills onGateway={onGateway} online={online} />
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
        {probe ? (
          <p className="probe">
            Ping {GATEWAY_ORIGIN}/api/status —{" "}
            {probe.ok
              ? `ok in ${probe.ms}ms (sw1 ${probe.status?.sw1 ? "yes" : "no"})`
              : `${probe.error ?? "failed"} in ${probe.ms}ms`}
            {probe.detail ? ` · ${probe.detail}` : ""}
            {` · page ${window.location.protocol}//${window.location.host}`}
          </p>
        ) : (
          <p className="probe">Pinging {GATEWAY_ORIGIN}/api/status…</p>
        )}
        {saved ? (
          <button type="button" className="primary" onClick={onCancel} disabled={!backOnline}>
            {backOnline ? "Continue" : "Waiting for internet…"}
          </button>
        ) : showForm ? (
          <>
          <iframe name="gateway-save" title="Save to gateway" hidden />
          <form
            ref={formRef}
            className="wifi-form"
            method="post"
            action={`${GATEWAY_ORIGIN}/api/wifi`}
            target="gateway-save"
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
          </>
        ) : currentIndex === 1 ? (
          <p className="meta">
            Open Wi-Fi settings, join <strong>{GATEWAY_AP_SSID}</strong>,
            password <strong>{GATEWAY_AP_PASSWORD}</strong>. This page pings{" "}
            <a href={`${GATEWAY_ORIGIN}/api/status`}>{GATEWAY_ORIGIN}</a> and
            marks this step when that answers. If a Wi-Fi login page opens,
            close it and come back here. If the pill stays red, open{" "}
            <a href={GATEWAY_ORIGIN}>{GATEWAY_ORIGIN}</a>.
          </p>
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
