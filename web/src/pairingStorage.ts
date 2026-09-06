const KEY = "garage.pairing";
export const PAIR_WINDOW_MS = 15 * 60 * 1000;

export type StoredPairing = {
  nonce: string;
  expiresAt: number;
};

export function readPairing(): StoredPairing | null {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) {
      return null;
    }
    const data = JSON.parse(raw) as StoredPairing;
    if (!data.nonce || !data.expiresAt || data.expiresAt <= Date.now()) {
      localStorage.removeItem(KEY);
      return null;
    }
    return data;
  } catch {
    return null;
  }
}

export function writePairing(pairing: StoredPairing): void {
  localStorage.setItem(KEY, JSON.stringify(pairing));
}

export function saveStartedPairing(input: { nonce?: string; expiresAt?: number }): StoredPairing {
  if (!input.nonce) {
    throw new Error("Pairing did not return a nonce. Deploy Convex and try again.");
  }
  const serverExpiry = typeof input.expiresAt === "number" ? input.expiresAt : 0;
  const pairing = {
    nonce: input.nonce,
    expiresAt: Math.max(serverExpiry, Date.now() + PAIR_WINDOW_MS),
  };
  writePairing(pairing);
  return pairing;
}

export function clearPairing(): void {
  localStorage.removeItem(KEY);
}
