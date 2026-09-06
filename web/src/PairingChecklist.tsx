import { GATEWAY_AP_SSID } from "./gatewayApi";

type Props = {
  ready: boolean;
  joinedAp: boolean;
  pairPressed: boolean;
  wifiSaved: boolean;
  online: boolean | null;
};

export function PairingChecklist({
  ready,
  joinedAp,
  pairPressed,
  wifiSaved,
  online,
}: Props) {
  const steps = [
    { done: ready, label: "Ready to start pairing" },
    { done: joinedAp || wifiSaved, label: `Connect to WiFi called ${GATEWAY_AP_SSID}` },
    { done: pairPressed || wifiSaved, label: "Press pair button" },
    { done: wifiSaved, label: "Setup WiFi on gateway" },
    { done: wifiSaved && online === true, label: "Back online" },
  ];
  const currentIndex = steps.findIndex((step) => !step.done);

  return (
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
  );
}
