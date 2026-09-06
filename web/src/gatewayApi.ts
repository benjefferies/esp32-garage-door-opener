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

export async function fetchGatewayStatus(nonce?: string | null): Promise<GatewayStatus | null> {
  try {
    const url = new URL("/api/status", GATEWAY_ORIGIN);
    if (nonce) {
      url.searchParams.set("n", nonce);
    }
    const response = await fetch(url, {
      mode: "cors",
      cache: "no-store",
    });
    if (!response.ok) {
      return null;
    }
    return (await response.json()) as GatewayStatus;
  } catch {
    return null;
  }
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
