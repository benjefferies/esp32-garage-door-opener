export const APP_CACHE = "garage-app-v2";

export async function precacheAppShell(): Promise<void> {
  if (!("caches" in window)) {
    return;
  }
  const cache = await caches.open(APP_CACHE);
  const assets = new Set<string>([
    "/",
    "/index.html",
    "/manifest.webmanifest",
    window.location.pathname || "/",
  ]);
  for (const el of document.querySelectorAll("script[src]")) {
    assets.add((el as HTMLScriptElement).src);
  }
  for (const el of document.querySelectorAll("link[rel='stylesheet']")) {
    assets.add((el as HTMLLinkElement).href);
  }
  await Promise.all(
    [...assets].map((url) => cache.add(url).catch(() => undefined)),
  );
}
