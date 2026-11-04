import { useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import PageHeader from "../components/PageHeader";
import { apiService } from "../services/api";
import { Upload, FileImage, FileVideo, FileAudio, Play, Loader2, XCircle } from "lucide-react";

export default function Analyze() {
  const navigate = useNavigate();
  const [mediaType, setMediaType] = useState<"image" | "video" | "audio">("image");
  const [file, setFile] = useState<File | null>(null);
  const [dragging, setDragging] = useState(false);
  const cancelRef = useRef(false);
  
  // UI States
  const [status, setStatus] = useState<"idle" | "uploading" | "processing" | "failed">("idle");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (status !== "idle" && status !== "failed") return;

    if (e.type === "dragenter" || e.type === "dragover") {
      setDragging(true);
    } else if (e.type === "dragleave") {
      setDragging(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragging(false);
    if (status !== "idle" && status !== "failed") return;
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const handleCancelAnalysis = () => {
    cancelRef.current = true;
    setStatus("idle");
    setErrorMessage(null);
  };

  const pollAnalysis = async (analysisId: number) => {
    if (cancelRef.current) return;
    try {
      const data = await apiService.getAnalysis(analysisId);
      if (cancelRef.current) return;
      if (data.status === "completed") {
        navigate(`/analysis/${analysisId}`);
      } else if (data.status === "failed") {
        setStatus("failed");
        setErrorMessage(data.error_message || "Analysis failed during processing.");
      } else {
        // Continue polling
        setTimeout(() => pollAnalysis(analysisId), 2000);
      }
    } catch (err: any) {
      if (cancelRef.current) return;
      setStatus("failed");
      setErrorMessage(err.message || "Error checking analysis status");
    }
  };

  const handleStartAnalysis = async () => {
    if (!file || status === "uploading" || status === "processing") return;
    
    cancelRef.current = false;
    setStatus("uploading");
    setErrorMessage(null);

    try {
      if (mediaType === "image") {
        const response = await apiService.analyzeImage(file);
        const analysisId = response.analysis_id || response.id;
        if (response.status === "completed" && analysisId) {
          navigate(`/analysis/${analysisId}`);
        } else if (response.status === "failed") {
          setStatus("failed");
          setErrorMessage(response.error_message || "Image analysis failed.");
        } else if (analysisId) {
          setStatus("processing");
          pollAnalysis(analysisId);
        } else {
          setStatus("failed");
          setErrorMessage("Failed to receive analysis ID from server.");
        }
      } else if (mediaType === "video") {
        const response = await apiService.analyzeVideo(file);
        const analysisId = response.analysis_id || response.id;
        if (analysisId) {
          setStatus("processing");
          pollAnalysis(analysisId);
        } else {
          setStatus("failed");
          setErrorMessage("Failed to initialize video analysis.");
        }
      } else if (mediaType === "audio") {
        const response = await apiService.analyzeAudio(file);
        const analysisId = response.analysis_id || response.id;
        if (analysisId) {
          setStatus("processing");
          pollAnalysis(analysisId);
        } else {
          setStatus("failed");
          setErrorMessage("Failed to initialize audio analysis.");
        }
      }
    } catch (err: any) {
      setStatus("failed");
      setErrorMessage(err.message || "An error occurred during upload/analysis.");
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Analyze Media"
        description="Submit images, videos, or audio recordings to analyze authenticity and detect synthetic manipulations."
      />

      {status === "failed" && (
        <div className="flex items-start gap-3 rounded-xl border border-rose-500/20 bg-rose-500/5 p-4 text-sm text-rose-400">
          <XCircle size={18} className="mt-0.5 shrink-0" />
          <div>
            <h4 className="font-semibold">
              {errorMessage?.toLowerCase().includes("audio analysis model is unavailable") || errorMessage?.toLowerCase().includes("audio model")
                ? "Audio Analysis Unavailable"
                : errorMessage?.toLowerCase().includes("session expired") || errorMessage?.toLowerCase().includes("log in")
                ? "Authentication Required"
                : errorMessage?.toLowerCase().includes("too large")
                ? "File Size Limit Exceeded"
                : errorMessage?.toLowerCase().includes("unsupported")
                ? "Unsupported File Format"
                : "Analysis Notice"}
            </h4>
            <p className="mt-1 leading-relaxed">{errorMessage}</p>
          </div>
        </div>
      )}

      {/* Loading Overlay state indication */}
      {(status === "uploading" || status === "processing") && (
        <div className="flex flex-col items-center justify-center p-8 rounded-2xl border border-violet-500/20 bg-violet-500/5">
          <div className="text-center space-y-4 text-violet-400">
            <Loader2 size={40} className="mx-auto animate-spin" />
            <h3 className="font-bold text-lg">
              {status === "uploading" ? "Uploading Media..." : "Processing AI Analysis..."}
            </h3>
            <p className="text-sm text-slate-400 max-w-sm mx-auto">
              {status === "processing" && "This may take a few moments depending on the file size and analysis depth."}
            </p>
            <button
              onClick={handleCancelAnalysis}
              className="mt-2 rounded-xl border border-white/10 px-4 py-2 text-xs font-semibold text-slate-300 hover:bg-white/10 hover:text-white transition"
            >
              Cancel Analysis
            </button>
          </div>
        </div>
      )}

      <div className={`grid gap-6 md:grid-cols-3 ${(status === "uploading" || status === "processing") ? "opacity-50 pointer-events-none" : ""}`}>
        {/* Left Column: Form & Configuration */}
        <div className="md:col-span-2 space-y-6">
          <div className="rounded-2xl border border-white/10 bg-white/[0.01] p-6">
            <h3 className="text-lg font-semibold text-white mb-4">Upload File</h3>
            
            {/* Split Type Selector */}
            <div className="grid grid-cols-3 gap-2 mb-6">
              {(["image", "video", "audio"] as const).map((type) => (
                <button
                  key={type}
                  onClick={() => {
                    setMediaType(type);
                    setFile(null);
                    setErrorMessage(null);
                    if (status === "failed") setStatus("idle");
                  }}
                  className={`flex flex-col items-center gap-2 rounded-xl border py-4 text-sm font-semibold transition ${
                    mediaType === type
                      ? "border-violet-500 bg-violet-500/10 text-white"
                      : "border-white/10 hover:bg-white/5 text-slate-400"
                  }`}
                >
                  {type === "image" && <FileImage size={20} />}
                  {type === "video" && <FileVideo size={20} />}
                  {type === "audio" && <FileAudio size={20} />}
                  <span className="capitalize">{type}</span>
                </button>
              ))}
            </div>

            {mediaType === "audio" && (
              <div className="mb-4 rounded-xl border border-violet-500/20 bg-violet-500/5 p-4 text-xs text-violet-300 leading-relaxed">
                <strong>AASIST Audio Deepfake Engine:</strong> Powered by Graph Attention Networks trained on ASVspoof 2019 benchmarks. Detects synthetic speech, voice cloning, and neural vocoder anomalies across WAV, MP3, M4A, FLAC, and AAC.
              </div>
            )}

            {/* Dropzone area */}
            <div
              onDragEnter={handleDrag}
              onDragOver={handleDrag}
              onDragLeave={handleDrag}
              onDrop={handleDrop}
              className={`relative flex flex-col items-center justify-center rounded-2xl border border-dashed p-12 text-center transition ${
                dragging
                  ? "border-violet-500 bg-violet-500/5"
                  : "border-white/10 bg-slate-900/10 hover:border-white/20"
              }`}
            >
              <input
                type="file"
                id="file-upload"
                onChange={handleFileChange}
                accept={
                  mediaType === "image"
                    ? "image/*"
                    : mediaType === "video"
                    ? "video/*"
                    : "audio/*"
                }
                className="hidden"
              />

              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-violet-600/10 text-violet-400 mb-4">
                <Upload size={24} />
              </div>

              {file ? (
                <div className="flex flex-col items-center">
                  <p className="text-sm font-semibold text-white truncate max-w-xs">{file.name}</p>
                  <p className="text-xs text-slate-500 mt-1">{(file.size / (1024 * 1024)).toFixed(2)} MB</p>
                  
                  {mediaType === "audio" && (
                    <div className="mt-3 w-full max-w-xs">
                      <audio controls className="w-full h-8" src={URL.createObjectURL(file)} />
                    </div>
                  )}

                  <button
                    onClick={() => setFile(null)}
                    className="mt-4 text-xs font-semibold text-rose-400 hover:text-rose-300 transition"
                  >
                    Remove File
                  </button>
                </div>
              ) : (
                <label htmlFor="file-upload" className="cursor-pointer">
                  <span className="text-sm font-semibold text-violet-400 hover:text-violet-300">
                    Click to upload
                  </span>{" "}
                  <span className="text-sm text-slate-400">or drag and drop</span>
                  <p className="text-xs text-slate-500 mt-2">
                    Supports formats: {
                      mediaType === "image"
                        ? "PNG, JPG, WEBP"
                        : mediaType === "video"
                        ? "MP4, MOV, WEBM"
                        : "MP3, WAV, FLAC, AAC, M4A"
                    } (Max 50MB)
                  </p>
                </label>
              )}
            </div>
          </div>
        </div>

        {/* Right Column: Settings & Model Choice */}
        <div className="space-y-6">
          <div className="rounded-2xl border border-white/10 bg-white/[0.01] p-6 space-y-6">
            <div>
              <h3 className="text-sm font-bold uppercase tracking-wider text-slate-500 mb-3">Model Selection</h3>
              <select className="w-full rounded-xl border border-white/10 bg-slate-900 px-4 py-3 text-sm text-slate-300 outline-none focus:border-violet-500">
                <option value="resnet">ResNet50-DualAttn (Standard)</option>
                <option value="vit">ViT-L-Base (Deepfake Video)</option>
                <option value="audio-lstm">AudioLSTM-Spec (Speech Manipulation)</option>
              </select>
            </div>

            <div>
              <h3 className="text-sm font-bold uppercase tracking-wider text-slate-500 mb-3">Analysis Depth</h3>
              <div className="space-y-3">
                <label className="flex items-center gap-3 text-sm text-slate-300 cursor-pointer">
                  <input type="radio" name="depth" defaultChecked className="accent-violet-600" />
                  Quick Scan (Low latency, metadata evaluation)
                </label>
                <label className="flex items-center gap-3 text-sm text-slate-300 cursor-pointer">
                  <input type="radio" name="depth" className="accent-violet-600" />
                  Deep Frame Analysis (Thorough facial check)
                </label>
              </div>
            </div>

            <button
              disabled={!file || status === "uploading" || status === "processing"}
              onClick={handleStartAnalysis}
              className="flex w-full items-center justify-center gap-2 rounded-xl bg-violet-600 py-3.5 font-semibold hover:bg-violet-500 transition disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Play size={16} />
              Start Analysis
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
