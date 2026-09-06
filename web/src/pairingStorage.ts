const KEY = "garage.pairing";
export const PAIR_WINDOW_MS = 15 * 60 * 1000;
export const CAPTIVE_RETURN_MS = 15_000;

export type StoredPairing = {
  nonce: string;
  expiresAt: number;
  joinedAp?: boolean;
  pairPressed?: boolean;
  wifiSaved?: boolean;
  awaitingCaptive?: boolean;
  hiddenAt?: number;
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

export function writePairing(pairing: StoredPairing): StoredPairing {
  localStorage.setItem(KEY, JSON.stringify(pairing));
  return pairing;
}

function mergeProgress(current: StoredPairing, patch: Partial<StoredPairing>): StoredPairing {
  const wifiSaved = Boolean(current.wifiSaved || patch.wifiSaved);
  const pairPressed = Boolean(current.pairPressed || patch.pairPressed || wifiSaved);
  const joinedAp = Boolean(current.joinedAp || patch.joinedAp || pairPressed);
  return {
    nonce: patch.nonce ?? current.nonce,
    expiresAt: patch.expiresAt ?? current.expiresAt,
    joinedAp,
    pairPressed,
    wifiSaved,
    awaitingCaptive: wifiSaved ? false : (patch.awaitingCaptive ?? current.awaitingCaptive),
    hiddenAt: wifiSaved ? undefined : (patch.hiddenAt ?? current.hiddenAt),
  };
}

export function patchPairing(patch: Partial<StoredPairing>): StoredPairing | null {
  const current = readPairing();
  if (!current) {
    return null;
  }
  return writePairing(mergeProgress(current, patch));
}

export function saveStartedPairing(input: { nonce?: string; expiresAt?: number }): StoredPairing {
  if (!input.nonce) {
    throw new Error("Pairing did not return a nonce");
  }
  const current = readPairing();
  const serverExpiry = typeof input.expiresAt === "number" ? input.expiresAt : 0;
  const expiresAt = Math.max(serverExpiry, Date.now() + PAIR_WINDOW_MS);
  if (current?.nonce === input.nonce) {
    return writePairing(mergeProgress(current, { expiresAt }));
  }
  return writePairing({
    nonce: input.nonce,
    expiresAt,
  });
}

export function markAwaitingCaptive(): StoredPairing | null {
  return patchPairing({ awaitingCaptive: true });
}

export function markJoinedAp(): StoredPairing | null {
  return patchPairing({ joinedAp: true, awaitingCaptive: true });
}

export function markPairPressed(): StoredPairing | null {
  return patchPairing({ pairPressed: true, joinedAp: true });
}

export function markWifiSaved(): StoredPairing | null {
  return patchPairing({ wifiSaved: true, pairPressed: true, joinedAp: true });
}

export function markSetupHidden(): StoredPairing | null {
  const current = readPairing();
  if (!current || current.wifiSaved || !current.awaitingCaptive) {
    return current;
  }
  return patchPairing({ hiddenAt: Date.now() });
}

export function markLeftSetup(): StoredPairing | null {
  const current = readPairing();
  if (!current || current.wifiSaved) {
    return current;
  }
  return writePairing({
    ...current,
    awaitingCaptive: false,
    hiddenAt: undefined,
  });
}

export function resumeAfterCaptive(input: {
  online: boolean;
  onGateway: boolean;
}): StoredPairing | null {
  const current = readPairing();
  if (!current) {
    return null;
  }
  if (current.wifiSaved) {
    return current;
  }
  if (typeof document !== "undefined" && document.visibilityState === "hidden") {
    return current;
  }
  if (!current.awaitingCaptive || !current.hiddenAt || input.onGateway || !input.online) {
    return current;
  }
  if (Date.now() - current.hiddenAt < CAPTIVE_RETURN_MS) {
    return current;
  }
  return markWifiSaved();
}

export function pairingWifiSaved(): boolean {
  return readPairing()?.wifiSaved === true;
}

export function clearPairing(): void {
  localStorage.removeItem(KEY);
}
