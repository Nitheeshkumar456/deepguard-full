import { useState, useEffect } from "react";
import { useSearchParams, Link } from "react-router-dom";
import {
  Activity,
  Layers,
  ChevronRight,
  Scale
} from "lucide-react";
import { api } from "../services/api";

export default function CompareMedia() {
  const [searchParams, setSearchParams] = useSearchParams();
  const paramId1 = searchParams.get("id1");
  const paramId2 = searchParams.get("id2");

  const [historyList, setHistoryList] = useState<any[]>([]);
  const [selectedId1, setSelectedId1] = useState<number | null>(paramId1 ? Number(paramId1) : null);
  const [selectedId2, setSelectedId2] = useState<number | null>(paramId2 ? Number(paramId2) : null);

  const [comparisonResult, setComparisonResult] = useState<any | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    // Load recent scan history to populate selectors
    const loadHistory = async () => {
      try {
        const res = await api.getScanHistory(1, 50);
        const completed = (res.analyses || []).filter((a: any) => a.status === "completed");
        setHistoryList(completed);
        if (completed.length >= 2 && !selectedId1 && !selectedId2) {
          setSelectedId1(completed[0].id);
          setSelectedId2(completed[1].id);
        }
      } catch (err) {
        console.error("Failed to load scan history", err);
      }
    };
    loadHistory();
  }, []);

  const runComparison = async () => {
    if (!selectedId1 || !selectedId2) return;
    if (selectedId1 === selectedId2) {
      setErrorMsg("Please select two distinct media artifacts to compare.");
      return;
    }
    setIsLoading(true);
    setErrorMsg(null);
    try {
      setSearchParams({ id1: String(selectedId1), id2: String(selectedId2) });
      const res = await api.compareAnalyses(selectedId1, selectedId2);
      setComparisonResult(res);
    } catch (err: any) {
      setErrorMsg(err.message || "Forensic comparison failed.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (selectedId1 && selectedId2 && selectedId1 !== selectedId2) {
      runComparison();
    }
  }, [selectedId1, selectedId2]);

  const item1 = comparisonResult?.item1;
  const item2 = comparisonResult?.item2;
  const comp = comparisonResult?.comparison;

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2.5">
          <Scale className="text-violet-400" size={26} />
          Side-by-Side Forensic Comparison
        </h1>
        <p className="text-sm text-slate-400 mt-1">
          Compare two media artifacts to evaluate authenticity discrepancies, confidence delta, and anomaly patterns.
        </p>
      </div>

      {/* Selectors Bar */}
      <div className="rounded-2xl border border-white/10 bg-slate-900/60 p-5">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {/* Artifact A */}
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-violet-400 mb-1.5">
              Artifact A (Baseline / Target)
            </label>
            <select
              value={selectedId1 || ""}
              onChange={(e) => setSelectedId1(Number(e.target.value))}
              className="w-full rounded-xl bg-slate-950 border border-white/10 px-3.5 py-2.5 text-xs text-white focus:outline-none focus:border-violet-500"
            >
              <option value="" disabled>Select first artifact...</option>
              {historyList.map((item) => (
                <option key={item.id} value={item.id} disabled={item.id === selectedId2}>
                  [{item.media_type.toUpperCase()}] {item.original_filename} ({(item.prediction || "completed").toUpperCase()})
                </option>
              ))}
            </select>
          </div>

          {/* Artifact B */}
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-sky-400 mb-1.5">
              Artifact B (Comparison Specimen)
            </label>
            <select
              value={selectedId2 || ""}
              onChange={(e) => setSelectedId2(Number(e.target.value))}
              className="w-full rounded-xl bg-slate-950 border border-white/10 px-3.5 py-2.5 text-xs text-white focus:outline-none focus:border-violet-500"
            >
              <option value="" disabled>Select second artifact...</option>
              {historyList.map((item) => (
                <option key={item.id} value={item.id} disabled={item.id === selectedId1}>
                  [{item.media_type.toUpperCase()}] {item.original_filename} ({(item.prediction || "completed").toUpperCase()})
                </option>
              ))}
            </select>
          </div>
        </div>

        {errorMsg && (
          <div className="mt-4 rounded-xl border border-red-500/20 bg-red-500/10 p-3 text-xs text-red-400">
            {errorMsg}
          </div>
        )}
      </div>

      {/* Comparison Body */}
      {isLoading ? (
        <div className="flex justify-center items-center py-24">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-violet-500 border-t-transparent" />
        </div>
      ) : !comparisonResult ? (
        <div className="rounded-2xl border border-dashed border-white/10 p-12 text-center bg-slate-950/40">
          <Scale className="mx-auto text-slate-600 mb-3" size={36} />
          <p className="text-sm font-medium text-slate-300">Select two media artifacts to launch forensic comparison</p>
        </div>
      ) : (
        <div className="space-y-6">
          {/* Verdict Banner */}
          <div className="rounded-2xl border border-violet-500/30 bg-violet-950/20 p-5 flex items-start gap-3">
            <Activity className="text-violet-400 shrink-0 mt-0.5" size={20} />
            <div>
              <h3 className="text-sm font-bold text-white uppercase tracking-wider">Comparative Finding</h3>
              <p className="text-xs text-slate-200 mt-1 leading-relaxed">{comp.forensic_verdict}</p>
              <div className="mt-3 flex flex-wrap items-center gap-4 text-[11px] text-slate-400">
                <span>Modality: <strong className="text-white">{comp.same_modality ? "Matched" : "Cross-Modal"}</strong></span>
                <span>•</span>
                <span>Prediction: <strong className={comp.prediction_match ? "text-emerald-400" : "text-amber-400"}>{comp.prediction_match ? "Consistent" : "Discrepant"}</strong></span>
                <span>•</span>
                <span>Confidence Delta: <strong className="text-white">{(comp.confidence_delta * 100).toFixed(1)}%</strong></span>
              </div>
            </div>
          </div>

          {/* Side-by-Side Cards */}
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
            {/* Specimen A Card */}
            <div className="rounded-2xl border border-white/10 bg-slate-900/60 p-6 flex flex-col justify-between space-y-4">
              <div>
                <div className="flex items-center justify-between pb-3 border-b border-white/10">
                  <span className="text-xs font-semibold text-violet-400 uppercase tracking-wider">Specimen A</span>
                  <Link
                    to={`/analysis/${item1.id}`}
                    className="text-xs text-violet-400 hover:text-violet-300 font-medium inline-flex items-center gap-1"
                  >
                    View Details <ChevronRight size={14} />
                  </Link>
                </div>

                <h3 className="text-base font-bold text-white mt-3 truncate">{item1.original_filename}</h3>
                <p className="text-xs text-slate-400 capitalize mt-0.5">{item1.media_type} • {item1.file_size ? `${Math.round(item1.file_size / 1024)} KB` : "Standard"}</p>

                {/* Prediction Bar */}
                <div className="mt-4 p-4 rounded-xl bg-slate-950/80 border border-white/5 space-y-2">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-400 font-medium">Model Classification</span>
                    <span className={`font-bold uppercase ${item1.prediction === "synthetic" ? "text-rose-400" : "text-emerald-400"}`}>
                      {item1.prediction}
                    </span>
                  </div>
                  <div className="h-2 w-full bg-slate-800 rounded-full overflow-hidden">
                    <div
                      className={`h-full ${item1.prediction === "synthetic" ? "bg-rose-500" : "bg-emerald-500"}`}
                      style={{ width: `${Math.round((item1.confidence || 0) * 100)}%` }}
                    />
                  </div>
                  <div className="flex justify-between text-[11px] text-slate-500">
                    <span>Calibrated Confidence</span>
                    <span className="text-slate-300 font-semibold">{Math.round((item1.confidence || 0) * 100)}%</span>
                  </div>
                </div>

                {/* Score Metrics */}
                <div className="mt-4 space-y-2 text-xs">
                  {item1.face_manipulation_score !== null && (
                    <div className="flex justify-between py-1 border-b border-white/5">
                      <span className="text-slate-400">Face Manipulation Score</span>
                      <span className="font-semibold text-slate-200">{(item1.face_manipulation_score * 100).toFixed(1)}%</span>
                    </div>
                  )}
                  {item1.gan_artifact_score !== null && (
                    <div className="flex justify-between py-1 border-b border-white/5">
                      <span className="text-slate-400">GAN Artifact Signature</span>
                      <span className="font-semibold text-slate-200">{(item1.gan_artifact_score * 100).toFixed(1)}%</span>
                    </div>
                  )}
                  {item1.spectral_anomaly_score !== null && (
                    <div className="flex justify-between py-1 border-b border-white/5">
                      <span className="text-slate-400">Spectral Anomaly Score</span>
                      <span className="font-semibold text-slate-200">{(item1.spectral_anomaly_score * 100).toFixed(1)}%</span>
                    </div>
                  )}
                  {item1.voice_cloning_score !== null && (
                    <div className="flex justify-between py-1 border-b border-white/5">
                      <span className="text-slate-400">Voice Synthesis Score</span>
                      <span className="font-semibold text-slate-200">{(item1.voice_cloning_score * 100).toFixed(1)}%</span>
                    </div>
                  )}
                </div>
              </div>

              <div className="pt-2 text-[11px] text-slate-500">
                Model: {item1.model_name || "DualPath DeepGuard Model"}
              </div>
            </div>

            {/* Specimen B Card */}
            <div className="rounded-2xl border border-white/10 bg-slate-900/60 p-6 flex flex-col justify-between space-y-4">
              <div>
                <div className="flex items-center justify-between pb-3 border-b border-white/10">
                  <span className="text-xs font-semibold text-sky-400 uppercase tracking-wider">Specimen B</span>
                  <Link
                    to={`/analysis/${item2.id}`}
                    className="text-xs text-sky-400 hover:text-sky-300 font-medium inline-flex items-center gap-1"
                  >
                    View Details <ChevronRight size={14} />
                  </Link>
                </div>

                <h3 className="text-base font-bold text-white mt-3 truncate">{item2.original_filename}</h3>
                <p className="text-xs text-slate-400 capitalize mt-0.5">{item2.media_type} • {item2.file_size ? `${Math.round(item2.file_size / 1024)} KB` : "Standard"}</p>

                {/* Prediction Bar */}
                <div className="mt-4 p-4 rounded-xl bg-slate-950/80 border border-white/5 space-y-2">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-400 font-medium">Model Classification</span>
                    <span className={`font-bold uppercase ${item2.prediction === "synthetic" ? "text-rose-400" : "text-emerald-400"}`}>
                      {item2.prediction}
                    </span>
                  </div>
                  <div className="h-2 w-full bg-slate-800 rounded-full overflow-hidden">
                    <div
                      className={`h-full ${item2.prediction === "synthetic" ? "bg-rose-500" : "bg-emerald-500"}`}
                      style={{ width: `${Math.round((item2.confidence || 0) * 100)}%` }}
                    />
                  </div>
                  <div className="flex justify-between text-[11px] text-slate-500">
                    <span>Calibrated Confidence</span>
                    <span className="text-slate-300 font-semibold">{Math.round((item2.confidence || 0) * 100)}%</span>
                  </div>
                </div>

                {/* Score Metrics */}
                <div className="mt-4 space-y-2 text-xs">
                  {item2.face_manipulation_score !== null && (
                    <div className="flex justify-between py-1 border-b border-white/5">
                      <span className="text-slate-400">Face Manipulation Score</span>
                      <span className="font-semibold text-slate-200">{(item2.face_manipulation_score * 100).toFixed(1)}%</span>
                    </div>
                  )}
                  {item2.gan_artifact_score !== null && (
                    <div className="flex justify-between py-1 border-b border-white/5">
                      <span className="text-slate-400">GAN Artifact Signature</span>
                      <span className="font-semibold text-slate-200">{(item2.gan_artifact_score * 100).toFixed(1)}%</span>
                    </div>
                  )}
                  {item2.spectral_anomaly_score !== null && (
                    <div className="flex justify-between py-1 border-b border-white/5">
                      <span className="text-slate-400">Spectral Anomaly Score</span>
                      <span className="font-semibold text-slate-200">{(item2.spectral_anomaly_score * 100).toFixed(1)}%</span>
                    </div>
                  )}
                  {item2.voice_cloning_score !== null && (
                    <div className="flex justify-between py-1 border-b border-white/5">
                      <span className="text-slate-400">Voice Synthesis Score</span>
                      <span className="font-semibold text-slate-200">{(item2.voice_cloning_score * 100).toFixed(1)}%</span>
                    </div>
                  )}
                </div>
              </div>

              <div className="pt-2 text-[11px] text-slate-500">
                Model: {item2.model_name || "DualPath DeepGuard Model"}
              </div>
            </div>
          </div>

          {/* Indicator Cross-Analysis */}
          <div className="rounded-2xl border border-white/10 bg-slate-900/60 p-6 space-y-4">
            <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
              <Layers size={18} className="text-violet-400" />
              Forensic Indicator Cross-Correlation
            </h3>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
              {/* Common Indicators */}
              <div className="p-4 rounded-xl bg-slate-950/60 border border-white/5">
                <p className="text-xs font-semibold text-violet-400 mb-2">
                  Correlated Indicators ({comp.common_indicators.length})
                </p>
                {comp.common_indicators.length === 0 ? (
                  <p className="text-xs text-slate-500 italic">No shared anomaly indicators.</p>
                ) : (
                  <div className="space-y-1.5">
                    {comp.common_indicators.map((ind: string, i: number) => (
                      <span key={i} className="block text-xs bg-white/5 px-2.5 py-1 rounded text-slate-200 font-mono">
                        {ind}
                      </span>
                    ))}
                  </div>
                )}
              </div>

              {/* Unique to Item 1 */}
              <div className="p-4 rounded-xl bg-slate-950/60 border border-white/5">
                <p className="text-xs font-semibold text-violet-300 mb-2">
                  Exclusive to Specimen A ({comp.item1_unique_indicators.length})
                </p>
                {comp.item1_unique_indicators.length === 0 ? (
                  <p className="text-xs text-slate-500 italic">None</p>
                ) : (
                  <div className="space-y-1.5">
                    {comp.item1_unique_indicators.map((ind: string, i: number) => (
                      <span key={i} className="block text-xs bg-violet-500/10 border border-violet-500/20 px-2.5 py-1 rounded text-violet-300 font-mono">
                        {ind}
                      </span>
                    ))}
                  </div>
                )}
              </div>

              {/* Unique to Item 2 */}
              <div className="p-4 rounded-xl bg-slate-950/60 border border-white/5">
                <p className="text-xs font-semibold text-sky-300 mb-2">
                  Exclusive to Specimen B ({comp.item2_unique_indicators.length})
                </p>
                {comp.item2_unique_indicators.length === 0 ? (
                  <p className="text-xs text-slate-500 italic">None</p>
                ) : (
                  <div className="space-y-1.5">
                    {comp.item2_unique_indicators.map((ind: string, i: number) => (
                      <span key={i} className="block text-xs bg-sky-500/10 border border-sky-500/20 px-2.5 py-1 rounded text-sky-300 font-mono">
                        {ind}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
