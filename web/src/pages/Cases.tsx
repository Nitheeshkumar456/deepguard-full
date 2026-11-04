import React, { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  FolderGit2,
  Plus,
  Search,
  Clock,
  Tag,
  AlertTriangle,
  CheckCircle2,
  Layers,
  ArrowRight
} from "lucide-react";
import { api } from "../services/api";
import { wsService } from "../services/websocket";

interface CaseSummary {
  id: number;
  case_number: string;
  title: string;
  description?: string;
  status: "OPEN" | "IN_REVIEW" | "FLAGGED" | "RESOLVED";
  priority: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  tags?: string;
  analyses_count: number;
  notes_count: number;
  created_at: string;
  updated_at: string;
}

export default function Cases() {
  const navigate = useNavigate();
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [priorityFilter, setPriorityFilter] = useState<string>("ALL");

  // Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newDesc, setNewDesc] = useState("");
  const [newPriority, setNewPriority] = useState<string>("MEDIUM");
  const [newTags, setNewTags] = useState("");
  const [recentAnalyses, setRecentAnalyses] = useState<any[]>([]);
  const [selectedAnalysisIds, setSelectedAnalysisIds] = useState<number[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const fetchCases = async () => {
    setIsLoading(true);
    try {
      const params: any = {};
      if (statusFilter !== "ALL") params.status = statusFilter;
      if (priorityFilter !== "ALL") params.priority = priorityFilter;
      if (search.trim()) params.search = search.trim();
      const res = await api.getCases(params);
      setCases(res);
    } catch (err: any) {
      console.error("Failed to load cases", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchCases();
  }, [statusFilter, priorityFilter]);

  // WebSocket real-time subscription
  useEffect(() => {
    const unsub = wsService.subscribe("*", () => {
      fetchCases();
    });
    return () => unsub();
  }, []);

  const handleOpenCreateModal = async () => {
    setIsModalOpen(true);
    setErrorMsg(null);
    try {
      const historyRes = await api.getScanHistory(1, 20);
      setRecentAnalyses(historyRes.analyses || []);
    } catch (e) {
      console.error("Could not fetch recent analyses", e);
    }
  };

  const handleCreateCase = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle.trim()) {
      setErrorMsg("Please enter a valid case title.");
      return;
    }
    setIsSubmitting(true);
    setErrorMsg(null);
    try {
      const created = await api.createCase({
        title: newTitle.trim(),
        description: newDesc.trim() || undefined,
        priority: newPriority,
        tags: newTags.trim() || undefined,
        initial_analysis_ids: selectedAnalysisIds,
      });
      setIsModalOpen(false);
      setNewTitle("");
      setNewDesc("");
      setNewTags("");
      setSelectedAnalysisIds([]);
      navigate(`/cases/${created.id}`);
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to create investigation case.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const toggleAnalysisSelection = (id: number) => {
    if (selectedAnalysisIds.includes(id)) {
      setSelectedAnalysisIds(selectedAnalysisIds.filter((x) => x !== id));
    } else {
      setSelectedAnalysisIds([...selectedAnalysisIds, id]);
    }
  };

  const getPriorityBadge = (p: string) => {
    switch (p) {
      case "CRITICAL":
        return <span className="px-2 py-0.5 rounded text-xs font-semibold bg-rose-500/20 text-rose-400 border border-rose-500/30">CRITICAL</span>;
      case "HIGH":
        return <span className="px-2 py-0.5 rounded text-xs font-semibold bg-amber-500/20 text-amber-400 border border-amber-500/30">HIGH</span>;
      case "MEDIUM":
        return <span className="px-2 py-0.5 rounded text-xs font-semibold bg-violet-500/20 text-violet-400 border border-violet-500/30">MEDIUM</span>;
      default:
        return <span className="px-2 py-0.5 rounded text-xs font-semibold bg-slate-500/20 text-slate-400 border border-slate-500/30">LOW</span>;
    }
  };

  const getStatusBadge = (s: string) => {
    switch (s) {
      case "FLAGGED":
        return <span className="flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-red-950/60 text-red-300 border border-red-800/50"><AlertTriangle size={12} /> Flagged</span>;
      case "IN_REVIEW":
        return <span className="flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-sky-950/60 text-sky-300 border border-sky-800/50"><Clock size={12} /> In Review</span>;
      case "RESOLVED":
        return <span className="flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-950/60 text-emerald-300 border border-emerald-800/50"><CheckCircle2 size={12} /> Resolved</span>;
      default:
        return <span className="flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-violet-950/60 text-violet-300 border border-violet-800/50"><FolderGit2 size={12} /> Open</span>;
    }
  };

  const totalCount = cases.length;
  const flaggedCount = cases.filter((c) => c.status === "FLAGGED").length;
  const inReviewCount = cases.filter((c) => c.status === "IN_REVIEW").length;
  const resolvedCount = cases.filter((c) => c.status === "RESOLVED").length;

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2.5">
            <FolderGit2 className="text-violet-400" size={26} />
            Forensic Investigation Cases
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Group suspect media artifacts, track evidence chains of custody, and collaborate on forensic findings.
          </p>
        </div>
        <button
          onClick={handleOpenCreateModal}
          className="inline-flex items-center gap-2 rounded-xl bg-violet-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-violet-500 transition focus:outline-none"
        >
          <Plus size={18} />
          New Investigation Case
        </button>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <div className="rounded-2xl border border-white/10 bg-slate-900/60 p-5">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">Total Cases</p>
          <p className="mt-2 text-2xl font-bold text-white">{totalCount}</p>
        </div>
        <div className="rounded-2xl border border-white/10 bg-slate-900/60 p-5">
          <p className="text-xs font-semibold uppercase tracking-wider text-sky-400">Under Review</p>
          <p className="mt-2 text-2xl font-bold text-sky-300">{inReviewCount}</p>
        </div>
        <div className="rounded-2xl border border-white/10 bg-slate-900/60 p-5">
          <p className="text-xs font-semibold uppercase tracking-wider text-rose-400">Flagged Threats</p>
          <p className="mt-2 text-2xl font-bold text-rose-400">{flaggedCount}</p>
        </div>
        <div className="rounded-2xl border border-white/10 bg-slate-900/60 p-5">
          <p className="text-xs font-semibold uppercase tracking-wider text-emerald-400">Resolved</p>
          <p className="mt-2 text-2xl font-bold text-emerald-300">{resolvedCount}</p>
        </div>
      </div>

      {/* Filters and Search Bar */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between bg-slate-900/40 p-4 rounded-2xl border border-white/10">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" size={16} />
          <input
            type="text"
            placeholder="Search by case number, title, or tag..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && fetchCases()}
            className="w-full rounded-xl bg-slate-950/80 border border-white/10 pl-10 pr-4 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-violet-500"
          />
        </div>

        <div className="flex items-center gap-3">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="rounded-xl bg-slate-950/80 border border-white/10 px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-violet-500"
          >
            <option value="ALL">All Statuses</option>
            <option value="OPEN">Open</option>
            <option value="IN_REVIEW">In Review</option>
            <option value="FLAGGED">Flagged</option>
            <option value="RESOLVED">Resolved</option>
          </select>

          <select
            value={priorityFilter}
            onChange={(e) => setPriorityFilter(e.target.value)}
            className="rounded-xl bg-slate-950/80 border border-white/10 px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-violet-500"
          >
            <option value="ALL">All Priorities</option>
            <option value="CRITICAL">Critical</option>
            <option value="HIGH">High</option>
            <option value="MEDIUM">Medium</option>
            <option value="LOW">Low</option>
          </select>
        </div>
      </div>

      {/* Case List */}
      {isLoading ? (
        <div className="flex justify-center items-center py-24">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-violet-500 border-t-transparent" />
        </div>
      ) : cases.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-white/10 p-12 text-center bg-slate-950/40">
          <FolderGit2 className="mx-auto text-slate-600 mb-3" size={40} />
          <h3 className="text-base font-semibold text-white">No investigation cases found</h3>
          <p className="mt-1 text-sm text-slate-400">
            Create an investigation case to organize related media analyses and evidence.
          </p>
          <button
            onClick={handleOpenCreateModal}
            className="mt-4 inline-flex items-center gap-2 rounded-xl bg-violet-600 px-4 py-2 text-sm font-semibold text-white hover:bg-violet-500 transition"
          >
            <Plus size={16} />
            Create First Case
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {cases.map((c) => (
            <Link
              key={c.id}
              to={`/cases/${c.id}`}
              className="group rounded-2xl border border-white/10 bg-slate-900/60 p-5 hover:border-violet-500/50 hover:bg-slate-900/90 transition flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between mb-3">
                  <span className="text-xs font-mono font-medium text-slate-400">{c.case_number}</span>
                  <div className="flex items-center gap-2">
                    {getPriorityBadge(c.priority)}
                    {getStatusBadge(c.status)}
                  </div>
                </div>

                <h3 className="text-base font-semibold text-white group-hover:text-violet-300 transition line-clamp-1">
                  {c.title}
                </h3>
                {c.description && (
                  <p className="mt-1.5 text-xs text-slate-400 line-clamp-2 leading-relaxed">
                    {c.description}
                  </p>
                )}

                {c.tags && (
                  <div className="mt-3 flex flex-wrap gap-1.5">
                    {c.tags.split(",").slice(0, 3).map((tag, i) => (
                      <span key={i} className="inline-flex items-center gap-1 rounded bg-white/5 px-2 py-0.5 text-[10px] text-slate-400">
                        <Tag size={10} />
                        {tag.trim()}
                      </span>
                    ))}
                  </div>
                )}
              </div>

              <div className="mt-5 pt-4 border-t border-white/5 flex items-center justify-between text-xs text-slate-400">
                <div className="flex items-center gap-3">
                  <span className="flex items-center gap-1">
                    <Layers size={13} className="text-violet-400" />
                    {c.analyses_count} {c.analyses_count === 1 ? "artifact" : "artifacts"}
                  </span>
                  <span>•</span>
                  <span>{c.notes_count} {c.notes_count === 1 ? "note" : "notes"}</span>
                </div>
                <ArrowRight size={14} className="text-slate-500 group-hover:translate-x-1 group-hover:text-violet-400 transition" />
              </div>
            </Link>
          ))}
        </div>
      )}

      {/* Create Case Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="w-full max-w-lg rounded-2xl border border-white/10 bg-slate-950 p-6 shadow-2xl">
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <FolderGit2 className="text-violet-400" size={20} />
              New Investigation Case
            </h2>
            <p className="text-xs text-slate-400 mt-1">
              Initialize a dedicated investigative case file to correlate forensic findings.
            </p>

            {errorMsg && (
              <div className="mt-4 rounded-xl border border-red-500/20 bg-red-500/10 p-3 text-xs text-red-400">
                {errorMsg}
              </div>
            )}

            <form onSubmit={handleCreateCase} className="mt-4 space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Case Title *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Operation DeepShield Executive Impersonation"
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  className="w-full rounded-xl bg-slate-900 border border-white/10 px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-violet-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Description / Brief</label>
                <textarea
                  rows={2}
                  placeholder="Briefly state the suspected threat or investigative goal..."
                  value={newDesc}
                  onChange={(e) => setNewDesc(e.target.value)}
                  className="w-full rounded-xl bg-slate-900 border border-white/10 px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-violet-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Priority</label>
                  <select
                    value={newPriority}
                    onChange={(e) => setNewPriority(e.target.value)}
                    className="w-full rounded-xl bg-slate-900 border border-white/10 px-3 py-2 text-sm text-white focus:outline-none focus:border-violet-500"
                  >
                    <option value="LOW">Low</option>
                    <option value="MEDIUM">Medium</option>
                    <option value="HIGH">High</option>
                    <option value="CRITICAL">Critical</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Tags (comma-separated)</label>
                  <input
                    type="text"
                    placeholder="deepfake, audio, phishing"
                    value={newTags}
                    onChange={(e) => setNewTags(e.target.value)}
                    className="w-full rounded-xl bg-slate-900 border border-white/10 px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-violet-500"
                  />
                </div>
              </div>

              {recentAnalyses.length > 0 && (
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Attach Initial Evidence ({selectedAnalysisIds.length} selected)
                  </label>
                  <div className="max-h-36 overflow-y-auto rounded-xl border border-white/10 bg-slate-900/50 p-2 space-y-1">
                    {recentAnalyses.map((item) => {
                      const isSelected = selectedAnalysisIds.includes(item.id);
                      return (
                        <div
                          key={item.id}
                          onClick={() => toggleAnalysisSelection(item.id)}
                          className={`flex items-center justify-between p-2 rounded-lg text-xs cursor-pointer transition ${
                            isSelected ? "bg-violet-600/30 border border-violet-500/40 text-white" : "hover:bg-white/5 text-slate-300"
                          }`}
                        >
                          <span className="truncate max-w-[240px]">{item.original_filename}</span>
                          <span className="text-[10px] text-slate-400 capitalize">{item.media_type}</span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              <div className="mt-6 flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="rounded-xl border border-white/10 px-4 py-2 text-xs font-semibold text-slate-300 hover:bg-white/5 transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="rounded-xl bg-violet-600 px-4 py-2 text-xs font-semibold text-white hover:bg-violet-500 transition disabled:opacity-50"
                >
                  {isSubmitting ? "Creating..." : "Create Case"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
