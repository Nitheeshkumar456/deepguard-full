import { useState, useRef, useEffect } from "react";
import { ShieldCheck, KeyRound, ArrowLeft, Loader2, CheckCircle2, AlertCircle } from "lucide-react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { apiService } from "../services/api";

export default function VerifyOtp() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  
  const email = searchParams.get("email") || "";
  const purpose = searchParams.get("purpose") || "register";

  const [otp, setOtp] = useState<string[]>(Array(6).fill(""));
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [resendTimer, setResendTimer] = useState(30);
  const canResend = resendTimer === 0;
  const inputRefs = useRef<(HTMLInputElement | null)[]>([]);

  useEffect(() => {
    if (resendTimer > 0) {
      const timer = setTimeout(() => setResendTimer((prev) => prev - 1), 1000);
      return () => clearTimeout(timer);
    }
  }, [resendTimer]);

  const handleChange = (index: number, value: string) => {
    if (isNaN(Number(value))) return; // only allow numbers

    const newOtp = [...otp];
    newOtp[index] = value.substring(value.length - 1); // keep only last character
    setOtp(newOtp);
    setError(null);

    // Auto-focus next input
    if (value && index < 5 && inputRefs.current[index + 1]) {
      inputRefs.current[index + 1]?.focus();
    }
  };

  const handleKeyDown = (index: number, e: React.KeyboardEvent<HTMLInputElement>) => {
    // Move to previous on backspace
    if (e.key === "Backspace" && !otp[index] && index > 0 && inputRefs.current[index - 1]) {
      inputRefs.current[index - 1]?.focus();
    }
  };

  const handlePaste = (e: React.ClipboardEvent<HTMLInputElement>) => {
    e.preventDefault();
    const pastedData = e.clipboardData.getData("text").trim();
    if (!/^\d{6}$/.test(pastedData)) {
      setError("Please paste a valid 6-digit numeric code.");
      return;
    }

    const digits = pastedData.split("");
    setOtp(digits);
    setError(null);
    inputRefs.current[5]?.focus();
  };

  const handleResend = async () => {
    if (!canResend) return;
    setLoading(true);
    setError(null);
    
    try {
      await apiService.sendOtp(email, purpose);
      setResendTimer(30);
    } catch (err: any) {
      setError(err.message || "Failed to resend verification code.");
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const code = otp.join("");
    if (code.length < 6) {
      setError("Please enter the complete 6-digit code.");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const data = await apiService.verifyOtp(email, code, purpose);
      setSuccess(true);
      
      setTimeout(() => {
        if (purpose === "register") {
          navigate("/login");
        } else if (purpose === "reset" && data.reset_token) {
          navigate(`/reset-password?email=${encodeURIComponent(email)}&token=${encodeURIComponent(data.reset_token)}`);
        } else {
          navigate("/login");
        }
      }, 1000);
    } catch (err: any) {
      setError(err.message || "Invalid verification code.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-white flex items-center justify-center">
      <div className="mx-auto flex w-full max-w-md flex-col justify-center px-6 py-12">
        
        {/* Branding */}
        <div className="mb-8 text-center">
          <Link to="/" className="inline-flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-violet-600">
              <ShieldCheck size={25} />
            </div>
            <div className="text-left">
              <h1 className="font-bold text-lg leading-none">DeepGuard AI</h1>
              <p className="text-xs text-slate-400 mt-1">
                Multimodal Authenticity Platform
              </p>
            </div>
          </Link>
        </div>

        {/* Form Container */}
        <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-8 shadow-2xl backdrop-blur-md">
          <div className="flex justify-center mb-6">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-violet-600/10 text-violet-400">
              <KeyRound size={24} />
            </div>
          </div>

          <h2 className="text-2xl font-bold text-center">Two-Factor Verification</h2>
          <p className="mt-2 text-sm text-center text-slate-400 leading-relaxed">
            Enter the 6-digit verification code sent to <span className="text-white font-medium block break-all">{email || "your registered email"}</span>
          </p>

          {/* Feedback Messages */}
          {error && (
            <div className="mt-6 flex items-start gap-3 rounded-xl border border-red-500/20 bg-red-500/10 p-4 text-sm text-red-400 animate-pulse">
              <AlertCircle size={18} className="mt-0.5 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {success && (
            <div className="mt-6 flex items-start gap-3 rounded-xl border border-emerald-500/20 bg-emerald-500/10 p-4 text-sm text-emerald-400">
              <CheckCircle2 size={18} className="mt-0.5 shrink-0" />
              <span>Security code verified! Redirecting...</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="mt-8 space-y-6">
            <div className="flex justify-between gap-2" onPaste={handlePaste}>
              {otp.map((digit, index) => (
                <input
                  key={index}
                  ref={(el) => { inputRefs.current[index] = el; }}
                  type="text"
                  inputMode="numeric"
                  pattern="[0-9]*"
                  maxLength={1}
                  value={digit}
                  disabled={loading || success}
                  onChange={(e) => handleChange(index, e.target.value)}
                  onKeyDown={(e) => handleKeyDown(index, e)}
                  className="h-12 w-12 rounded-xl border border-white/10 bg-slate-900/50 text-center text-lg font-semibold text-white outline-none focus:border-violet-500 disabled:opacity-50"
                  aria-label={`Digit ${index + 1} of verification code`}
                />
              ))}
            </div>

            <button
              type="submit"
              disabled={loading || success}
              className="flex w-full items-center justify-center gap-2 rounded-xl bg-violet-600 py-3.5 font-semibold hover:bg-violet-500 transition disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <>
                  <Loader2 size={18} className="animate-spin" />
                  Verifying Code...
                </>
              ) : (
                "Verify Code"
              )}
            </button>
          </form>

          {/* Resend Action */}
          <div className="mt-8 text-center text-sm">
            <p className="text-slate-400">
              Didn't receive the code?{" "}
              {canResend ? (
                <button
                  onClick={handleResend}
                  disabled={loading}
                  className="font-medium text-violet-400 hover:text-violet-300 transition"
                >
                  Resend Code
                </button>
              ) : (
                <span className="text-slate-500 font-medium">
                  Resend in {resendTimer}s
                </span>
              )}
            </p>
          </div>

          <Link
            to="/login"
            className="mt-6 flex items-center justify-center gap-2 text-sm text-slate-400 hover:text-white transition"
          >
            <ArrowLeft size={16} />
            Back to Sign In
          </Link>
        </div>
      </div>
    </div>
  );
}
