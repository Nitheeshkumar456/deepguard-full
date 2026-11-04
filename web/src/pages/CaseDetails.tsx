import React, { useState, useEffect } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  Download,
  Plus,
  Trash2,
  Tag,
  ExternalLink,
  MessageSquare,
  Layers,
  Send,
  X
} from "lucide-react";
import { api } from "../services/api";

export default function CaseDetails() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [caseData, setCaseData] = useState<any | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // New Note state
  const [noteContent, setNoteContent] = useState("");
  const [isSubmittingNote, setIsSubmittingNote] = useState(false);

  // Attach Modal state
  const [isAttachModalOpen, setIsAttachModalOpen] = useState(false);
  const [availableAnalyses, setAvailableAnalyses] = useState<any[]>([]);
  const [selectedAnalysisId, setSelectedAnalysisId] = useState<number | null>(null);
  const [attachNote, setAttachNote] = useState("");
  const [isAttaching, setIsAttaching] = useState(false);

  const fetchCase = async () => {
    if (!id) return;
    setIsLoading(true);
    try {
      const data = await api.getCase(id);
      setCaseData(data);
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to load case details.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchCase();
  }, [id]);

  const handleStatusChange = async (newStatus: string) => {
    if (!id) return;
    try {
      const updated = await api.updateCase(id, { status: newStatus });
      setCaseData(updated);
    } catch (err: any) {
      alert("Failed to update status: " + err.message);
    }
  };

  const handlePriorityChange = async (newPriority: string) => {
    if (!id) return;
    try {
      const updated = await api.updateCase(id, { priority: newPriority });
      setCaseData(updated);
    } catch (err: any) {
      alert("Failed to update priority: " + err.message);
    }
  };

  const handleAddNote = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!noteContent.trim() || !id) return;
    setIsSubmittingNote(true);
    try {
      const updated = await api.addCaseNote(id, { content: noteContent.trim() });
      setCaseData(updated);
      setNoteContent("");
    } catch (err: any) {
      alert("Failed to add note: " + err.message);
    } finally {
      setIsSubmittingNote(false);
    }
  };

  const handleOpenAttachModal = async () => {
    setIsAttachModalOpen(true);
    try {
      const res = await api.getScanHistory(1, 50);
      const attachedIds = (caseData?.analyses || []).map((a: any) => a.analysis_id);
      const unattached = (res.analyses || []).filter((a: any) => !attachedIds.includes(a.id));
      setAvailableAnalyses(unattached);
      if (unattached.length > 0) {
        setSelectedAnalysisId(unattached[0].id);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleAttachAnalysis = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedAnalysisId || !id) return;
    setIsAttaching(true);
    try {
      const updated = await api.attachCaseAnalysis(id, {
        analysis_id: selectedAnalysisId,
        notes: attachNote.trim() || undefined,
      });
      setCaseData(updated);
      setIsAttachModalOpen(false);
      setAttachNote("");
      setSelectedAnalysisId(null);
    } catch (err: any) {
      alert("Failed to attach evidence: " + err.message);
    } finally {
      setIsAttaching(false);
    }
  };

  const handleDetachAnalysis = async (analysisId: number) => {
    if (!id || !confirm("Are you sure you want to remove this evidence artifact from the case?")) return;
    try {
      const updated = await api.detachCaseAnalysis(id, analysisId);
      setCaseData(updated);
    } catch (err: any) {
      alert("Failed to detach evidence: " + err.message);
    }
  };

  const handleDeleteCase = async () => {
    if (!id || !confirm("Are you sure you want to delete this investigation case? Attached analyses will not be deleted.")) return;
    try {
      await api.deleteCase(id);
      navigate("/cases");
    } catch (err: any) {
      alert("Failed to delete case: " + err.message);
    }
  };

  const handleExportDossier = async () => {
    if (!id) return;
    try {
      const dossier = await api.exportCaseDossier(id);
      const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(dossier, null, 2));
      const downloadAnchor = document.createElement("a");
      downloadAnchor.setAttribute("href", dataStr);
      downloadAnchor.setAttribute("download", `${caseData?.case_number || "case"}_dossier.json`);
      document.body.appendChild(downloadAnchor);
      downloadAnchor.click();
      downloadAnchor.remove();
    } catch (err: any) {
      alert("Export failed: " + err.message);
    }
  };

  if (isLoading) {
    return (
      <div className="flex justify-center items-center py-32">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-violet-500 border-t-transparent" />
      </div>
    );
  }

  if (errorMsg || !caseData) {
    return (
      <div className="space-y-4">
        <Link to="/cases" className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-white transition">
          <ArrowLeft size={14} /> Back to Cases
        </Link>
        <div className="rounded-2xl border border-red-500/20 bg-red-500/10 p-6 text-center text-sm text-red-400">
          {errorMsg || "Case not found."}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Top Navigation */}
      <div className="flex items-center justify-between">
        <Link
          to="/cases"
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-400 hover:text-white transition"
        >
          <ArrowLeft size={16} /> Back to Cases
        </Link>
        <div className="flex items-center gap-2">
          <button
            onClick={handleExportDossier}
            className="inline-flex items-center gap-2 rounded-xl border border-white/10 bg-slate-900 px-3.5 py-2 text-xs font-semibold text-slate-200 hover:bg-slate-800 transition"
          >
            <Download size={14} /> Export Case Dossier
          </button>
          <button
            onClick={handleDeleteCase}
            className="inline-flex items-center gap-1.5 rounded-xl border border-red-500/20 bg-red-500/10 px-3.5 py-2 text-xs font-semibold text-red-400 hover:bg-red-500/20 transition"
          >
            <Trash2 size={14} /> Delete Case
          </button>
        </div>
      </div>

      {/* Case Header Card */}
      <div className="rounded-2xl border border-white/10 bg-slate-900/60 p-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <span className="font-mono text-sm font-bold text-violet-400">{caseData.case_number}</span>
              <span className="text-xs text-slate-500">•</span>
              <span className="text-xs text-slate-400">Created {new Date(caseData.created_at).toLocaleDateString()}</span>
            </div>
            <h1 className="text-2xl font-bold text-white tracking-tight">{caseData.title}</h1>
            {caseData.description && (
              <p className="mt-2 text-sm text-slate-300 max-w-3xl leading-relaxed">{caseData.description}</p>
            )}

            {caseData.tags && (
              <div className="mt-3 flex flex-wrap gap-2">
                {caseData.tags.split(",").map((t: string, i: number) => (
                  <span key={i} className="inline-flex items-center gap-1 rounded bg-white/5 px-2.5 py-0.5 text-xs text-slate-400">
                    <Tag size={12} /> {t.trim()}
                  </span>
                ))}
              </div>
            )}
          </div>

          {/* Status & Priority Controls */}
          <div className="flex flex-wrap sm:flex-col gap-3 min-w-[160px]">
            <div>
              <label className="block text-[10px] font-semibold uppercase tracking-wider text-slate-400 mb-1">Status</label>
              <select
                value={caseData.status}
                onChange={(e) => handleStatusChange(e.target.value)}
                className="w-full rounded-xl bg-slate-950 border border-white/15 px-3 py-1.5 text-xs font-medium text-white focus:outline-none focus:border-violet-500"
              >
                <option value="OPEN">Open</option>
                <option value="IN_REVIEW">In Review</option>
                <option value="FLAGGED">Flagged Threat</option>
                <option value="RESOLVED">Resolved</option>
              </select>
            </div>

            <div>
              <label className="block text-[10px] font-semibold uppercase tracking-wider text-slate-400 mb-1">Priority</label>
              <select
                value={caseData.priority}
                onChange={(e) => handlePriorityChange(e.target.value)}
                className="w-full rounded-xl bg-slate-950 border border-white/15 px-3 py-1.5 text-xs font-medium text-white focus:outline-none focus:border-violet-500"
              >
                <option value="LOW">Low</option>
                <option value="MEDIUM">Medium</option>
                <option value="HIGH">High</option>
                <option value="CRITICAL">Critical</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content Grid: Evidence Chain & Notes */}
      <div className="grid grid-cols-1 gap-8 lg:grid-cols-3">
        {/* Left 2 Cols: Attached Evidence Artifacts */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <Layers className="text-violet-400" size={20} />
              Attached Forensic Evidence ({caseData.analyses.length})
            </h2>
            <button
              onClick={handleOpenAttachModal}
              className="inline-flex items-center gap-1.5 rounded-xl bg-violet-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-violet-500 transition"
            >
              <Plus size={14} /> Attach Media
            </button>
          </div>

          {caseData.analyses.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-white/10 p-10 text-center bg-slate-950/40">
              <Layers className="mx-auto text-slate-600 mb-2" size={32} />
              <p className="text-sm font-medium text-slate-300">No media artifacts attached to this case yet</p>
              <p className="text-xs text-slate-500 mt-1">Link image, video, or audio analyses to establish an evidence chain.</p>
              <button
                onClick={handleOpenAttachModal}
                className="mt-3 inline-flex items-center gap-1.5 rounded-xl border border-white/10 px-3 py-1.5 text-xs text-violet-300 hover:bg-white/5 transition"
              >
                <Plus size={14} /> Link Analysis
              </button>
            </div>
          ) : (
            <div className="space-y-3">
              {caseData.analyses.map((item: any) => {
                const isSynthetic = item.prediction === "synthetic";
                const isAuthentic = item.prediction === "authentic";

                return (
                  <div
                    key={item.id}
                    className="rounded-2xl border border-white/10 bg-slate-900/60 p-4 hover:border-white/20 transition flex flex-col gap-3"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <span className="capitalize px-2 py-0.5 rounded text-[11px] font-semibold bg-violet-500/20 text-violet-300 border border-violet-500/30">
                          {item.media_type}
                        </span>
                        <h4 className="text-sm font-semibold text-white truncate max-w-sm">{item.original_filename}</h4>
                      </div>

                      <div className="flex items-center gap-2">
                        {isSynthetic && (
                          <span className="px-2 py-0.5 rounded text-xs font-semibold bg-rose-500/20 text-rose-400 border border-rose-500/30">
                            SYNTHETIC ({Math.round((item.confidence || 0) * 100)}%)
                          </span>
                        )}
                        {isAuthentic && (
                          <span className="px-2 py-0.5 rounded text-xs font-semibold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                            AUTHENTIC ({Math.round((item.confidence || 0) * 100)}%)
                          </span>
                        )}
                        {!isSynthetic && !isAuthentic && (
                          <span className="px-2 py-0.5 rounded text-xs font-semibold bg-amber-500/20 text-amber-400 border border-amber-500/30">
                            UNCERTAIN
                          </span>
                        )}
                      </div>
                    </div>

                    {item.notes && (
                      <p className="text-xs text-slate-400 italic bg-slate-950/40 p-2.5 rounded-xl border border-white/5">
                        "{item.notes}"
                      </p>
                    )}

                    <div className="flex items-center justify-between pt-2 border-t border-white/5 text-xs text-slate-500">
                      <span>Added {new Date(item.added_at).toLocaleDateString()}</span>
                      <div className="flex items-center gap-3">
                        <Link
                          to={`/analysis/${item.analysis_id}`}
                          className="inline-flex items-center gap-1 text-violet-400 hover:text-violet-300 font-medium transition"
                        >
                          <ExternalLink size={12} /> View Full Forensics
                        </Link>
                        <button
                          onClick={() => handleDetachAnalysis(item.analysis_id)}
                          className="text-rose-400 hover:text-rose-300 transition"
                          title="Detach from case"
                        >
                          <X size={15} />
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Right 1 Col: Investigator Notes Timeline */}
        <div className="space-y-4">
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <MessageSquare className="text-violet-400" size={20} />
            Investigator Notes ({caseData.notes.length})
          </h2>

          {/* Add Note Form */}
          <form onSubmit={handleAddNote} className="rounded-2xl border border-white/10 bg-slate-900/60 p-4 space-y-3">
            <textarea
              rows={3}
              required
              placeholder="Record investigative observation or technical finding..."
              value={noteContent}
              onChange={(e) => setNoteContent(e.target.value)}
              className="w-full rounded-xl bg-slate-950 border border-white/10 p-3 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-violet-500"
            />
            <div className="flex justify-end">
              <button
                type="submit"
                disabled={isSubmittingNote || !noteContent.trim()}
                className="inline-flex items-center gap-1.5 rounded-xl bg-violet-600 px-3.5 py-1.5 text-xs font-semibold text-white hover:bg-violet-500 transition disabled:opacity-50"
              >
                <Send size={12} /> {isSubmittingNote ? "Posting..." : "Post Note"}
              </button>
            </div>
          </form>

          {/* Notes List */}
          <div className="space-y-3">
            {caseData.notes.length === 0 ? (
              <p className="text-xs text-slate-500 text-center py-6">No notes added yet.</p>
            ) : (
              caseData.notes.map((note: any) => (
                <div key={note.id} className="rounded-2xl border border-white/10 bg-slate-900/40 p-4 space-y-1.5">
                  <div className="flex items-center justify-between text-[11px] text-slate-400">
                    <span className="font-semibold text-violet-300">{note.author_name}</span>
                    <span>{new Date(note.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                  </div>
                  <p className="text-xs text-slate-200 leading-relaxed whitespace-pre-wrap">{note.content}</p>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Attach Modal */}
      {isAttachModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-2xl border border-white/10 bg-slate-950 p-6 shadow-2xl">
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <Plus className="text-violet-400" size={18} />
              Attach Analysis Evidence
            </h2>
            <p className="text-xs text-slate-400 mt-1">
              Select an existing media scan to include in this investigation case.
            </p>

            {availableAnalyses.length === 0 ? (
              <div className="mt-4 p-4 text-center text-xs text-slate-400">
                No unattached analyses available. Upload and analyze media first.
              </div>
            ) : (
              <form onSubmit={handleAttachAnalysis} className="mt-4 space-y-4">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Select Media Scan</label>
                  <select
                    value={selectedAnalysisId || ""}
                    onChange={(e) => setSelectedAnalysisId(Number(e.target.value))}
                    className="w-full rounded-xl bg-slate-900 border border-white/10 px-3 py-2 text-xs text-white focus:outline-none focus:border-violet-500"
                  >
                    {availableAnalyses.map((a) => (
                      <option key={a.id} value={a.id}>
                        [{a.media_type.toUpperCase()}] {a.original_filename} ({a.prediction || "pending"})
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Evidence Annotation (Optional)</label>
                  <input
                    type="text"
                    placeholder="e.g. Primary suspect frame from timestamp 00:04"
                    value={attachNote}
                    onChange={(e) => setAttachNote(e.target.value)}
                    className="w-full rounded-xl bg-slate-900 border border-white/10 px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-violet-500"
                  />
                </div>

                <div className="mt-6 flex justify-end gap-3 pt-2">
                  <button
                    type="button"
                    onClick={() => setIsAttachModalOpen(false)}
                    className="rounded-xl border border-white/10 px-3.5 py-1.5 text-xs text-slate-300 hover:bg-white/5 transition"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={isAttaching}
                    className="rounded-xl bg-violet-600 px-4 py-1.5 text-xs font-semibold text-white hover:bg-violet-500 transition disabled:opacity-50"
                  >
                    {isAttaching ? "Linking..." : "Attach to Case"}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
