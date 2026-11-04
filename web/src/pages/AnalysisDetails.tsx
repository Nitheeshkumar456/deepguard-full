import { useState, useEffect, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import PageHeader from "../components/PageHeader";
import { ErrorState } from "../components/FeedbackStates";
import { apiService } from "../services/api";
import {
  ArrowLeft,
  FileText,
  FileImage,
  FileVideo,
  FileAudio,
  Sparkles,
  Loader2,
  Flame,
  Layers,
  Download,
  Info,
  Sliders,
  Eye,
  AlertTriangle,
} from "lucide-react";
import { syncWebSocket } from "../services/websocket";

export default function AnalysisDetails() {
  const { id } = useParams<{ id: string }>();
  const [scan, setScan] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Tabs: overview | heatmap | indicators | metadata
  const [activeTab, setActiveTab] = useState<"overview" | "heatmap" | "indicators" | "metadata" | "localization">("overview");

  // Heatmap viewer state
  const [heatmapMode, setHeatmapMode] = useState<"blend" | "split" | "original" | "heatmap">("blend");
  const [opacity, setOpacity] = useState<number>(0.55);
  const [selectedVideoFrame, setSelectedVideoFrame] = useState<number>(0);
  const [originalBlobUrl, setOriginalBlobUrl] = useState<string | null>(null);
  const [heatmapBlobUrl, setHeatmapBlobUrl] = useState<string | null>(null);
  const [pureHeatmapBlobUrl, setPureHeatmapBlobUrl] = useState<string | null>(null);
  const [heatmapLoading, setHeatmapLoading] = useState(false);
  const [heatmapError, setHeatmapError] = useState<string | null>(null);

  const fetchAnalysisDetails = useCallback(async function pollAnalysis(analysisId: string) {
    setLoading(true);
    setError(null);
    try {
      const data = await apiService.getAnalysis(analysisId);
      setScan(data);
      
      // If it's still processing, keep polling
      if (data.status === "processing" || data.status === "queued") {
        setTimeout(() => pollAnalysis(analysisId), 2000);
      }
    } catch (err: any) {
      setError(err.message || "Failed to load analysis details.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (id) {
      fetchAnalysisDetails(id);
    }

    const numId = Number(id);
    const unsubCompleted = syncWebSocket.subscribe("analysis.completed", (detail) => {
      if (detail && detail.id === numId) {
        setScan(detail);
        setLoading(false);
      }
    });

    const unsubFailed = syncWebSocket.subscribe("analysis.failed", (failData) => {
      if (failData && failData.analysis_id === numId) {
        setScan((prev: any) => (prev ? { ...prev, status: "failed", error_message: failData.error } : prev));
        setLoading(false);
      }
    });

    return () => {
      unsubCompleted();
      unsubFailed();
    };
  }, [id, fetchAnalysisDetails]);

  // Load heatmap media blobs when on heatmap tab or changing video frame
  useEffect(() => {
    if (!scan || scan.status !== "completed" || scan.media_type === "audio") return;
    if (activeTab !== "heatmap" && activeTab !== "overview") return;

    let isMounted = true;
    setHeatmapLoading(true);
    setHeatmapError(null);

    async function loadMediaBlobs() {
      try {
        if (scan.media_type === "image") {
          const [origUrl, heatUrl, pureHeatUrl] = await Promise.all([
            apiService.fetchMediaBlob(`api/analysis/${scan.id}/media`),
            apiService.fetchMediaBlob(`api/analysis/${scan.id}/heatmap?type=overlay`),
            apiService.fetchMediaBlob(`api/analysis/${scan.id}/heatmap?type=heatmap`),
          ]);
          if (isMounted) {
            setOriginalBlobUrl(origUrl);
            setHeatmapBlobUrl(heatUrl);
            setPureHeatmapBlobUrl(pureHeatUrl);
          }
        } else if (scan.media_type === "video") {
          const [origUrl, heatUrl] = await Promise.all([
            apiService.fetchMediaBlob(`api/analysis/${scan.id}/media?frame=${selectedVideoFrame}`),
            apiService.fetchMediaBlob(`api/analysis/${scan.id}/heatmap?frame=${selectedVideoFrame}`),
          ]);
          if (isMounted) {
            setOriginalBlobUrl(origUrl);
            setHeatmapBlobUrl(heatUrl);
            setPureHeatmapBlobUrl(heatUrl);
          }
        } else if (scan.media_type === "audio") {
          const audioUrl = await apiService.fetchMediaBlob(`api/analysis/${scan.id}/media`);
          if (isMounted) {
            setOriginalBlobUrl(audioUrl);
          }
        }
      } catch (err: any) {
        if (isMounted) {
          setHeatmapError(err.message || "Failed to load Grad-CAM visualization.");
        }
      } finally {
        if (isMounted) setHeatmapLoading(false);
      }
    }

    loadMediaBlobs();

    return () => {
      isMounted = false;
    };
  }, [scan, activeTab, selectedVideoFrame]);

  if (loading && !scan) {
    return (
      <div className="flex flex-col items-center justify-center p-12 text-slate-400">
        <Loader2 size={32} className="animate-spin mb-4 text-violet-500" />
        <p>Loading analysis report...</p>
      </div>
    );
  }

  if (error || !scan) {
    return (
      <div className="max-w-xl mx-auto py-12">
        <ErrorState
          title="Analysis Record Not Found"
          description={error || `No scan report matches the identification ID "${id}". Please review your search criteria.`}
          actionLabel="Return to Scan History"
          onAction={() => window.history.back()}
        />
      </div>
    );
  }
  
  if (scan.status === "processing" || scan.status === "queued") {
    return (
      <div className="flex flex-col items-center justify-center p-12 text-slate-400">
        <Loader2 size={48} className="animate-spin mb-6 text-violet-500" />
        <h3 className="text-xl font-bold text-white mb-2">Analysis in Progress</h3>
        <p>Your {scan.media_type} is currently being analyzed by DeepGuard AI...</p>
      </div>
    );
  }

  if (scan.status === "failed") {
    return (
      <div className="max-w-xl mx-auto py-12">
        <ErrorState
          title={scan.error_message?.toLowerCase().includes("audio") ? "Audio Analysis Unavailable" : "Analysis Processing Failed"}
          description={scan.error_message || "The AI inference service encountered an error while processing this file."}
          actionLabel="Return to Scan History"
          onAction={() => window.history.back()}
        />
      </div>
    );
  }

  const result = scan.result || {};
  const prediction = result.prediction || "unknown";
  const confidence = result.confidence || 0;
  const indicators = scan.indicators || [];

  const getStatusColor = () => {
    switch (prediction) {
      case "authentic":
        return "text-emerald-400 border-emerald-500/20 bg-emerald-500/5";
      case "synthetic":
        return "text-rose-400 border-rose-500/20 bg-rose-500/5";
      case "uncertain":
      default:
        return "text-amber-400 border-amber-500/20 bg-amber-500/5";
    }
  };

  const downloadHeatmapImage = () => {
    if (!heatmapBlobUrl) return;
    const a = document.createElement("a");
    a.href = heatmapBlobUrl;
    a.download = `deepguard_gradcam_analysis_${scan.id}${scan.media_type === "video" ? `_frame_${selectedVideoFrame}` : ""}.jpg`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between mb-2">
        <Link
          to="/history"
          className="inline-flex items-center gap-2 text-sm text-slate-400 hover:text-white transition"
        >
          <ArrowLeft size={16} />
          Back to History
        </Link>
      </div>

      <PageHeader
        title={`Scan Audit: #${scan.id}`}
        description={`Authenticity evaluation of ${scan.original_filename} (${scan.media_type.toUpperCase()})`}
        action={
          <div className="flex items-center gap-3">
            {scan.media_type !== "audio" && heatmapBlobUrl && (
              <button
                onClick={downloadHeatmapImage}
                className="flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-4 py-2.5 text-sm font-semibold text-white hover:bg-white/10 transition"
              >
                <Download size={16} />
                Download Heatmap
              </button>
            )}
            <Link
              to={`/report/${scan.id}`}
              className="flex items-center gap-2 rounded-xl bg-violet-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-violet-500 transition"
            >
              <FileText size={16} />
              View PDF Report
            </Link>
          </div>
        }
      />

      {/* Tabs Navigation */}
      <div className="flex items-center gap-2 border-b border-white/10 pb-4">
        <button
          onClick={() => setActiveTab("overview")}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold transition ${
            activeTab === "overview"
              ? "bg-violet-600/20 text-violet-400 border border-violet-500/30"
              : "text-slate-400 hover:text-white hover:bg-white/5"
          }`}
        >
          <Eye size={16} />
          Overview
        </button>

        {scan.media_type !== "audio" && (
          <button
            onClick={() => setActiveTab("heatmap")}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold transition ${
              activeTab === "heatmap"
                ? "bg-violet-600/20 text-violet-400 border border-violet-500/30"
                : "text-slate-400 hover:text-white hover:bg-white/5"
            }`}
          >
            <Flame size={16} className="text-amber-400" />
            Explainable Heatmap (Grad-CAM)
          </button>
        )}

        <button
          onClick={() => setActiveTab("indicators")}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold transition ${
            activeTab === "indicators"
              ? "bg-violet-600/20 text-violet-400 border border-violet-500/30"
              : "text-slate-400 hover:text-white hover:bg-white/5"
          }`}
        >
          <Sparkles size={16} />
          Forensic Indicators ({indicators.length})
        </button>

        <button
          onClick={() => setActiveTab("metadata")}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold transition ${
            activeTab === "metadata"
              ? "bg-violet-600/20 text-violet-400 border border-violet-500/30"
              : "text-slate-400 hover:text-white hover:bg-white/5"
          }`}
        >
          <Layers size={16} />
          Technical Metadata
        </button>


        {/* Manipulation Localization Tab */}
        <button
          onClick={() => setActiveTab("localization")}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold transition ${
            activeTab === "localization"
              ? "bg-violet-600/20 text-violet-400 border border-violet-500/30"
              : "text-slate-400 hover:text-white hover:bg-white/5"
          }`}
        >
          <AlertTriangle size={16} className="text-rose-400" />
          Manipulation Localization
        </button>
      </div>

      {/* ── TAB 1: OVERVIEW ────────────────────────────────────────────────── */}
      {activeTab === "overview" && (
        <div className="grid gap-6 lg:grid-cols-3">
          {/* Left Column: Media Visualizer */}
          <div className="lg:col-span-2 space-y-6">
            <div className="rounded-2xl border border-white/10 bg-white/[0.01] overflow-hidden">
              <div className="border-b border-white/10 bg-slate-950/40 px-6 py-4 flex items-center justify-between">
                <span className="text-sm font-semibold text-white">Media Preview & Attribution</span>
                <span className="text-xs text-slate-500 font-mono">{scan.original_filename}</span>
              </div>

              <div className="flex min-h-[360px] items-center justify-center bg-slate-950/60 p-6 relative">
                {scan.media_type === "image" && (
                  <div className="w-full flex flex-col items-center justify-center space-y-4">
                    {heatmapBlobUrl ? (
                      <div className="relative rounded-xl overflow-hidden border border-white/10 max-h-[380px]">
                        <img
                          src={heatmapBlobUrl}
                          alt="Grad-CAM Heatmap"
                          className="max-h-[380px] w-auto object-contain rounded-xl"
                        />
                        <div className="absolute bottom-3 left-3 bg-black/70 backdrop-blur-md px-3 py-1 rounded-lg text-[11px] font-medium text-amber-300 border border-amber-500/20">
                          Grad-CAM Attention Overlay
                        </div>
                      </div>
                    ) : (
                      <div className="flex flex-col items-center justify-center text-center p-8 rounded-xl border border-white/5 bg-slate-900/40 w-full h-full">
                        <FileImage size={48} className="text-slate-500 mb-4" />
                        <p className="text-sm font-medium text-white">Image Visualizer</p>
                        <p className="text-xs text-slate-500 mt-1">Resolution: {scan.width || "-"}x{scan.height || "-"} | File size: {(scan.file_size / 1024 / 1024).toFixed(2)}MB</p>
                      </div>
                    )}
                  </div>
                )}

                {scan.media_type === "video" && (
                  <div className="w-full flex flex-col items-center justify-center space-y-4">
                    {heatmapBlobUrl ? (
                      <div className="relative rounded-xl overflow-hidden border border-white/10 max-h-[380px]">
                        <img
                          src={heatmapBlobUrl}
                          alt="Video Keyframe Grad-CAM"
                          className="max-h-[380px] w-auto object-contain rounded-xl"
                        />
                        <div className="absolute bottom-3 left-3 bg-black/70 backdrop-blur-md px-3 py-1 rounded-lg text-[11px] font-medium text-amber-300 border border-amber-500/20">
                          Keyframe #{selectedVideoFrame} Grad-CAM Overlay
                        </div>
                      </div>
                    ) : (
                      <div className="flex flex-col items-center justify-center text-center p-8 rounded-xl border border-white/5 bg-slate-900/40 w-full h-full">
                        <FileVideo size={48} className="text-slate-500 mb-4" />
                        <p className="text-sm font-medium text-white">Video Frame Analysis</p>
                        <p className="text-xs text-slate-500 mt-1">File size: {(scan.file_size / 1024 / 1024).toFixed(2)}MB</p>
                      </div>
                    )}
                  </div>
                )}

                {scan.media_type === "audio" && (
                  <div className="flex flex-col items-center justify-center p-8 rounded-xl border border-white/5 bg-slate-900/40 w-full h-full text-center">
                    <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-violet-600/10 text-violet-400 mb-4">
                      <FileAudio size={36} />
                    </div>
                    <p className="text-base font-semibold text-white">{scan.original_filename}</p>
                    <p className="text-xs text-slate-500 mt-1 mb-4">
                      Audio Recording • {(scan.file_size / 1024 / 1024).toFixed(2)} MB
                      {scan.duration_seconds && ` • ${scan.duration_seconds}s`}
                    </p>

                    {originalBlobUrl && (
                      <div className="w-full max-w-md my-4">
                        <audio controls className="w-full" src={originalBlobUrl} />
                      </div>
                    )}

                    <div className="grid grid-cols-2 gap-4 w-full max-w-md mt-2 text-left">
                      <div className="rounded-xl border border-white/5 bg-white/[0.02] p-3">
                        <span className="text-[11px] text-slate-400 block font-medium">Voice Cloning Risk</span>
                        <span className="text-sm font-bold text-rose-400 mt-0.5 block">
                          {result.voice_cloning_score !== undefined && result.voice_cloning_score !== null
                            ? `${(result.voice_cloning_score * 100).toFixed(1)}%`
                            : `${(confidence * 100).toFixed(1)}%`}
                        </span>
                      </div>
                      <div className="rounded-xl border border-white/5 bg-white/[0.02] p-3">
                        <span className="text-[11px] text-slate-400 block font-medium">Spectral Anomaly</span>
                        <span className="text-sm font-bold text-amber-400 mt-0.5 block">
                          {result.spectral_anomaly_score !== undefined && result.spectral_anomaly_score !== null
                            ? `${(result.spectral_anomaly_score * 100).toFixed(1)}%`
                            : "Normal"}
                        </span>
                      </div>
                    </div>

                    <p className="text-[11px] text-slate-500 mt-4 max-w-md leading-relaxed">
                      * AASIST graph attention evaluates raw waveform spectral anomalies and vocoder artifacts. Does not verify individual speaker identity.
                    </p>
                  </div>
                )}
              </div>
            </div>

            {/* Quick Forensic Indicators Summary */}
            <div className="rounded-2xl border border-white/10 bg-white/[0.01] p-6 space-y-4">
              <h3 className="text-lg font-semibold text-white flex items-center gap-2">
                <Sparkles size={18} className="text-violet-400" />
                Key Forensic Indicators
              </h3>
              <ul className="space-y-3 text-sm text-slate-300">
                {indicators.length === 0 && (
                  <li className="text-slate-500">No anomalies detected.</li>
                )}
                {indicators.slice(0, 3).map((indicator: any, index: number) => (
                  <li key={index} className="flex items-start gap-3 p-3 rounded-xl bg-white/[0.01] border border-white/5">
                    <div className={`h-2 w-2 rounded-full shrink-0 mt-2 ${
                      indicator.severity === 'critical' ? 'bg-rose-500' :
                      indicator.severity === 'high' ? 'bg-orange-500' :
                      indicator.severity === 'medium' ? 'bg-amber-500' :
                      indicator.severity === 'low' ? 'bg-blue-400' : 'bg-slate-500'
                    }`} />
                    <div>
                      <span className="font-semibold text-white capitalize mr-2">{indicator.indicator_type.replace(/_/g, ' ')}:</span>
                      <span>{indicator.description}</span>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          </div>

          {/* Right Column: Classification Verdict Gauge */}
          <div className="space-y-6">
            <div className={`rounded-2xl border p-6 text-center space-y-6 ${getStatusColor()}`}>
              <div>
                <span className="text-xs font-bold uppercase tracking-wider text-slate-500">Classification Verdict</span>
                <h3 className="text-2xl font-bold mt-2 capitalize">{prediction}</h3>
              </div>

              {/* Circular Gauge */}
              <div className="relative flex items-center justify-center h-40 w-40 mx-auto">
                <svg className="w-full h-full transform -rotate-90">
                  <circle
                    cx="80"
                    cy="80"
                    r="64"
                    stroke="rgba(255,255,255,0.05)"
                    strokeWidth="8"
                    fill="transparent"
                  />
                  <circle
                    cx="80"
                    cy="80"
                    r="64"
                    stroke="currentColor"
                    strokeWidth="8"
                    fill="transparent"
                    strokeDasharray={402}
                    strokeDashoffset={402 - (402 * confidence)}
                    className="transition-all duration-1000 ease-out"
                  />
                </svg>
                <div className="absolute text-center">
                  <span className="block text-3xl font-extrabold text-white">{(confidence * 100).toFixed(1)}%</span>
                  <span className="text-[10px] text-slate-500 font-semibold uppercase tracking-wider">Confidence</span>
                </div>
              </div>

              <div className="pt-4 border-t border-white/5 text-xs text-slate-400 text-left space-y-2">
                <p className="flex justify-between">
                  <span>Assessment:</span>
                  <span className="text-white font-semibold capitalize">{prediction}</span>
                </p>
                <p className="flex justify-between">
                  <span>Severity Risk:</span>
                  <span className={`font-semibold ${
                    result.risk_level === "critical" || result.risk_level === "high"
                      ? "text-rose-400"
                      : result.risk_level === "medium"
                      ? "text-amber-400"
                      : "text-emerald-400"
                  }`}>
                    {(result.risk_level || "low").toUpperCase()}
                  </span>
                </p>
              </div>
            </div>

            {/* Quick Metrics */}
            <div className="rounded-2xl border border-white/10 bg-white/[0.01] p-6 space-y-4">
              <h3 className="text-sm font-bold uppercase tracking-wider text-slate-500">Inference Metrics</h3>
              <div className="grid grid-cols-2 gap-4 text-xs">
                <div>
                  <span className="text-slate-500">Analysis Engine</span>
                  <span className="text-white font-semibold block mt-1">{result.model_name || "EfficientNet-B0"}</span>
                </div>
                <div>
                  <span className="text-slate-500">Latency</span>
                  <span className="text-white font-semibold block mt-1">{scan.processing_time ? `${(scan.processing_time * 1000).toFixed(0)} ms` : "-"}</span>
                </div>
                <div>
                  <span className="text-slate-500">Real Probability</span>
                  <span className="text-emerald-400 font-semibold block mt-1">
                    {result.face_manipulation_score !== undefined && result.face_manipulation_score !== null
                      ? `${((1 - result.face_manipulation_score) * 100).toFixed(1)}%`
                      : prediction === "authentic"
                      ? `${(confidence * 100).toFixed(1)}%`
                      : `${((1 - confidence) * 100).toFixed(1)}%`}
                  </span>
                </div>
                <div>
                  <span className="text-slate-500">Fake Probability</span>
                  <span className="text-rose-400 font-semibold block mt-1">
                    {result.face_manipulation_score !== undefined && result.face_manipulation_score !== null
                      ? `${(result.face_manipulation_score * 100).toFixed(1)}%`
                      : prediction === "synthetic"
                      ? `${(confidence * 100).toFixed(1)}%`
                      : `${((1 - confidence) * 100).toFixed(1)}%`}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── TAB 2: EXPLAINABLE GRAD-CAM HEATMAP ────────────────────────────── */}
      {activeTab === "heatmap" && scan.media_type !== "audio" && (
        <div className="space-y-6">
          {/* Scientific Context Banner */}
          <div className="flex items-start gap-3 rounded-2xl border border-amber-500/20 bg-amber-500/5 p-5 text-xs text-amber-300 leading-relaxed">
            <Info size={20} className="mt-0.5 shrink-0 text-amber-400" />
            <div>
              <h4 className="font-bold text-sm text-amber-200">Explainable AI & Grad-CAM Attention Attribution</h4>
              <p className="mt-1">
                Warm colors (red, yellow, orange) indicate image regions that contributed more strongly to the model's <strong>{prediction.toUpperCase()}</strong> prediction. This visualization represents the convolutional neural network's attention focus and is not a ground-truth segmentation mask.
              </p>
            </div>
          </div>

          {/* Video Keyframe Selector (if video) */}
          {scan.media_type === "video" && (
            <div className="rounded-2xl border border-white/10 bg-white/[0.01] p-6 space-y-4">
              <h3 className="text-sm font-bold uppercase tracking-wider text-slate-400 flex items-center gap-2">
                <FileVideo size={16} className="text-violet-400" />
                Video Keyframe Selection (5 Bounded Frames)
              </h3>
              <div className="grid grid-cols-5 gap-3">
                {[0, 1, 2, 3, 4].map((fIndex) => (
                  <button
                    key={fIndex}
                    onClick={() => setSelectedVideoFrame(fIndex)}
                    className={`flex flex-col items-center justify-center p-3 rounded-xl border transition ${
                      selectedVideoFrame === fIndex
                        ? "border-violet-500 bg-violet-500/20 text-white shadow-lg shadow-violet-500/10"
                        : "border-white/10 bg-white/[0.02] text-slate-400 hover:bg-white/5 hover:text-white"
                    }`}
                  >
                    <span className="text-xs font-bold">Frame #{fIndex + 1}</span>
                    <span className="text-[10px] text-slate-500 mt-1">Sample {(fIndex * 0.6).toFixed(1)}s</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Controls Bar */}
          <div className="flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-white/10 bg-white/[0.01] p-4">
            {/* Mode Selectors */}
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-slate-400 mr-2 flex items-center gap-1.5">
                <Eye size={14} /> View Mode:
              </span>
              {(["blend", "split", "original", "heatmap"] as const).map((mode) => (
                <button
                  key={mode}
                  onClick={() => setHeatmapMode(mode)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold capitalize transition ${
                    heatmapMode === mode
                      ? "bg-violet-600 text-white"
                      : "bg-white/5 text-slate-400 hover:text-white hover:bg-white/10"
                  }`}
                >
                  {mode === "blend" ? "Interactive Blend" : mode === "split" ? "Side-by-Side" : mode}
                </button>
              ))}
            </div>

            {/* Opacity Slider for Blend Mode */}
            {heatmapMode === "blend" && (
              <div className="flex items-center gap-3">
                <Sliders size={14} className="text-slate-400" />
                <span className="text-xs text-slate-400">Heatmap Opacity:</span>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.05"
                  value={opacity}
                  onChange={(e) => setOpacity(parseFloat(e.target.value))}
                  className="w-32 accent-violet-500 cursor-pointer"
                />
                <span className="text-xs font-mono text-white w-10 text-right">
                  {Math.round(opacity * 100)}%
                </span>
              </div>
            )}
          </div>

          {/* Visualizer Display Area */}
          <div className="rounded-2xl border border-white/10 bg-slate-950/80 p-6 min-h-[460px] flex items-center justify-center relative overflow-hidden">
            {heatmapLoading && (
              <div className="flex flex-col items-center justify-center text-slate-400">
                <Loader2 size={36} className="animate-spin text-violet-500 mb-3" />
                <p className="text-sm">Calculating Grad-CAM gradient activations...</p>
              </div>
            )}

            {heatmapError && (
              <div className="text-center p-8 text-rose-400">
                <AlertTriangle size={32} className="mx-auto mb-2" />
                <p className="text-sm font-semibold">{heatmapError}</p>
              </div>
            )}

            {!heatmapLoading && !heatmapError && originalBlobUrl && (
              <div className="w-full flex items-center justify-center">
                {/* 1. INTERACTIVE BLEND MODE */}
                {heatmapMode === "blend" && (
                  <div className="relative max-h-[500px] rounded-xl overflow-hidden border border-white/10 shadow-2xl">
                    {/* Background Original */}
                    <img
                      src={originalBlobUrl}
                      alt="Original Reference"
                      className="max-h-[500px] w-auto object-contain block"
                    />
                    {/* Foreground Heatmap Overlay */}
                    {heatmapBlobUrl && (
                      <img
                        src={pureHeatmapBlobUrl || heatmapBlobUrl}
                        alt="Grad-CAM Overlay"
                        className="absolute inset-0 w-full h-full object-contain pointer-events-none transition-opacity duration-150"
                        style={{ opacity }}
                      />
                    )}
                    <div className="absolute bottom-3 right-3 bg-black/80 backdrop-blur-md px-3 py-1.5 rounded-lg text-[11px] font-semibold text-white border border-white/10 flex items-center gap-2">
                      <span className="h-2 w-2 rounded-full bg-violet-400 animate-pulse" />
                      Alpha Blend: {Math.round(opacity * 100)}% Heatmap
                    </div>
                  </div>
                )}

                {/* 2. SIDE BY SIDE MODE */}
                {heatmapMode === "split" && (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6 w-full max-w-5xl">
                    <div className="flex flex-col items-center space-y-2">
                      <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Original Source</span>
                      <div className="rounded-xl overflow-hidden border border-white/10 bg-slate-900/50 p-1 w-full flex items-center justify-center">
                        <img
                          src={originalBlobUrl}
                          alt="Original Source"
                          className="max-h-[380px] w-auto object-contain rounded-lg"
                        />
                      </div>
                    </div>
                    <div className="flex flex-col items-center space-y-2">
                      <span className="text-xs font-semibold uppercase tracking-wider text-amber-400">Grad-CAM Activation Map</span>
                      <div className="rounded-xl overflow-hidden border border-amber-500/20 bg-slate-900/50 p-1 w-full flex items-center justify-center">
                        <img
                          src={heatmapBlobUrl || originalBlobUrl}
                          alt="Grad-CAM Heatmap"
                          className="max-h-[380px] w-auto object-contain rounded-lg"
                        />
                      </div>
                    </div>
                  </div>
                )}

                {/* 3. ORIGINAL ONLY */}
                {heatmapMode === "original" && (
                  <div className="relative max-h-[500px] rounded-xl overflow-hidden border border-white/10">
                    <img
                      src={originalBlobUrl}
                      alt="Original Unmodified"
                      className="max-h-[500px] w-auto object-contain rounded-xl"
                    />
                    <div className="absolute bottom-3 left-3 bg-black/70 backdrop-blur-md px-3 py-1 rounded-lg text-xs font-medium text-slate-300">
                      Original Input Image
                    </div>
                  </div>
                )}

                {/* 4. HEATMAP ONLY */}
                {heatmapMode === "heatmap" && heatmapBlobUrl && (
                  <div className="relative max-h-[500px] rounded-xl overflow-hidden border border-amber-500/30">
                    <img
                      src={heatmapBlobUrl}
                      alt="Pure Heatmap Overlay"
                      className="max-h-[500px] w-auto object-contain rounded-xl"
                    />
                    <div className="absolute bottom-3 left-3 bg-black/70 backdrop-blur-md px-3 py-1 rounded-lg text-xs font-medium text-amber-300">
                      Full Grad-CAM Attribution
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Color Scale Legend */}
          <div className="rounded-2xl border border-white/10 bg-white/[0.01] p-6 space-y-3">
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400">Attribution Heatmap Color Interpretation</h4>
            <div className="h-4 w-full rounded-lg bg-gradient-to-r from-blue-600 via-emerald-400 via-amber-400 to-rose-600 shadow-inner" />
            <div className="flex justify-between text-[11px] font-mono text-slate-400">
              <span>Low Model Influence (Blue)</span>
              <span>Moderate Context (Green/Yellow)</span>
              <span>High Evidence Activation (Red)</span>
            </div>
          </div>
        </div>
      )}

      {/* ── TAB 3: MANIPULATION LOCALIZATION (UNAVAILABLE) ────────────────────────────────────── */}
      {activeTab === "localization" && (
        <div className="rounded-2xl border border-amber-500/20 bg-amber-500/5 p-5 text-xs text-amber-300 leading-relaxed">
          <Info size={20} className="mt-0.5 shrink-0 text-amber-400" />
          <h4 className="font-bold text-sm text-amber-200 mt-2">Manipulation Localization</h4>
          <p className="mt-1">
            Pixel-level manipulation localization is currently unavailable because no trained localization model is installed.
          </p>
        </div>
      )}

      {/* ── TAB 3: FORENSIC INDICATORS ────────────────────────────────────── */}
      {activeTab === "indicators" && (
        <div className="rounded-2xl border border-white/10 bg-white/[0.01] p-6 space-y-6">
          <h3 className="text-lg font-semibold text-white flex items-center gap-2">
            <Sparkles size={18} className="text-violet-400" />
            Detailed Forensic Indicators & Artifact Evidence
          </h3>

          <div className="space-y-4">
            {indicators.length === 0 && (
              <div className="p-8 text-center text-slate-500 rounded-xl border border-white/5">
                No specific forensic anomalies detected for this media asset.
              </div>
            )}
            {indicators.map((indicator: any, index: number) => (
              <div
                key={index}
                className="p-4 rounded-xl border border-white/10 bg-white/[0.02] flex items-start gap-4"
              >
                <div className={`p-2 rounded-lg shrink-0 mt-0.5 ${
                  indicator.severity === 'critical' ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20' :
                  indicator.severity === 'high' ? 'bg-orange-500/10 text-orange-400 border border-orange-500/20' :
                  indicator.severity === 'medium' ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20' :
                  'bg-blue-500/10 text-blue-400 border border-blue-500/20'
                }`}>
                  <Sparkles size={16} />
                </div>
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-white capitalize">{indicator.indicator_type.replace(/_/g, ' ')}</span>
                    <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full ${
                      indicator.severity === 'critical' ? 'bg-rose-500/20 text-rose-300' :
                      indicator.severity === 'high' ? 'bg-orange-500/20 text-orange-300' :
                      indicator.severity === 'medium' ? 'bg-amber-500/20 text-amber-300' :
                      'bg-blue-500/20 text-blue-300'
                    }`}>
                      {indicator.severity}
                    </span>
                  </div>
                  <p className="text-sm text-slate-300 leading-relaxed">{indicator.description}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── TAB 4: TECHNICAL METADATA ───────────────────────────────────────── */}
      {activeTab === "metadata" && (
        <div className="rounded-2xl border border-white/10 bg-white/[0.01] p-6 space-y-6">
          <h3 className="text-lg font-semibold text-white flex items-center gap-2">
            <Layers size={18} className="text-violet-400" />
            File & AI Pipeline Technical Specifications
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-sm">
            <div className="p-4 rounded-xl border border-white/5 bg-slate-900/40 space-y-3">
              <h4 className="font-semibold text-slate-300 border-b border-white/5 pb-2">Analysis Engine Specs</h4>
              <p className="flex justify-between"><span className="text-slate-500">Model Architecture:</span><span className="text-white font-mono">{result.model_name || "EfficientNet-B0"}</span></p>
              <p className="flex justify-between"><span className="text-slate-500">Model Version:</span><span className="text-white font-mono">{result.model_version || "1.0.0-trained"}</span></p>
              <p className="flex justify-between"><span className="text-slate-400">High Evidence Activation (Red)</span></p>
              <p className="flex justify-between"><span className="text-slate-500">Inference Device:</span><span className="text-white font-mono">CPU (PyTorch)</span></p>
              <p className="flex justify-between"><span className="text-slate-500">Target Conv Layer:</span><span className="text-white font-mono">features[-1] (1280ch)</span></p>
              <p className="flex justify-between"><span className="text-slate-500">Processing Latency:</span><span className="text-white font-mono">{scan.processing_time ? `${(scan.processing_time * 1000).toFixed(0)} ms` : "-"}</span></p>
            </div>

            <div className="p-4 rounded-xl border border-white/5 bg-slate-900/40 space-y-3">
              <h4 className="font-semibold text-slate-300 border-b border-white/5 pb-2">Asset Parameters</h4>
              <p className="flex justify-between"><span className="text-slate-500">Original Filename:</span><span className="text-white font-mono truncate max-w-xs">{scan.original_filename}</span></p>
              <p className="flex justify-between"><span className="text-slate-500">File Size:</span><span className="text-white font-mono">{(scan.file_size / 1024 / 1024).toFixed(2)} MB</span></p>
              <p className="flex justify-between"><span className="text-slate-500">Media Type:</span><span className="text-white font-mono uppercase">{scan.media_type}</span></p>
              <p className="flex justify-between"><span className="text-slate-500">MIME Type:</span><span className="text-white font-mono">{scan.mime_type || "-"}</span></p>
              <p className="flex justify-between"><span className="text-slate-500">Resolution:</span><span className="text-white font-mono">{scan.width && scan.height ? `${scan.width}x${scan.height}` : "-"}</span></p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

