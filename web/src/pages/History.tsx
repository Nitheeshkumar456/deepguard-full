import { useState, useEffect, useCallback } from "react";
import { Link, useSearchParams } from "react-router-dom";
import PageHeader from "../components/PageHeader";
import { EmptyState } from "../components/FeedbackStates";
import { apiService } from "../services/api";
import { syncWebSocket } from "../services/websocket";
import {
  Search,
  ShieldAlert,
  CheckCircle2,
  AlertTriangle,
  FileImage,
  FileVideo,
  FileAudio,
  ArrowRight,
  Loader2,
} from "lucide-react";

export default function History() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [searchTerm, setSearchTerm] = useState("");
  const [mediaType, setMediaType] = useState<string>(searchParams.get("media_type") || "all");
  const [verdict, setVerdict] = useState<string>(searchParams.get("verdict") || "all");
  const [riskStatus, setRiskStatus] = useState<string>(searchParams.get("status") || "all");
  
  const [scans, setScans] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const pageSize = 10;

  // Sync state if search params in URL change
  useEffect(() => {
    const pVerdict = searchParams.get("verdict") || "all";
    const pMediaType = searchParams.get("media_type") || "all";
    const pStatus = searchParams.get("status") || "all";
    setVerdict(pVerdict);
    setMediaType(pMediaType);
    setRiskStatus(pStatus);
  }, [searchParams]);

  const fetchHistory = useCallback(async () => {
    setLoading(true);
    try {
      const data = await apiService.getAnalysisHistory({
        page,
        page_size: pageSize,
        media_type: mediaType,
        status: riskStatus,
        prediction: verdict,
      });
      setScans(data.items || []);
      setTotal(data.total || 0);
    } catch (error) {
      console.error("Failed to fetch history:", error);
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, mediaType, riskStatus, verdict]);

  useEffect(() => {
    fetchHistory();

    const unsubUpload = syncWebSocket.subscribe("media.uploaded", (item) => {
      if (item && item.id) {
        setScans((prev) => {
          if (prev.some((s) => s.id === item.id)) return prev;
          return [item, ...prev];
        });
        setTotal((t) => t + 1);
      }
    });

    const unsubCompleted = syncWebSocket.subscribe("analysis.completed", (detail) => {
      if (detail && detail.id) {
        setScans((prev) =>
          prev.map((s) =>
            s.id === detail.id
              ? {
                  ...s,
                  status: "completed",
                  prediction: detail.result?.prediction || s.prediction,
                  confidence: detail.result?.confidence || s.confidence,
                  risk_level: detail.result?.risk_level || s.risk_level,
                  processing_time: detail.processing_time,
                  completed_at: detail.completed_at,
                }
              : s
          )
        );
      }
    });

    const unsubFailed = syncWebSocket.subscribe("analysis.failed", (failData) => {
      if (failData && failData.analysis_id) {
        setScans((prev) =>
          prev.map((s) =>
            s.id === failData.analysis_id ? { ...s, status: "failed" } : s
          )
        );
      }
    });

    const unsubDeleted = syncWebSocket.subscribe("media.deleted", (delData) => {
      if (delData && delData.analysis_id) {
        setScans((prev) => prev.filter((s) => s.id !== delData.analysis_id));
        setTotal((t) => Math.max(0, t - 1));
      }
    });

    const unsubReconnect = syncWebSocket.onReconnect(() => {
      fetchHistory();
    });

    return () => {
      unsubUpload();
      unsubCompleted();
      unsubFailed();
      unsubDeleted();
      unsubReconnect();
    };
  }, [fetchHistory]);

  const updateFilters = (newParams: { media_type?: string; verdict?: string; status?: string }) => {
    const updated = new URLSearchParams(searchParams);
    if (newParams.media_type !== undefined) {
      if (newParams.media_type === "all") updated.delete("media_type");
      else updated.set("media_type", newParams.media_type);
      setMediaType(newParams.media_type);
    }
    if (newParams.verdict !== undefined) {
      if (newParams.verdict === "all") updated.delete("verdict");
      else updated.set("verdict", newParams.verdict);
      setVerdict(newParams.verdict);
    }
    if (newParams.status !== undefined) {
      if (newParams.status === "all") updated.delete("status");
      else updated.set("status", newParams.status);
      setRiskStatus(newParams.status);
    }
    setPage(1);
    setSearchParams(updated, { replace: true });
  };

  const clearFilters = () => {
    setSearchTerm("");
    setMediaType("all");
    setVerdict("all");
    setRiskStatus("all");
    setPage(1);
    setSearchParams({}, { replace: true });
  };

  // Client-side search filter for file name or ID
  const filteredScans = scans.filter((scan) => {
    if (!searchTerm) return true;
    const term = searchTerm.toLowerCase();
    return (
      (scan.original_filename || "").toLowerCase().includes(term) ||
      scan.id.toString().includes(term)
    );
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="Scan History"
        description="View, search, and audit all processed file classification analysis reports."
      />

      {/* Query Filter Area */}
      <div className="grid gap-4 md:grid-cols-5 bg-white/[0.01] border border-white/10 rounded-2xl p-4">
        {/* Search Input */}
        <div className="relative md:col-span-2">
          <Search size={18} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-500" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search scans by file name or ID..."
            className="w-full rounded-xl border border-white/10 bg-slate-900 px-10 py-2.5 text-sm text-white outline-none focus:border-violet-500"
            aria-label="Search scans"
          />
        </div>

        {/* Media Type Filter */}
        <div>
          <select
            value={mediaType}
            onChange={(e) => updateFilters({ media_type: e.target.value })}
            className="w-full rounded-xl border border-white/10 bg-slate-900 px-3 py-2.5 text-sm text-slate-300 outline-none focus:border-violet-500"
            aria-label="Filter by media type"
          >
            <option value="all">All Media Types</option>
            <option value="image">Images</option>
            <option value="video">Videos</option>
            <option value="audio">Audio</option>
          </select>
        </div>

        {/* Verdict Filter */}
        <div>
          <select
            value={verdict}
            onChange={(e) => updateFilters({ verdict: e.target.value })}
            className="w-full rounded-xl border border-white/10 bg-slate-900 px-3 py-2.5 text-sm text-slate-300 outline-none focus:border-violet-500"
            aria-label="Filter by verdict"
          >
            <option value="all">All Verdicts</option>
            <option value="authentic">Authentic / Real</option>
            <option value="synthetic">AI / Synthetic</option>
            <option value="uncertain">Uncertain / Other</option>
          </select>
        </div>

        {/* Status Filter */}
        <div>
          <select
            value={riskStatus}
            onChange={(e) => updateFilters({ status: e.target.value })}
            className="w-full rounded-xl border border-white/10 bg-slate-900 px-3 py-2.5 text-sm text-slate-300 outline-none focus:border-violet-500"
            aria-label="Filter by processing status"
          >
            <option value="all">All Statuses</option>
            <option value="completed">Completed</option>
            <option value="queued">Queued</option>
            <option value="processing">Processing</option>
            <option value="failed">Failed</option>
          </select>
        </div>
      </div>

      {/* Scans List / Table */}
      {loading ? (
        <div className="flex flex-col items-center justify-center p-12 text-slate-400">
          <Loader2 size={32} className="animate-spin mb-4 text-violet-500" />
          <p>Loading analysis history...</p>
        </div>
      ) : filteredScans.length === 0 ? (
        <EmptyState
          title="No scans match criteria"
          description="Try broadening your filters or clearing search terms to discover historical scans."
          actionLabel="Clear Filters"
          onAction={clearFilters}
        />
      ) : (
        <div className="rounded-2xl border border-white/10 bg-white/[0.01] overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-left text-sm">
              <thead className="border-b border-white/10 bg-slate-950/50 text-slate-400 font-semibold uppercase tracking-wider text-[11px]">
                <tr>
                  <th className="px-6 py-4">Scan ID</th>
                  <th className="px-6 py-4">File Name</th>
                  <th className="px-6 py-4">Media Type</th>
                  <th className="px-6 py-4">Status / Result</th>
                  <th className="px-6 py-4">Confidence</th>
                  <th className="px-6 py-4">Date</th>
                  <th className="px-6 py-4 text-right">Audit</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5 text-slate-300">
                {filteredScans.map((scan) => (
                  <tr key={scan.id} className="hover:bg-white/[0.02] transition group">
                    <td className="px-6 py-4 font-mono text-xs text-violet-400 font-semibold">
                      {scan.id}
                    </td>
                    <td className="px-6 py-4 font-medium text-white truncate max-w-xs">
                      {scan.original_filename}
                    </td>
                    <td className="px-6 py-4">
                      <span className="flex items-center gap-2">
                        {scan.media_type === "image" && <FileImage size={16} className="text-slate-500" />}
                        {scan.media_type === "video" && <FileVideo size={16} className="text-slate-500" />}
                        {scan.media_type === "audio" && <FileAudio size={16} className="text-slate-500" />}
                        <span className="capitalize">{scan.media_type}</span>
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      {scan.status === "completed" ? (
                        <>
                          {scan.prediction === "authentic" && (
                            <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-500/10 px-2.5 py-1 text-xs font-semibold text-emerald-400 border border-emerald-500/20">
                              <CheckCircle2 size={12} />
                              Authentic
                            </span>
                          )}
                          {scan.prediction === "synthetic" && (
                            <span className="inline-flex items-center gap-1.5 rounded-full bg-rose-500/10 px-2.5 py-1 text-xs font-semibold text-rose-400 border border-rose-500/20">
                              <ShieldAlert size={12} />
                              Synthetic
                            </span>
                          )}
                          {scan.prediction === "uncertain" && (
                            <span className="inline-flex items-center gap-1.5 rounded-full bg-amber-500/10 px-2.5 py-1 text-xs font-semibold text-amber-400 border border-amber-500/20">
                              <AlertTriangle size={12} />
                              Uncertain
                            </span>
                          )}
                        </>
                      ) : (
                        <span className="inline-flex items-center gap-1.5 rounded-full bg-slate-500/10 px-2.5 py-1 text-xs font-semibold text-slate-400 border border-slate-500/20 capitalize">
                          {scan.status}
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4 font-semibold text-white">
                      {scan.confidence ? `${(scan.confidence * 100).toFixed(1)}%` : "-"}
                    </td>
                    <td className="px-6 py-4 text-slate-400">
                      {new Date(scan.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <Link
                        to={`/analysis/${scan.id}`}
                        className="inline-flex items-center gap-1.5 rounded-xl border border-white/10 px-3.5 py-1.5 text-xs font-semibold text-slate-300 hover:border-violet-500 hover:bg-violet-600 hover:text-white transition group-hover:border-white/20"
                      >
                        Inspect
                        <ArrowRight size={12} className="transition-transform group-hover:translate-x-0.5" />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination Controls */}
          {total > pageSize && (
            <div className="border-t border-white/10 bg-slate-950/20 px-6 py-4 flex items-center justify-between">
              <div className="text-xs text-slate-500 font-medium">
                Showing {filteredScans.length} of {total} historical scans.
              </div>
              <div className="flex gap-2">
                <button
                  disabled={page === 1}
                  onClick={() => setPage(page - 1)}
                  className="px-3 py-1 text-xs font-semibold rounded-lg border border-white/10 text-slate-300 hover:bg-white/5 disabled:opacity-50"
                >
                  Previous
                </button>
                <button
                  disabled={page * pageSize >= total}
                  onClick={() => setPage(page + 1)}
                  className="px-3 py-1 text-xs font-semibold rounded-lg border border-white/10 text-slate-300 hover:bg-white/5 disabled:opacity-50"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
