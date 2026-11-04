import { useState, useEffect, useCallback } from "react";
import PageHeader from "../components/PageHeader";
import {
  Settings as SettingsIcon,
  Shield,
  Eye,
  EyeOff,
  Key,
  Save,
  CheckCircle2,
  AlertCircle,
  Laptop,
  Smartphone,
  Trash2,
  Download,
  ScrollText,
  Database
} from "lucide-react";
import { api, apiService, ApiError } from "../services/api";
import { syncWebSocket } from "../services/websocket";

export default function Settings() {
  const [activeTab, setActiveTab] = useState<"security" | "sessions" | "audit" | "preferences" | "data">("security");
  const [apiKey, setApiKey] = useState<string>("dg_live_2026_987x123abc456def789");
  const [showKey, setShowKey] = useState(false);
  const [tolerance, setTolerance] = useState<number>(80);
  const [version, setVersion] = useState<number>(1);
  const [statusMessage, setStatusMessage] = useState<{ text: string; isError: boolean } | null>(null);
  const [saving, setSaving] = useState(false);

  // Sessions state
  const [sessions, setSessions] = useState<any[]>([]);
  const [loadingSessions, setLoadingSessions] = useState(false);

  // Audit Logs state
  const [auditLogs, setAuditLogs] = useState<any[]>([]);
  const [loadingAudit, setLoadingAudit] = useState(false);

  // Data Export state
  const [isExporting, setIsExporting] = useState(false);

  const fetchSettings = useCallback(async () => {
    try {
      const data = await apiService.getSettings();
      setTolerance(data.sensitivity_tolerance);
      setApiKey(data.api_key);
      setVersion(data.version);
    } catch (err: any) {
      console.error("Failed to load settings from server:", err);
    }
  }, []);

  const fetchSessions = async () => {
    setLoadingSessions(true);
    try {
      const list = await api.getSessions();
      setSessions(list);
    } catch (err: any) {
      console.error("Failed to load sessions:", err);
    } finally {
      setLoadingSessions(false);
    }
  };

  const fetchAuditLogs = async () => {
    setLoadingAudit(true);
    try {
      const logs = await api.getAuditLogs(40, 0);
      setAuditLogs(logs);
    } catch (err: any) {
      console.error("Failed to load audit logs:", err);
    } finally {
      setLoadingAudit(false);
    }
  };

  useEffect(() => {
    fetchSettings();

    const unsub = syncWebSocket.subscribe("settings.updated", (updated) => {
      if (updated) {
        setTolerance(updated.sensitivity_tolerance);
        setApiKey(updated.api_key);
        setVersion(updated.version);
        setStatusMessage({ text: "Settings synchronized from connected client.", isError: false });
      }
    });

    const unsubReconnect = syncWebSocket.onReconnect(() => {
      fetchSettings();
    });

    return () => {
      unsub();
      unsubReconnect();
    };
  }, [fetchSettings]);

  useEffect(() => {
    if (activeTab === "sessions") fetchSessions();
    if (activeTab === "audit") fetchAuditLogs();
  }, [activeTab]);

  const handleToggleKeyVisibility = () => {
    setShowKey((prev) => !prev);
  };

  const handleRevokeKey = async () => {
    setSaving(true);
    setStatusMessage(null);
    try {
      const res = await apiService.updateSettings({
        api_key: "",
        sensitivity_tolerance: tolerance,
        version,
      });
      setApiKey(res.api_key);
      setVersion(res.version);
      setStatusMessage({ text: "API credential revoked successfully.", isError: false });
    } catch (err: any) {
      if (err instanceof ApiError && err.status === 409) {
        setStatusMessage({ text: "Conflict: Settings were updated elsewhere. Reloading latest...", isError: true });
        await fetchSettings();
      } else {
        setStatusMessage({ text: err.message || "Failed to revoke key.", isError: true });
      }
    } finally {
      setSaving(false);
    }
  };

  const handleGenerateKey = async () => {
    const chars = "abcdef0123456789";
    let randomPart = "";
    for (let i = 0; i < 24; i++) {
      randomPart += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    const newKey = `dg_live_2026_${randomPart}`;
    setSaving(true);
    setStatusMessage(null);
    try {
      const res = await apiService.updateSettings({
        api_key: newKey,
        sensitivity_tolerance: tolerance,
        version,
      });
      setApiKey(res.api_key);
      setVersion(res.version);
      setStatusMessage({ text: "Generated new API key successfully.", isError: false });
    } catch (err: any) {
      if (err instanceof ApiError && err.status === 409) {
        setStatusMessage({ text: "Conflict: Settings were updated elsewhere. Reloading latest...", isError: true });
        await fetchSettings();
      } else {
        setStatusMessage({ text: err.message || "Failed to generate key.", isError: true });
      }
    } finally {
      setSaving(false);
    }
  };

  const handleSavePreferences = async () => {
    setSaving(true);
    setStatusMessage(null);
    try {
      const res = await apiService.updateSettings({
        sensitivity_tolerance: tolerance,
        api_key: apiKey,
        version,
      });
      setTolerance(res.sensitivity_tolerance);
      setVersion(res.version);
      setStatusMessage({
        text: `Configuration saved: Sensitivity tolerance set to ${res.sensitivity_tolerance}%.`,
        isError: false,
      });
    } catch (err: any) {
      if (err instanceof ApiError && err.status === 409) {
        setStatusMessage({ text: "Conflict: Settings were updated elsewhere. Reloading latest...", isError: true });
        await fetchSettings();
      } else {
        setStatusMessage({ text: err.message || "Failed to save preferences.", isError: true });
      }
    } finally {
      setSaving(false);
    }
  };

  const handleRevokeSession = async (sessionId: number) => {
    try {
      await api.revokeSession(sessionId);
      await fetchSessions();
      setStatusMessage({ text: "Session revoked successfully.", isError: false });
    } catch (err: any) {
      setStatusMessage({ text: err.message || "Failed to revoke session.", isError: true });
    }
  };

  const handleRevokeOtherSessions = async () => {
    if (!confirm("Revoke all other active sessions across browsers and devices?")) return;
    try {
      const res = await api.revokeOtherSessions();
      await fetchSessions();
      setStatusMessage({ text: res.message, isError: false });
    } catch (err: any) {
      setStatusMessage({ text: err.message || "Failed to revoke sessions.", isError: true });
    }
  };

  const handleExportDataArchive = async () => {
    setIsExporting(true);
    try {
      await api.downloadAccountArchive();
      setStatusMessage({ text: "Account archive downloaded successfully.", isError: false });
    } catch (err: any) {
      setStatusMessage({ text: err.message || "Data export failed.", isError: true });
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Settings & Governance"
        description="Manage API access, active device sessions, security audit trails, and data compliance."
      />

      {statusMessage && (
        <div
          className={`flex items-center gap-2 p-4 rounded-xl text-sm border ${
            statusMessage.isError
              ? "bg-rose-500/10 border-rose-500/20 text-rose-300"
              : "bg-emerald-500/10 border-emerald-500/20 text-emerald-300"
          }`}
        >
          {statusMessage.isError ? <AlertCircle size={16} /> : <CheckCircle2 size={16} />}
          <span>{statusMessage.text}</span>
        </div>
      )}

      <div className="grid gap-6 md:grid-cols-4">
        {/* Left Options Navigation */}
        <div className="rounded-2xl border border-white/10 bg-white/[0.01] p-3 h-fit space-y-1">
          <button
            onClick={() => { setActiveTab("security"); setStatusMessage(null); }}
            className={`w-full text-left rounded-xl px-4 py-2.5 text-xs font-semibold transition ${
              activeTab === "security" ? "bg-violet-600 text-white" : "text-slate-400 hover:bg-white/5 hover:text-white"
            }`}
          >
            Security & API Keys
          </button>
          <button
            onClick={() => { setActiveTab("sessions"); setStatusMessage(null); }}
            className={`w-full text-left rounded-xl px-4 py-2.5 text-xs font-semibold transition ${
              activeTab === "sessions" ? "bg-violet-600 text-white" : "text-slate-400 hover:bg-white/5 hover:text-white"
            }`}
          >
            Active Sessions & Devices
          </button>
          <button
            onClick={() => { setActiveTab("audit"); setStatusMessage(null); }}
            className={`w-full text-left rounded-xl px-4 py-2.5 text-xs font-semibold transition ${
              activeTab === "audit" ? "bg-violet-600 text-white" : "text-slate-400 hover:bg-white/5 hover:text-white"
            }`}
          >
            Security Audit Logs
          </button>
          <button
            onClick={() => { setActiveTab("preferences"); setStatusMessage(null); }}
            className={`w-full text-left rounded-xl px-4 py-2.5 text-xs font-semibold transition ${
              activeTab === "preferences" ? "bg-violet-600 text-white" : "text-slate-400 hover:bg-white/5 hover:text-white"
            }`}
          >
            Detection Thresholds
          </button>
          <button
            onClick={() => { setActiveTab("data"); setStatusMessage(null); }}
            className={`w-full text-left rounded-xl px-4 py-2.5 text-xs font-semibold transition ${
              activeTab === "data" ? "bg-violet-600 text-white" : "text-slate-400 hover:bg-white/5 hover:text-white"
            }`}
          >
            Data & Privacy Archive
          </button>
        </div>

        {/* Right Settings Configuration Details */}
        <div className="md:col-span-3 space-y-6">
          {/* 1. Security & Keys */}
          {activeTab === "security" && (
            <div className="rounded-2xl border border-white/10 bg-slate-900/60 p-6 space-y-6">
              <h3 className="text-base font-semibold text-white flex items-center gap-2">
                <Shield size={18} className="text-violet-400" />
                API Credentials
              </h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                Generate and manage API keys to authenticate code integrations and remote scanning tools with DeepGuard's backend classification models.
              </p>

              <div className="space-y-4">
                <div>
                  <label className="mb-2 block text-xs font-bold uppercase tracking-wider text-slate-400">
                    Active API Key
                  </label>
                  <div className="flex gap-3">
                    <div className="relative flex-1">
                      <Key size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                      <input
                        type={showKey ? "text" : "password"}
                        value={apiKey || "No active key generated"}
                        disabled
                        className="w-full rounded-xl border border-white/10 bg-slate-950 px-9 py-2.5 text-xs text-slate-300 outline-none cursor-not-allowed font-mono"
                      />
                      {apiKey && (
                        <button
                          type="button"
                          onClick={handleToggleKeyVisibility}
                          className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 transition"
                          title={showKey ? "Hide API key" : "Show API key"}
                        >
                          {showKey ? <EyeOff size={16} /> : <Eye size={16} />}
                        </button>
                      )}
                    </div>
                    {apiKey && (
                      <button
                        onClick={handleRevokeKey}
                        disabled={saving}
                        className="rounded-xl border border-rose-500/20 bg-rose-500/5 px-4 py-2 text-xs font-semibold text-rose-400 hover:bg-rose-500/10 transition disabled:opacity-50"
                      >
                        {saving ? "Updating..." : "Revoke"}
                      </button>
                    )}
                  </div>
                </div>

                <button
                  onClick={handleGenerateKey}
                  disabled={saving}
                  className="rounded-xl bg-violet-600 px-4 py-2 text-xs font-semibold hover:bg-violet-500 transition text-white disabled:opacity-50"
                >
                  {saving ? "Generating..." : apiKey ? "Generate New Secret Key" : "Generate API Key"}
                </button>
              </div>
            </div>
          )}

          {/* 2. Active Sessions & Devices */}
          {activeTab === "sessions" && (
            <div className="rounded-2xl border border-white/10 bg-slate-900/60 p-6 space-y-6">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-base font-semibold text-white flex items-center gap-2">
                    <Laptop size={18} className="text-violet-400" />
                    Active Device Sessions
                  </h3>
                  <p className="text-xs text-slate-400 mt-1">
                    Manage all web browsers and mobile devices currently signed in to your DeepGuard account.
                  </p>
                </div>
                {sessions.length > 1 && (
                  <button
                    onClick={handleRevokeOtherSessions}
                    className="inline-flex items-center gap-1.5 rounded-xl border border-rose-500/20 bg-rose-500/10 px-3.5 py-1.5 text-xs font-semibold text-rose-400 hover:bg-rose-500/20 transition"
                  >
                    <Trash2 size={13} /> Revoke Other Sessions
                  </button>
                )}
              </div>

              {loadingSessions ? (
                <div className="flex justify-center py-12">
                  <div className="h-6 w-6 animate-spin rounded-full border-2 border-violet-500 border-t-transparent" />
                </div>
              ) : (
                <div className="space-y-3">
                  {sessions.map((sess) => {
                    const isMobile = sess.platform === "Android" || sess.platform === "iOS";
                    return (
                      <div
                        key={sess.id}
                        className="flex items-center justify-between p-4 rounded-xl border border-white/10 bg-slate-950/80"
                      >
                        <div className="flex items-center gap-3.5">
                          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-violet-600/20 text-violet-400">
                            {isMobile ? <Smartphone size={20} /> : <Laptop size={20} />}
                          </div>
                          <div>
                            <div className="flex items-center gap-2">
                              <span className="text-xs font-bold text-white">{sess.device_name}</span>
                              {sess.is_current && (
                                <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                                  Current Device
                                </span>
                              )}
                            </div>
                            <p className="text-[11px] text-slate-400 mt-0.5">
                              IP: {sess.ip_address} • Last active: {new Date(sess.last_active_at).toLocaleString()}
                            </p>
                          </div>
                        </div>

                        {!sess.is_current && (
                          <button
                            onClick={() => handleRevokeSession(sess.id)}
                            className="rounded-lg border border-white/10 px-3 py-1.5 text-xs text-rose-400 hover:bg-rose-500/10 transition"
                          >
                            Sign Out
                          </button>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {/* 3. Security Audit Logs */}
          {activeTab === "audit" && (
            <div className="rounded-2xl border border-white/10 bg-slate-900/60 p-6 space-y-4">
              <div>
                <h3 className="text-base font-semibold text-white flex items-center gap-2">
                  <ScrollText size={18} className="text-violet-400" />
                  Security & Access Audit Trail
                </h3>
                <p className="text-xs text-slate-400 mt-1">
                  Chronological record of sensitive actions, authentication events, and data governance operations.
                </p>
              </div>

              {loadingAudit ? (
                <div className="flex justify-center py-12">
                  <div className="h-6 w-6 animate-spin rounded-full border-2 border-violet-500 border-t-transparent" />
                </div>
              ) : auditLogs.length === 0 ? (
                <p className="text-xs text-slate-500 text-center py-8">No security events logged yet.</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead>
                      <tr className="border-b border-white/10 text-slate-400 font-semibold">
                        <th className="pb-2.5">Event</th>
                        <th className="pb-2.5">Status</th>
                        <th className="pb-2.5">Details</th>
                        <th className="pb-2.5">IP Address</th>
                        <th className="pb-2.5">Timestamp</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5">
                      {auditLogs.map((log) => (
                        <tr key={log.id} className="text-slate-300">
                          <td className="py-2.5 font-mono text-violet-300">{log.action}</td>
                          <td className="py-2.5">
                            <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-emerald-500/20 text-emerald-400">
                              {log.status}
                            </span>
                          </td>
                          <td className="py-2.5 text-slate-400 max-w-xs truncate">{log.details || "-"}</td>
                          <td className="py-2.5 font-mono text-slate-400">{log.ip_address || "127.0.0.1"}</td>
                          <td className="py-2.5 text-slate-500">{new Date(log.created_at).toLocaleString()}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {/* 4. Detection Thresholds */}
          {activeTab === "preferences" && (
            <div className="rounded-2xl border border-white/10 bg-slate-900/60 p-6 space-y-6">
              <h3 className="text-base font-semibold text-white flex items-center gap-2">
                <SettingsIcon size={18} className="text-violet-400" />
                Detection Thresholds & Model Sensitivity
              </h3>
              
              <div className="space-y-4">
                <div>
                  <div className="flex justify-between items-center mb-2">
                    <label className="block text-xs font-medium text-slate-300">Deepfake Sensitivity Tolerance</label>
                    <span className="text-xs font-semibold text-violet-400">{tolerance}%</span>
                  </div>
                  <input
                    type="range"
                    min="10"
                    max="99"
                    value={tolerance}
                    onChange={(e) => setTolerance(Number(e.target.value))}
                    className="w-full accent-violet-600 cursor-pointer"
                  />
                  <div className="flex justify-between text-[11px] text-slate-500 mt-1">
                    <span>Lenient (Low False Positives)</span>
                    <span>Strict ({tolerance}% Confidence Filter)</span>
                  </div>
                </div>

                <div className="pt-4 border-t border-white/5 flex justify-end">
                  <button
                    onClick={handleSavePreferences}
                    disabled={saving}
                    className="flex items-center gap-2 rounded-xl bg-violet-600 px-4 py-2 text-xs font-semibold hover:bg-violet-500 transition text-white disabled:opacity-50"
                  >
                    <Save size={14} />
                    {saving ? "Saving..." : "Save Configurations"}
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* 5. Data & Privacy Archive */}
          {activeTab === "data" && (
            <div className="rounded-2xl border border-white/10 bg-slate-900/60 p-6 space-y-6">
              <div>
                <h3 className="text-base font-semibold text-white flex items-center gap-2">
                  <Database size={18} className="text-violet-400" />
                  Account Data Archive & Retention
                </h3>
                <p className="text-xs text-slate-400 mt-1 leading-relaxed">
                  Download a full export of your personal profile, scan analyses, forensic findings, investigation cases, and security audit events in a compliant JSON archive.
                </p>
              </div>

              <div className="p-4 rounded-xl border border-white/10 bg-slate-950/80 space-y-3">
                <div className="flex items-center justify-between">
                  <div>
                    <h4 className="text-xs font-bold text-white">Export Full Account Archive (GDPR Compliant)</h4>
                    <p className="text-[11px] text-slate-400 mt-0.5">
                      Contains all scan history, model predictions, forensic indicators, investigation notes, and audit logs.
                    </p>
                  </div>
                  <button
                    onClick={handleExportDataArchive}
                    disabled={isExporting}
                    className="inline-flex items-center gap-1.5 rounded-xl bg-violet-600 px-4 py-2 text-xs font-semibold text-white hover:bg-violet-500 transition disabled:opacity-50"
                  >
                    <Download size={14} /> {isExporting ? "Archiving..." : "Download JSON Archive"}
                  </button>
                </div>
              </div>

              <div className="p-4 rounded-xl border border-white/10 bg-slate-950/80 space-y-3">
                <div>
                  <h4 className="text-xs font-bold text-white">Media Retention Policy</h4>
                  <p className="text-[11px] text-slate-400 mt-0.5">
                    Configure automated cleanup schedules for uploaded media artifacts.
                  </p>
                </div>
                <select className="w-full max-w-xs rounded-xl bg-slate-900 border border-white/15 px-3 py-2 text-xs text-white focus:outline-none focus:border-violet-500">
                  <option value="indefinite">Retain until manually deleted (Default)</option>
                  <option value="90days">Auto-purge after 90 days</option>
                  <option value="30days">Auto-purge after 30 days</option>
                </select>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
