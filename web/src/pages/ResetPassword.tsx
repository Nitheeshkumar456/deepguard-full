import { useState } from "react";
import { ShieldCheck, Lock, Eye, EyeOff, Loader2, CheckCircle2, AlertCircle } from "lucide-react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { apiService } from "../services/api";

export default function ResetPassword() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const email = searchParams.get("email") || "";
  const token = searchParams.get("token") || "";

  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  // Password strength checklist states computed directly
  const checks = {
    length: password.length >= 8,
    number: /\d/.test(password),
    upper: /[A-Z]/.test(password),
    special: /[^A-Za-z0-9]/.test(password),
  };

  const allChecksPassed = Object.values(checks).every(Boolean);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!email || !token) {
      setError("Invalid password reset request context parameters.");
      return;
    }

    if (!password || !confirmPassword) {
      setError("Please fill in all fields.");
      return;
    }

    if (!allChecksPassed) {
      setError("Please satisfy all password complexity rules.");
      return;
    }

    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setLoading(true);

    try {
      await apiService.resetPassword(email, token, password);
      setSuccess(true);
      setTimeout(() => {
        navigate("/login");
      }, 1500);
    } catch (err: any) {
      setError(err.message || "Failed to reset password.");
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
          <h2 className="text-2xl font-bold">Set new password</h2>
          <p className="mt-2 text-sm text-slate-400 leading-relaxed">
            Please choose a strong, unique password that you haven't used elsewhere.
          </p>

          {/* Feedback Messages */}
          {error && (
            <div className="mt-6 flex items-start gap-3 rounded-xl border border-red-500/20 bg-red-500/10 p-4 text-sm text-red-400 animate-pulse">
              <AlertCircle size={18} className="mt-0.5 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {(!email || !token) && (
            <div className="mt-6 flex items-start gap-3 rounded-xl border border-amber-500/20 bg-amber-500/10 p-4 text-sm text-amber-400">
              <AlertCircle size={18} className="mt-0.5 shrink-0" />
              <span>Missing reset link token arguments. Please request a new code from the forgot password page.</span>
            </div>
          )}

          {success && (
            <div className="mt-6 flex items-start gap-3 rounded-xl border border-emerald-500/20 bg-emerald-500/10 p-4 text-sm text-emerald-400">
              <CheckCircle2 size={18} className="mt-0.5 shrink-0" />
              <span>Password reset successfully! Redirecting to Sign In...</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="mt-8 space-y-5">
            {/* New Password */}
            <div>
              <label className="mb-2 block text-sm text-slate-300">New Password</label>
              <div className="relative">
                <Lock size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                <input
                  type={showPassword ? "text" : "password"}
                  placeholder="••••••••"
                  value={password}
                  disabled={loading || success || !email || !token}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full rounded-xl border border-white/10 bg-slate-900/50 px-10 py-3 text-sm text-white outline-none focus:border-violet-500 disabled:opacity-50"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
                >
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
            </div>

            {/* Password Validation Checklist */}
            <div className="rounded-xl border border-white/5 bg-slate-900/20 p-4 space-y-2 text-xs text-slate-400">
              <p className="font-semibold text-slate-300 mb-1">Complexity Requirements:</p>
              <div className="flex items-center gap-2">
                <div className={`h-1.5 w-1.5 rounded-full ${checks.length ? "bg-emerald-500" : "bg-slate-700"}`} />
                <span className={checks.length ? "text-emerald-400" : ""}>At least 8 characters</span>
              </div>
              <div className="flex items-center gap-2">
                <div className={`h-1.5 w-1.5 rounded-full ${checks.upper ? "bg-emerald-500" : "bg-slate-700"}`} />
                <span className={checks.upper ? "text-emerald-400" : ""}>One uppercase letter</span>
              </div>
              <div className="flex items-center gap-2">
                <div className={`h-1.5 w-1.5 rounded-full ${checks.number ? "bg-emerald-500" : "bg-slate-700"}`} />
                <span className={checks.number ? "text-emerald-400" : ""}>One numeric digit</span>
              </div>
              <div className="flex items-center gap-2">
                <div className={`h-1.5 w-1.5 rounded-full ${checks.special ? "bg-emerald-500" : "bg-slate-700"}`} />
                <span className={checks.special ? "text-emerald-400" : ""}>One special character</span>
              </div>
            </div>

            {/* Confirm Password */}
            <div>
              <label className="mb-2 block text-sm text-slate-300">Confirm New Password</label>
              <div className="relative">
                <Lock size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                <input
                  type={showConfirmPassword ? "text" : "password"}
                  placeholder="••••••••"
                  value={confirmPassword}
                  disabled={loading || success || !email || !token}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  className="w-full rounded-xl border border-white/10 bg-slate-900/50 px-10 py-3 text-sm text-white outline-none focus:border-violet-500 disabled:opacity-50"
                />
                <button
                  type="button"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
                >
                  {showConfirmPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading || success || !email || !token}
              className="flex w-full items-center justify-center gap-2 rounded-xl bg-violet-600 py-3.5 font-semibold hover:bg-violet-500 transition disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <>
                  <Loader2 size={18} className="animate-spin" />
                  Updating Password...
                </>
              ) : (
                "Reset Password"
              )}
            </button>
          </form>

          <Link
            to="/login"
            className="mt-6 flex items-center justify-center gap-2 text-sm text-slate-400 hover:text-white transition"
          >
            Cancel and Return
          </Link>
        </div>
      </div>
    </div>
  );
}
