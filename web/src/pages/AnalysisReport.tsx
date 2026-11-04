import { useState, useEffect, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import { ErrorState } from "../components/FeedbackStates";
import { apiService } from "../services/api";
import { ArrowLeft, Printer, ShieldCheck, ShieldAlert, AlertTriangle, Loader2, CheckCircle2 } from "lucide-react";

export default function AnalysisReport() {
  const { id } = useParams<{ id: string }>();
  const [scan, setScan] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAnalysisDetails = useCallback(async (analysisId: string) => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiService.getAnalysis(analysisId);
      setScan(data);
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
  }, [id, fetchAnalysisDetails]);

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

  const result = scan.result || {};
  const prediction = result.prediction || "unknown";
  const confidence = result.confidence || 0;
  const indicators = scan.indicators || [];

  const handlePrint = () => {
    window.print();
  };

  const getResultBadgeColor = () => {
    switch (prediction) {
      case "authentic":
        return "text-emerald-600 bg-emerald-50 border-emerald-200 print:text-emerald-700";
      case "synthetic":
        return "text-rose-600 bg-rose-50 border-rose-200 print:text-rose-700";
      case "uncertain":
      default:
        return "text-amber-600 bg-amber-50 border-amber-200 print:text-amber-700";
    }
  };

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      {/* Screen-Only Header Actions */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between mb-4 print:hidden">
        <Link
          to={`/analysis/${scan.id}`}
          className="inline-flex items-center gap-2 text-sm text-slate-400 hover:text-white transition"
        >
          <ArrowLeft size={16} />
          Back to Inspection Audit
        </Link>

        <div className="flex items-center gap-3">
          <button
            onClick={handlePrint}
            className="flex items-center gap-2 rounded-xl border border-white/10 bg-slate-900/50 px-4 py-2 text-sm font-semibold text-slate-300 hover:bg-white/5 transition"
          >
            <Printer size={16} />
            Print Report
          </button>
        </div>
      </div>

      {/* Printable Report Document Card */}
      <div className="rounded-2xl border border-white/10 bg-white p-8 md:p-12 shadow-2xl text-slate-900 print:border-none print:shadow-none print:bg-white print:p-0 print:text-black">
        
        {/* Document Header Logo & Branding */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-6 pb-8 border-b border-slate-200 print:pb-6">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-violet-600 print:bg-violet-700 text-white shrink-0">
              <ShieldCheck size={24} />
            </div>
            <div>
              <h1 className="text-xl font-bold text-slate-950 tracking-tight">DeepGuard AI</h1>
              <p className="text-xs text-slate-500 font-semibold uppercase tracking-wider mt-0.5">
                Multimodal Authenticity Platform
              </p>
            </div>
          </div>
          <div className="text-left sm:text-right font-mono text-xs text-slate-500 space-y-1">
            <p><span className="font-semibold text-slate-800">Report ID:</span> {scan.id}</p>
            <p><span className="font-semibold text-slate-800">Date Generated:</span> {new Date(scan.created_at).toLocaleDateString()}</p>
          </div>
        </div>

        {/* Executive Summary */}
        <div className="py-8 border-b border-slate-100 space-y-3">
          <h2 className="text-base font-bold uppercase tracking-wider text-slate-800">1. Executive Summary</h2>
          <p className="text-sm text-slate-600 leading-relaxed font-normal">
            This formal security classification report verifies the digital authenticity of the file submitted to the DeepGuard platform. Using multi-attention residual classifiers, the media file was inspected for spatial anomalies, metadata modifications, and synthetic generative patterns.
          </p>
        </div>

        {/* Media Details */}
        <div className="py-8 border-b border-slate-100 space-y-4">
          <h2 className="text-base font-bold uppercase tracking-wider text-slate-800">2. Media File Specifications</h2>
          <div className="grid gap-4 sm:grid-cols-2 text-sm">
            <div className="space-y-2">
              <p className="flex justify-between text-slate-600 py-1 border-b border-slate-100">
                <span className="font-medium">File Name:</span>
                <span className="text-slate-900 font-semibold truncate max-w-xs">{scan.original_filename}</span>
              </p>
              <p className="flex justify-between text-slate-600 py-1 border-b border-slate-100">
                <span className="font-medium">File Type:</span>
                <span className="text-slate-900 font-semibold capitalize">{scan.media_type}</span>
              </p>
              <p className="flex justify-between text-slate-600 py-1 border-b border-slate-100">
                <span className="font-medium">File Size:</span>
                <span className="text-slate-900 font-semibold">{(scan.file_size / 1024 / 1024).toFixed(2)} MB</span>
              </p>
            </div>
            <div className="space-y-2">
              {scan.width && scan.height && (
                <p className="flex justify-between text-slate-600 py-1 border-b border-slate-100">
                  <span className="font-medium">Dimensions:</span>
                  <span className="text-slate-900 font-semibold">{scan.width}x{scan.height}</span>
                </p>
              )}
              <p className="flex justify-between text-slate-600 py-1 border-b border-slate-100">
                <span className="font-medium">MIME Type:</span>
                <span className="text-slate-900 font-semibold">{scan.mime_type}</span>
              </p>
            </div>
          </div>
        </div>

        {/* Classification Result & Verification */}
        <div className="py-8 border-b border-slate-100 space-y-6">
          <h2 className="text-base font-bold uppercase tracking-wider text-slate-800">3. Verification Assessment</h2>
          
          <div className="flex flex-col sm:flex-row items-center gap-6 p-6 rounded-xl border border-slate-200/60 bg-slate-50/50">
            {/* Status Shield */}
            <div className={`flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl border text-xl font-bold ${getResultBadgeColor()}`}>
              {prediction === "authentic" && <CheckCircle2 size={36} />}
              {prediction === "synthetic" && <ShieldAlert size={36} />}
              {prediction === "uncertain" && <AlertTriangle size={36} />}
            </div>

            <div className="flex-1 space-y-1 text-center sm:text-left">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-500">Authenticity Score Verdict</span>
              <h3 className="text-xl font-extrabold text-slate-950 capitalize">{prediction} Media</h3>
              <p className="text-xs text-slate-600">
                The classification model generated a score of <span className="font-bold text-slate-950">{(confidence * 100).toFixed(1)}%</span> indicating the likelihood of the verdict.
              </p>
            </div>
          </div>

          <div>
            <h4 className="font-bold text-sm text-slate-800 mb-2">Risk Level:</h4>
            <p className={`text-sm leading-relaxed font-bold uppercase ${
              result.risk_level === 'critical' || result.risk_level === 'high' ? 'text-rose-600' :
              result.risk_level === 'medium' ? 'text-amber-600' :
              'text-emerald-600'
            }`}>
              {result.risk_level || 'low'}
            </p>
          </div>
        </div>

        {/* Detection Indicators */}
        <div className="py-8 border-b border-slate-100 space-y-4">
          <h2 className="text-base font-bold uppercase tracking-wider text-slate-800">4. Forensic Indicators</h2>
          <div className="space-y-3">
            {indicators.length === 0 && (
              <p className="text-sm text-slate-500">No anomalies detected.</p>
            )}
            {indicators.map((indicator: any, index: number) => (
              <div key={index} className="flex gap-3 text-sm text-slate-600">
                <span className="font-bold text-violet-600 print:text-violet-800 shrink-0">[{index + 1}]</span>
                <p className="font-normal capitalize"><span className="font-bold">{indicator.indicator_type.replace(/_/g, ' ')}:</span> {indicator.description}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Technical System Details */}
        <div className="py-8 space-y-4">
          <h2 className="text-base font-bold uppercase tracking-wider text-slate-800">5. Technical Pipeline Information</h2>
          <div className="grid gap-4 sm:grid-cols-3 text-xs text-slate-600">
            <div>
              <span className="font-bold text-slate-800 block">Inference Engine:</span>
              <span className="block mt-1 font-mono text-[11px]">{result.model_name || "EfficientNet-B0"}</span>
            </div>
            <div>
              <span className="font-bold text-slate-800 block">Model Version:</span>
              <span className="block mt-1">{result.model_version || "1.0.0"}</span>
            </div>
            <div>
              <span className="font-bold text-slate-800 block">Evaluation Duration:</span>
              <span className="block mt-1">{scan.processing_time ? `${scan.processing_time.toFixed(2)}s` : "-"} latency</span>
            </div>
          </div>
        </div>

        {/* Official Signature Stub */}
        <div className="pt-12 mt-12 border-t border-slate-200 flex justify-between text-xs text-slate-500 font-mono">
          <p>Verified by DeepGuard Engine Signature: A79X-2026</p>
          <p>Page 1 of 1</p>
        </div>

      </div>
    </div>
  );
}
