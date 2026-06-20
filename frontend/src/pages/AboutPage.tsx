import { Card } from "../components/Card";
import { APP_NAME, APP_TAGLINE } from "../lib/branding";

const features = [
  "Reverse Proxy Management",
  "SSL Automation",
  "Load Balancing",
  "Automatic Failover",
  "Backend Health Monitoring",
  "SMTP Notifications",
  "NGINX Management",
  "Centralized Administration",
  "Enterprise Security",
];

export function AboutPage() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold">About</h2>
        <p className="text-white/60">{APP_TAGLINE}</p>
      </div>
      <Card title={APP_NAME}>
        <p className="text-lg font-semibold">{APP_NAME}</p>
        <p className="mt-2 text-white/70">{APP_TAGLINE}</p>
        <p className="mt-4 text-sm text-white/50">© In a Cloud</p>
      </Card>
      <Card title="Features">
        <ul className="grid gap-2 md:grid-cols-2">
          {features.map((feature) => (
            <li key={feature} className="rounded-lg bg-white/5 px-3 py-2 text-sm">
              {feature}
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}
