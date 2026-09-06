const KEY = "garage.pairing";

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

export function clearPairing(): void {
  localStorage.removeItem(KEY);
}
