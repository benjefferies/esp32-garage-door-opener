export const GATEWAY_ORIGIN = "http://192.168.4.1";
export const GATEWAY_AP_SSID = "garage-gw";
export const GATEWAY_AP_PASSWORD = "garage-gw";

export type GatewayStatus = {
  ok: boolean;
  sw1: boolean;
  ssid?: string;
  ip?: string;
  reason?: string;
};

export type GatewayProbe = {
  status: GatewayStatus | null;
  ok: boolean;
  ms: number;
  error?: string;
  detail?: string;
};

const GATEWAY_PING_MS = 2000;

export async function fetchInternetReachable(): Promise<boolean> {
  const url = new URL("/manifest.webmanifest", window.location.origin);
  url.searchParams.set("online", String(Date.now()));
  try {
    const response = await fetch(url, { cache: "no-store" });
    return response.ok;
  } catch {
    return false;
  }
}

export async function probeGateway(nonce?: string | null): Promise<GatewayProbe> {
  const started = Date.now();
  const url = new URL("/api/status", GATEWAY_ORIGIN);
  if (nonce) {
    url.searchParams.set("n", nonce);
  }
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), GATEWAY_PING_MS);
  try {
    const response = await fetch(url, {
      mode: "cors",
      cache: "no-store",
      signal: controller.signal,
    });
    if (!response.ok) {
      return {
        status: null,
        ok: false,
        ms: Date.now() - started,
        error: `HTTP ${response.status}`,
        detail: response.statusText || "Gateway rejected the ping",
      };
    }
    const status = (await response.json()) as GatewayStatus;
    return { status, ok: true, ms: Date.now() - started };
  } catch (err) {
    const ms = Date.now() - started;
    if (err instanceof DOMException && err.name === "AbortError") {
      return {
        status: null,
        ok: false,
        ms,
        error: "timeout",
        detail: `No answer in ${GATEWAY_PING_MS}ms. Not on garage-gw, or the board is down.`,
      };
    }
    const message = err instanceof Error ? err.message : String(err);
    const pageHttps = window.location.protocol === "https:";
    if (pageHttps) {
      return {
        status: null,
        ok: false,
        ms,
        error: "blocked",
        detail: `This HTTPS page cannot fetch ${GATEWAY_ORIGIN} (${message}). Opening that URL in the address bar works; the app fetch does not.`,
      };
    }
    return { status: null, ok: false, ms, error: "failed", detail: message };
  } finally {
    clearTimeout(timer);
  }
}

export async function fetchGatewayStatus(nonce?: string | null): Promise<GatewayStatus | null> {
  const probe = await probeGateway(nonce);
  return probe.status;
}

export async function postGatewayWifi(input: {
  ssid: string;
  password: string;
  nonce: string;
}): Promise<{ ok: boolean; error?: string; unreachable?: boolean }> {
  try {
    const response = await fetch(`${GATEWAY_ORIGIN}/api/wifi`, {
      method: "POST",
      mode: "cors",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        ssid: input.ssid,
        password: input.password,
        nonce: input.nonce,
      }),
    });
    const data = (await response.json()) as { ok?: boolean; error?: string };
    if (!response.ok) {
      return { ok: false, error: data.error ?? "Gateway rejected Wi-Fi" };
    }
    return { ok: Boolean(data.ok), error: data.error };
  } catch {
    return { ok: false, unreachable: true };
  }
}
