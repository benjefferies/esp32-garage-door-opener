export function parseSetupHash(hash = window.location.hash) {
  const raw = hash.replace(/^#/, "");
  const [path, query = ""] = raw.split("?");
  const params = new URLSearchParams(query);
  return {
    isSetup: path === "setup",
    wifiSaved: params.get("saved") === "1",
  };
}
