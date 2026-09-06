import { useEffect, useRef, useState } from "react";
import {
  GATEWAY_AP_PASSWORD,
  GATEWAY_AP_SSID,
  GATEWAY_ORIGIN,
  postGatewayWifi,
} from "./gatewayApi";
import { NetworkPills, useNetworkProbe } from "./NetworkStatus";
import { PairingChecklist } from "./PairingChecklist";
import {
  markAwaitingCaptive,
  markJoinedAp,
  markLeftSetup,
  markPairPressed,
  markWifiSaved,
  pairingWifiSaved,
  type StoredPairing,
} from "./pairingStorage";
import { precacheAppShell } from "./precache";
import { parseSetupHash } from "./setupHash";

type Props = {
  pairing: StoredPairing | null;
  onCancel: () => void;
  onPairingChange?: (pairing: StoredPairing) => void;
};

export function SetupPage({ pairing, onCancel, onPairingChange }: Props) {
  const { status, online, onGateway, probe } = useNetworkProbe(pairing?.nonce);
  const [ssid, setSsid] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(
    () => parseSetupHash().wifiSaved || pairing?.wifiSaved === true || pairingWifiSaved(),
  );
  const [joinedAp, setJoinedAp] = useState(() => Boolean(pairing?.joinedAp));
  const [pairPressed, setPairPressed] = useState(() => Boolean(pairing?.pairPressed));
  const [error, setError] = useState<string | null>(null);
  const [useFormPost, setUseFormPost] = useState(false);
  const formRef = useRef<HTMLFormElement>(null);
  const advanced = useRef(false);
  const remaining = useCountdown(pairing?.expiresAt ?? null);

  useEffect(() => {
    void precacheAppShell();
    const next = markAwaitingCaptive();
    if (next) {
      onPairingChange?.(next);
    }
  }, [onPairingChange]);

  useEffect(() => {
    if (parseSetupHash().wifiSaved) {
      const next = markWifiSaved();
      setSaved(true);
      setJoinedAp(true);
      setPairPressed(true);
      if (next) {
        onPairingChange?.(next);
      }
    }
  }, [onPairingChange]);

  useEffect(() => {
    if (pairing?.wifiSaved) {
      setSaved(true);
    }
    if (pairing?.joinedAp) {
      setJoinedAp(true);
    }
    if (pairing?.pairPressed) {
      setPairPressed(true);
    }
  }, [pairing?.joinedAp, pairing?.pairPressed, pairing?.wifiSaved]);

  useEffect(() => {
    if (!onGateway) {
      return;
    }
    setJoinedAp(true);
    const next = markJoinedAp();
    if (next) {
      onPairingChange?.(next);
    }
  }, [onGateway, onPairingChange]);

  useEffect(() => {
    if (!status?.sw1) {
      return;
    }
    setPairPressed(true);
    setJoinedAp(true);
    const next = markPairPressed();
    if (next) {
      onPairingChange?.(next);
    }
  }, [onPairingChange, status?.sw1]);

  const nonce = pairing?.nonce ?? "";
  const ready = Boolean(pairing?.nonce);
  const onGarageGw = saved || joinedAp || onGateway;
  const pressedPair = saved || pairPressed || Boolean(status?.sw1);
  const backOnline = saved && online === true;
  const showForm = onGateway && !saved && remaining > 0 && pressedPair;
  const gatewaySetupHref = nonce ? `${GATEWAY_ORIGIN}/?n=${encodeURIComponent(nonce)}` : GATEWAY_ORIGIN;
  const showOpenGateway = !saved && remaining > 0 && !onGarageGw;

  useEffect(() => {
    if (advanced.current || !saved || online !== true) {
      return;
    }
    advanced.current = true;
    onCancel();
  }, [onCancel, online, saved]);

  const currentIndex = [
    ready,
    onGarageGw,
    pressedPair,
    saved,
    backOnline,
  ].findIndex((step) => !step);

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
      const next = markWifiSaved();
      setSaved(true);
      setJoinedAp(true);
      setPairPressed(true);
      if (next) {
        onPairingChange?.(next);
      }
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
        <button
          type="button"
          className="link"
          onClick={() => {
            if (!saved) {
              markLeftSetup();
            }
            onCancel();
          }}
        >
          Back
        </button>
      </header>
      <NetworkPills onGateway={onGateway} online={online} />
      <section className="card">
        <PairingChecklist
          ready={ready}
          joinedAp={onGarageGw}
          pairPressed={pressedPair}
          wifiSaved={saved}
          online={online}
        />
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
        ) : showOpenGateway || currentIndex === 1 ? (
          <>
            <p className="meta">
              Open Wi-Fi settings, join <strong>{GATEWAY_AP_SSID}</strong>,
              password <strong>{GATEWAY_AP_PASSWORD}</strong>. The phone should
              open a Garage login sheet — press SW1 and save home Wi-Fi there.
              This HTTPS tab cannot talk to the gateway. If the sheet does not
              appear, open the setup page on the board.
            </p>
            <a
              className="primary"
              href={gatewaySetupHref}
              onClick={() => {
                const next = markJoinedAp();
                setJoinedAp(true);
                if (next) {
                  onPairingChange?.(next);
                }
              }}
            >
              Open gateway setup
            </a>
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
