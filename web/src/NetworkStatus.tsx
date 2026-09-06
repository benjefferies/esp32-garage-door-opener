import { useEffect, useState } from "react";
import {
  GATEWAY_AP_SSID,
  fetchGatewayStatus,
  fetchInternetReachable,
  type GatewayStatus,
} from "./gatewayApi";

export function useNetworkProbe(nonce?: string | null) {
  const [status, setStatus] = useState<GatewayStatus | null>(null);
  const [online, setOnline] = useState<boolean | null>(null);

  useEffect(() => {
    let cancelled = false;
    const poll = async () => {
      const [nextStatus, nextOnline] = await Promise.all([
        fetchGatewayStatus(nonce),
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
  }, [nonce]);

  return { status, online, onGateway: status !== null };
}

export function NetworkPills({
  onGateway,
  online,
}: {
  onGateway: boolean;
  online: boolean | null;
}) {
  return (
    <div className="net-pills" role="status" aria-live="polite">
      <span className={`pill ${onGateway ? "on" : "off"}`}>
        {GATEWAY_AP_SSID} {onGateway ? "connected" : "not connected"}
      </span>
      <span className={`pill ${online === true ? "on" : online === false ? "off" : "wait"}`}>
        {online === true ? "Online" : online === false ? "Offline" : "Checking network…"}
      </span>
    </div>
  );
}
