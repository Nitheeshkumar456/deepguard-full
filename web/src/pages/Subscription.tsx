import { useState, useEffect } from "react";
import PageHeader from "../components/PageHeader";
import { Check, ShieldCheck, Zap, X, CheckCircle2 } from "lucide-react";
import { apiService } from "../services/api";

const plans = [
  {
    id: "free",
    name: "Developer Sandbox",
    price: "Free",
    description: "Ideal for workspace configuration and initial integration tests.",
    features: [
      "10 multimodal scans/month",
      "Standard model inference models",
      "Developer community support",
      "1 active API integration key",
    ],
  },
  {
    id: "pro",
    name: "DeepGuard Pro",
    price: "$49",
    period: "/mo",
    description: "For security auditors and independent investigators requiring detailed analysis.",
    features: [
      "Unlimited image scans",
      "500 minutes video/audio processing",
      "Experimental custom model selectors",
      "Priority email support",
      "5 active API integration keys",
    ],
  },
  {
    id: "enterprise",
    name: "Enterprise Threat Intelligence",
    price: "Custom",
    description: "Complete compliance, data governance, and high-performance dedicated resources.",
    features: [
      "Unlimited multimodal processing",
      "Dedicated GPU computing nodes",
      "SLA guarantee support (24/7)",
      "Infinite API credentials",
      "On-premise AI model weights deployment",
    ],
  },
];

export default function Subscription() {
  const [subData, setSubData] = useState<{
    tier: string;
    status: string;
    used_analyses: number;
    total_analyses: number;
  }>({
    tier: "free",
    status: "active",
    used_analyses: 0,
    total_analyses: 10,
  });
  const [selectedPlan, setSelectedPlan] = useState<string | null>(null);
  const [upgradeSuccess, setUpgradeSuccess] = useState<string | null>(null);

  useEffect(() => {
    async function loadSub() {
      try {
        const data = await apiService.getSubscription();
        if (data) {
          setSubData(data);
        }
      } catch (err) {
        console.error("Failed to load subscription info:", err);
      }
    }
    loadSub();
  }, []);

  const used = subData.used_analyses;
  const total = subData.total_analyses;
  const remaining = Math.max(0, total - used);
  const usagePercentage = Math.min(100, Math.round((used / total) * 100));

  const handleConfirmUpgrade = (planName: string) => {
    setSelectedPlan(null);
    setUpgradeSuccess(`Your subscription upgrade request for ${planName} has been received.`);
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Subscription Plan"
        description="Monitor your active deepfake processing usage, limits, and view pricing upgrades."
      />

      {upgradeSuccess && (
        <div className="flex items-center justify-between rounded-2xl border border-emerald-500/20 bg-emerald-500/10 p-4 text-emerald-300 text-sm">
          <div className="flex items-center gap-2">
            <CheckCircle2 size={18} />
            <span>{upgradeSuccess}</span>
          </div>
          <button onClick={() => setUpgradeSuccess(null)} className="text-emerald-400 hover:text-white">
            <X size={16} />
          </button>
        </div>
      )}

      {/* Usage card */}
      <div className="rounded-2xl border border-white/10 bg-white/[0.01] p-6 space-y-4">
        <h3 className="text-lg font-semibold text-white">Monthly Quota Consumption</h3>
        <div>
          <div className="flex justify-between text-sm text-slate-400 mb-2">
            <span>
              {subData.tier === "free" ? "Free Analyses" : "Pro Analyses"}: {remaining} of {total} remaining
            </span>
            <span>{100 - usagePercentage}% Remaining</span>
          </div>
          <div className="h-2.5 w-full rounded-full bg-slate-900 overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-500 ${
                usagePercentage >= 90
                  ? "bg-rose-500"
                  : usagePercentage >= 70
                  ? "bg-amber-500"
                  : "bg-violet-600"
              }`}
              style={{ width: `${Math.max(5, usagePercentage)}%` }}
            />
          </div>
        </div>
      </div>

      {/* Pricing options grid */}
      <div className="grid gap-6 md:grid-cols-3">
        {plans.map((plan) => {
          const isCurrent = subData.tier === plan.id;
          return (
            <div
              key={plan.name}
              className={`rounded-2xl border p-6 flex flex-col justify-between transition-all duration-300 ${
                isCurrent
                  ? "border-violet-500 bg-violet-500/[0.02] ring-1 ring-violet-500/20"
                  : "border-white/10 bg-white/[0.01] hover:border-white/20"
              }`}
            >
              <div className="space-y-4">
                <div>
                  <h4 className="text-lg font-bold text-white">{plan.name}</h4>
                  <p className="mt-2 text-xs text-slate-500 leading-normal">{plan.description}</p>
                </div>

                <div className="flex items-baseline text-white">
                  <span className="text-3xl font-extrabold tracking-tight">{plan.price}</span>
                  {plan.period && <span className="ml-1 text-sm font-semibold text-slate-400">{plan.period}</span>}
                </div>

                <ul className="space-y-3 pt-4 border-t border-white/5 text-xs text-slate-300">
                  {plan.features.map((feature) => (
                    <li key={feature} className="flex items-start gap-2">
                      <Check size={14} className="text-violet-400 shrink-0 mt-0.5" />
                      <span>{feature}</span>
                    </li>
                  ))}
                </ul>
              </div>

              <div className="mt-6">
                {isCurrent ? (
                  <button
                    disabled
                    className="flex w-full items-center justify-center gap-2 rounded-xl border border-violet-500/30 bg-violet-500/10 py-3 font-semibold text-violet-400 text-sm cursor-not-allowed"
                  >
                    <ShieldCheck size={16} />
                    Active Plan
                  </button>
                ) : (
                  <button
                    onClick={() => setSelectedPlan(plan.name)}
                    className="flex w-full items-center justify-center gap-2 rounded-xl bg-violet-600 py-3 font-semibold hover:bg-violet-500 transition text-sm text-white"
                  >
                    <Zap size={16} />
                    Upgrade License
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Upgrade Confirmation Modal */}
      {selectedPlan && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-2xl border border-white/10 bg-slate-900 p-6 shadow-2xl animate-in zoom-in-95 duration-200">
            <div className="flex items-center justify-between pb-3 border-b border-white/10">
              <h3 className="text-lg font-bold text-white">Confirm Upgrade</h3>
              <button
                onClick={() => setSelectedPlan(null)}
                className="text-slate-400 hover:text-white transition"
              >
                <X size={18} />
              </button>
            </div>
            <p className="mt-4 text-sm text-slate-300 leading-relaxed">
              Upgrade your current subscription to <strong className="text-violet-400">{selectedPlan}</strong>? You will immediately gain access to higher concurrency quotas and custom model weights.
            </p>
            <div className="mt-6 flex gap-3 justify-end">
              <button
                onClick={() => setSelectedPlan(null)}
                className="rounded-xl border border-white/10 px-4 py-2 text-sm font-semibold text-slate-400 hover:bg-white/5 transition"
              >
                Cancel
              </button>
              <button
                onClick={() => handleConfirmUpgrade(selectedPlan)}
                className="rounded-xl bg-violet-600 px-5 py-2 text-sm font-semibold text-white hover:bg-violet-500 transition"
              >
                Confirm Upgrade
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
