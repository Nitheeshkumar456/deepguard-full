import { useState, useEffect, useCallback, useMemo } from "react";
import PageHeader from "../components/PageHeader";
import StatCard from "../components/StatCard";
import { EmptyState, LoadingState, ErrorState } from "../components/FeedbackStates";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from "recharts";
import {
  ShieldAlert,
  CheckCircle2,
  AlertTriangle,
  Play,
  Activity,
  FileText,
  UserCheck,
  FileImage,
  FileVideo,
  FileAudio,
  ArrowRight,
  RefreshCw,
  User,
} from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { apiService, ApiError } from "../services/api";
import { useAuth } from "../context/AuthContext";
import { syncWebSocket } from "../services/websocket";

interface AnalysisItem {
  id: number;
  media_type: "image" | "video" | "audio";
  original_filename: string;
  file_size?: number | null;
  status: "queued" | "processing" | "completed" | "failed";
  created_at: string;
  completed_at?: string | null;
  processing_time?: number | null;
  prediction?: "authentic" | "synthetic" | "uncertain" | null;
  confidence?: number | null;
  risk_level?: "low" | "medium" | "high" | "critical" | null;
}

export default function Dashboard() {
  const navigate = useNavigate();
  const { user, refreshProfile } = useAuth();
  const [analyses, setAnalyses] = useState<AnalysisItem[]>([]);
  const [totalAnalyses, setTotalAnalyses] = useState(0);
  const [loading, setLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchDashboardData = useCallback(async (isManualRefresh = false) => {
    if (isManualRefresh) {
      setIsRefreshing(true);
    } else {
      setLoading(true);
    }
    setError(null);
    try {
      // Fetch user analysis history from real backend API
      const historyData = await apiService.getAnalysisHistory({
        page: 1,
        page_size: 50,
      });

      setAnalyses(historyData.items || []);
      setTotalAnalyses(historyData.total || (historyData.items ? historyData.items.length : 0));
    } catch (err: any) {
      console.error("Dashboard data fetch failed:", err);
      if (err instanceof ApiError && err.status === 401) {
        // Attempt session recovery
        try {
          await refreshProfile();
          const retryData = await apiService.getAnalysisHistory({ page: 1, page_size: 50 });
          setAnalyses(retryData.items || []);
          setTotalAnalyses(retryData.total || (retryData.items ? retryData.items.length : 0));
          return;
        } catch (authErr) {
          setError("Your session has expired. Please log in again.");
          return;
        }
      }
      setError(err?.message || "Failed to connect to DeepGuard services. Please try again.");
    } finally {
      setLoading(false);
      setIsRefreshing(false);
    }
  }, [refreshProfile]);

  useEffect(() => {
    fetchDashboardData(false);

    // Subscribe to bidirectional synchronization events
    const unsubUpload = syncWebSocket.subscribe("media.uploaded", (item) => {
      if (item && item.id) {
        setAnalyses((prev) => {
          if (prev.some((a) => a.id === item.id)) return prev;
          return [item, ...prev];
        });
        setTotalAnalyses((t) => t + 1);
      }
    });

    const unsubComplete = syncWebSocket.subscribe("analysis.completed", (detail) => {
      if (detail && detail.id) {
        setAnalyses((prev) =>
          prev.map((a) =>
            a.id === detail.id
              ? {
                  ...a,
                  status: "completed",
                  prediction: detail.result?.prediction || a.prediction,
                  confidence: detail.result?.confidence || a.confidence,
                  risk_level: detail.result?.risk_level || a.risk_level,
                  processing_time: detail.processing_time,
                  completed_at: detail.completed_at,
                }
              : a
          )
        );
      }
    });

    const unsubFailed = syncWebSocket.subscribe("analysis.failed", (failData) => {
      if (failData && failData.analysis_id) {
        setAnalyses((prev) =>
          prev.map((a) =>
            a.id === failData.analysis_id ? { ...a, status: "failed" } : a
          )
        );
      }
    });

    const unsubDelete = syncWebSocket.subscribe("media.deleted", (delData) => {
      if (delData && delData.analysis_id) {
        setAnalyses((prev) => prev.filter((a) => a.id !== delData.analysis_id));
        setTotalAnalyses((t) => Math.max(0, t - 1));
      }
    });

    const unsubReconnect = syncWebSocket.onReconnect(() => {
      fetchDashboardData(false);
    });

    return () => {
      unsubUpload();
      unsubComplete();
      unsubFailed();
      unsubDelete();
      unsubReconnect();
    };
  }, [fetchDashboardData]);

  // Derived statistics computed from real backend data
  const stats = useMemo(() => {
    const total = totalAnalyses;
    let authenticCount = 0;
    let syntheticCount = 0;
    let otherCount = 0;

    analyses.forEach((item) => {
      if (item.prediction === "authentic") {
        authenticCount++;
      } else if (item.prediction === "synthetic") {
        syntheticCount++;
      } else {
        otherCount++;
      }
    });

    return {
      total,
      authenticCount,
      syntheticCount,
      otherCount,
    };
  }, [analyses, totalAnalyses]);

  // Dynamic Pie Chart Data from actual analyses
  const riskDistributionData = useMemo(() => {
    return [
      { name: "Authentic / Real", value: stats.authenticCount, color: "#10b981" },
      { name: "AI / Synthetic", value: stats.syntheticCount, color: "#ef4444" },
      { name: "Uncertain / Other", value: stats.otherCount, color: "#f59e0b" },
    ];
  }, [stats]);

  // Dynamic Scan Activity Chart (grouped chronologically by date of analysis)
  const activityData = useMemo(() => {
    if (analyses.length === 0) {
      return [];
    }

    // Sort ascending by created_at date so graph displays chronologically from past to present
    const sorted = [...analyses].sort(
      (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
    );

    const dateMap: { [key: string]: { analyses: number; synthetic: number } } = {};

    // Group items by localized date string
    sorted.forEach((item) => {
      const dateStr = new Date(item.created_at).toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
      });
      if (!dateMap[dateStr]) {
        dateMap[dateStr] = { analyses: 0, synthetic: 0 };
      }
      dateMap[dateStr].analyses += 1;
      if (item.prediction === "synthetic") {
        dateMap[dateStr].synthetic += 1;
      }
    });

    return Object.keys(dateMap).map((date) => ({
      date,
      analyses: dateMap[date].analyses,
      synthetic: dateMap[date].synthetic,
    }));
  }, [analyses]);

  // Recent scans (up to 5 items)
  const recentScans = useMemo(() => {
    return analyses.slice(0, 5);
  }, [analyses]);

  if (loading && !isRefreshing) {
    return (
      <div className="space-y-8">
        <PageHeader
          title="Dashboard"
          description="Real-time authenticity monitoring and AI-powered media classification."
        />
        <LoadingState message="Fetching live analysis metrics and scan activity..." />
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-8">
        <PageHeader
          title="Dashboard"
          description="Real-time authenticity monitoring and AI-powered media classification."
        />
        <ErrorState
          title="Unable to load dashboard"
          description={error}
          actionLabel="Retry Connection"
          onAction={() => fetchDashboardData(false)}
        />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Console Header */}
      <PageHeader
        title="Dashboard"
        description={
          user
            ? `Welcome back, ${user.name || user.email}. Live authenticity monitoring and activity summaries.`
            : "Real-time authenticity monitoring, deepfake detection summaries, and system activity."
        }
        action={
          <div className="flex items-center gap-3">
            <button
              onClick={() => fetchDashboardData(true)}
              disabled={loading || isRefreshing}
              className="flex items-center gap-2 rounded-xl border border-white/10 bg-slate-900 px-4 py-2.5 text-sm font-semibold text-slate-300 hover:bg-white/5 transition disabled:opacity-50"
              title="Refresh live metrics"
            >
              <RefreshCw size={15} className={isRefreshing ? "animate-spin" : ""} />
              {isRefreshing ? "Refreshing..." : "Refresh"}
            </button>
            <Link
              to="/analyze"
              className="flex items-center gap-2 rounded-xl bg-violet-600 px-5 py-2.5 text-sm font-semibold hover:bg-violet-500 transition shadow-lg shadow-violet-600/10 text-white"
            >
              <Play size={16} fill="currentColor" />
              Analyze New Media
            </Link>
          </div>
        }
      />

      {/* User Information Banner */}
      {user && (
        <div className="flex items-center justify-between rounded-2xl border border-white/10 bg-white/[0.02] p-5">
          <div className="flex items-center gap-3.5">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-violet-600/10 border border-violet-500/20 text-violet-400">
              <User size={22} />
            </div>
            <div>
              <h4 className="font-semibold text-white text-sm flex items-center gap-2">
                {user.name || "Authenticated User"}
                {user.is_verified && (
                  <span className="rounded-full bg-emerald-500/10 px-2 py-0.5 text-[10px] font-semibold text-emerald-400 border border-emerald-500/20">
                    Verified
                  </span>
                )}
              </h4>
              <p className="text-xs text-slate-400 mt-0.5">{user.email}</p>
            </div>
          </div>
          <div className="hidden sm:flex items-center gap-3">
            <Link
              to="/profile"
              className="text-xs font-semibold text-violet-400 hover:text-violet-300 transition"
            >
              View Profile →
            </Link>
          </div>
        </div>
      )}

      {/* 4 Stat Cards based on real backend data */}
      <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Total Analyses"
          value={stats.total}
          description="Total media files evaluated"
          icon={<FileText size={20} />}
          status="default"
          onClick={() => navigate("/history")}
        />
        <StatCard
          title="Real / Authentic"
          value={stats.authenticCount}
          description="Verified authentic media"
          icon={<CheckCircle2 size={20} />}
          status="success"
          onClick={() => navigate("/history?verdict=authentic")}
        />
        <StatCard
          title="AI / Synthetic"
          value={stats.syntheticCount}
          description="Deepfakes & synthetic media"
          icon={<ShieldAlert size={20} />}
          status="error"
          onClick={() => navigate("/history?verdict=synthetic")}
        />
        <StatCard
          title="Uncertain / Other"
          value={stats.otherCount}
          description="Pending, failed or uncertain"
          icon={<AlertTriangle size={20} />}
          status="warning"
          onClick={() => navigate("/history?verdict=uncertain")}
        />
      </div>

      {/* Visualizations Grid */}
      {stats.total > 0 ? (
        <div className="grid gap-6 lg:grid-cols-3">
          {/* Line Chart: Scans over time */}
          <div className="lg:col-span-2 rounded-2xl border border-white/10 bg-white/[0.01] p-6 flex flex-col justify-between">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h3 className="text-lg font-bold text-white flex items-center gap-2">
                  <Activity size={18} className="text-violet-400" />
                  Scan Activity
                </h3>
                <p className="text-xs text-slate-500 mt-1">Processed media volume by date</p>
              </div>
              <span className="text-xs font-semibold text-slate-400 rounded-lg bg-slate-900 border border-white/5 px-2.5 py-1">
                Recent Scans
              </span>
            </div>

            <div className="h-72 w-full">
              {activityData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={activityData} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}>
                    <defs>
                      <linearGradient id="colorAnalyses" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.2} />
                        <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0} />
                      </linearGradient>
                      <linearGradient id="colorSynthetic" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#ef4444" stopOpacity={0.2} />
                        <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <XAxis dataKey="date" stroke="#475569" fontSize={11} tickLine={false} axisLine={false} />
                    <YAxis stroke="#475569" fontSize={11} tickLine={false} axisLine={false} allowDecimals={false} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "#0f172a",
                        border: "1px solid rgba(255,255,255,0.1)",
                        borderRadius: "12px",
                        color: "#fff",
                        fontSize: "12px",
                      }}
                    />
                    <Area
                      type="monotone"
                      dataKey="analyses"
                      name="Total Scans"
                      stroke="#8b5cf6"
                      strokeWidth={2}
                      fillOpacity={1}
                      fill="url(#colorAnalyses)"
                    />
                    <Area
                      type="monotone"
                      dataKey="synthetic"
                      name="AI Detected"
                      stroke="#ef4444"
                      strokeWidth={2}
                      fillOpacity={1}
                      fill="url(#colorSynthetic)"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex h-full items-center justify-center text-slate-500 text-xs">
                  No scan timeline data available
                </div>
              )}
            </div>
          </div>

          {/* Pie Chart: Risk Distribution */}
          <div className="rounded-2xl border border-white/10 bg-white/[0.01] p-6 flex flex-col justify-between">
            <div>
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <UserCheck size={18} className="text-violet-400" />
                Risk Distribution
              </h3>
              <p className="text-xs text-slate-500 mt-1">Classification summary breakdown</p>
            </div>

            <div className="h-60 w-full relative flex items-center justify-center my-3">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={riskDistributionData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={80}
                    paddingAngle={5}
                    dataKey="value"
                  >
                    {riskDistributionData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#0f172a",
                      border: "1px solid rgba(255,255,255,0.1)",
                      borderRadius: "12px",
                      color: "#fff",
                      fontSize: "12px",
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
              <div className="absolute text-center pointer-events-none">
                <span className="block text-2xl font-bold text-white">{stats.total}</span>
                <span className="text-[10px] text-slate-500 font-semibold uppercase tracking-wider">
                  Scans Run
                </span>
              </div>
            </div>

            {/* Custom Legends list */}
            <div className="space-y-2 text-xs">
              {riskDistributionData.map((item) => (
                <div key={item.name} className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="h-2 w-2 rounded-full" style={{ backgroundColor: item.color }} />
                    <span className="text-slate-400">{item.name}</span>
                  </div>
                  <span className="font-semibold text-white">{item.value} scans</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      ) : null}

      {/* Recent Analyses list / Table */}
      <div className="rounded-2xl border border-white/10 bg-white/[0.01] overflow-hidden">
        <div className="flex items-center justify-between border-b border-white/10 bg-slate-950/20 px-6 py-4">
          <h3 className="font-semibold text-white text-base">Recent Media Scans</h3>
          <Link to="/history" className="text-xs font-semibold text-violet-400 hover:text-violet-300 transition">
            View All History →
          </Link>
        </div>

        {recentScans.length === 0 ? (
          <div className="p-8">
            <EmptyState
              title="No media analyses found"
              description="You have not submitted any images, videos, or audio recordings for deepfake evaluation yet."
              actionLabel="Analyze First Media"
              onAction={() => navigate("/analyze")}
            />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-left text-sm">
              <thead className="border-b border-white/5 bg-slate-950/40 text-slate-400 font-semibold uppercase tracking-wider text-[11px]">
                <tr>
                  <th className="px-6 py-3.5">Scan ID</th>
                  <th className="px-6 py-3.5">File Name</th>
                  <th className="px-6 py-3.5">Type</th>
                  <th className="px-6 py-3.5">Result</th>
                  <th className="px-6 py-3.5">Confidence</th>
                  <th className="px-6 py-3.5">Date</th>
                  <th className="px-6 py-3.5 text-right">Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5 text-slate-300">
                {recentScans.map((scan) => (
                  <tr key={scan.id} className="hover:bg-white/[0.02] transition">
                    <td className="px-6 py-3.5 font-mono text-xs text-violet-400 font-semibold">
                      #{scan.id}
                    </td>
                    <td className="px-6 py-3.5 font-medium text-white truncate max-w-xs">
                      {scan.original_filename}
                    </td>
                    <td className="px-6 py-3.5 text-slate-400 text-xs">
                      <span className="flex items-center gap-1.5 capitalize">
                        {scan.media_type === "image" && <FileImage size={14} className="text-slate-500" />}
                        {scan.media_type === "video" && <FileVideo size={14} className="text-slate-500" />}
                        {scan.media_type === "audio" && <FileAudio size={14} className="text-slate-500" />}
                        {scan.media_type}
                      </span>
                    </td>
                    <td className="px-6 py-3.5">
                      {scan.status === "completed" ? (
                        <>
                          {scan.prediction === "authentic" && (
                            <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-500/10 px-2.5 py-0.5 text-xs font-semibold text-emerald-400 border border-emerald-500/20">
                              <CheckCircle2 size={12} />
                              Authentic
                            </span>
                          )}
                          {scan.prediction === "synthetic" && (
                            <span className="inline-flex items-center gap-1.5 rounded-full bg-rose-500/10 px-2.5 py-0.5 text-xs font-semibold text-rose-400 border border-rose-500/20">
                              <ShieldAlert size={12} />
                              Synthetic
                            </span>
                          )}
                          {scan.prediction === "uncertain" && (
                            <span className="inline-flex items-center gap-1.5 rounded-full bg-amber-500/10 px-2.5 py-0.5 text-xs font-semibold text-amber-400 border border-amber-500/20">
                              <AlertTriangle size={12} />
                              Uncertain
                            </span>
                          )}
                          {!scan.prediction && (
                            <span className="inline-flex items-center gap-1.5 rounded-full bg-slate-500/10 px-2.5 py-0.5 text-xs font-semibold text-slate-400 border border-slate-500/20">
                              Completed
                            </span>
                          )}
                        </>
                      ) : (
                        <span className="inline-flex items-center gap-1.5 rounded-full bg-slate-500/10 px-2.5 py-0.5 text-xs font-semibold text-slate-400 border border-slate-500/20 capitalize">
                          {scan.status}
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-3.5 font-semibold text-white text-xs">
                      {scan.confidence != null ? `${(scan.confidence * 100).toFixed(1)}%` : "-"}
                    </td>
                    <td className="px-6 py-3.5 text-slate-400 text-xs">
                      {new Date(scan.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-6 py-3.5 text-right">
                      <Link
                        to={`/analysis/${scan.id}`}
                        className="inline-flex items-center gap-1 text-xs font-semibold text-violet-400 hover:text-violet-300 transition"
                      >
                        Inspect
                        <ArrowRight size={12} />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
