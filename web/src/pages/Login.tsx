import { useState } from "react";
import { ShieldCheck, User, Mail, Lock, ArrowRight, Eye, EyeOff, Loader2, AlertCircle, CheckCircle2, KeyRound, RefreshCw } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { apiService } from "../services/api";

export default function Login() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [unverifiedEmail, setUnverifiedEmail] = useState<string | null>(null);
  const [resending, setResending] = useState(false);
  const [resendNotice, setResendNotice] = useState<string | null>(null);

  const handleResendOtp = async () => {
    const target = unverifiedEmail || username.trim();
    if (!target) return;
    setResending(true);
    setResendNotice(null);
    try {
      const res = await apiService.sendOtp(target, "register");
      setResendNotice(res.message || "A fresh OTP verification code has been dispatched to your email.");
    } catch (err: any) {
      setResendNotice(err.message || "Failed to resend verification code. Please try again.");
    } finally {
      setResending(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setUnverifiedEmail(null);
    setResendNotice(null);

    // Validation
    if (!username.trim() || !password) {
      setError("Please enter both username and password.");
      return;
    }

    const trimmed = username.trim();
    const isEmail = trimmed.includes("@");

    if (isEmail) {
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!emailRegex.test(trimmed)) {
        setError("Please enter a valid email address.");
        return;
      }
    } else {
      // Username validation: must be at least 3 characters and contain alphabets/letters
      if (trimmed.length < 3) {
        setError("Username must be at least 3 characters long.");
        return;
      }
      if (!/[a-zA-Z]/.test(trimmed)) {
        setError("Username must contain alphabets and letters.");
        return;
      }
      if (!/^[a-zA-Z0-9_.-]+$/.test(trimmed)) {
        setError("Username can only contain alphabets, letters, numbers, and underscores.");
        return;
      }
    }

    if (password.length < 8) {
      setError("Password must be at least 8 characters long.");
      return;
    }

    setLoading(true);

    try {
      await login(trimmed, password);
      setSuccess(true);
      setTimeout(() => {
        navigate("/dashboard");
      }, 1000);
    } catch (err: any) {
      const errMsg = err.message || "Invalid username/email or password.";
      setError(errMsg);
      if (err.status === 403 || errMsg.toLowerCase().includes("not been verified") || errMsg.toLowerCase().includes("otp")) {
        const match = errMsg.match(/\(([^)]+@[^)]+)\)/);
        const resolved = match ? match[1] : trimmed;
        setUnverifiedEmail(resolved);
      } else {
        setUnverifiedEmail(null);
      }
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
          <h2 className="text-2xl font-bold">Welcome back</h2>
          <p className="mt-2 text-sm text-slate-400">
            Sign in to continue protecting digital trust.
          </p>

          {/* Feedback Messages */}
          {error && (
            <div className="mt-6 rounded-xl border border-red-500/20 bg-red-500/10 p-4 text-sm text-red-400">
              <div className="flex items-start gap-3">
                <AlertCircle size={18} className="mt-0.5 shrink-0" />
                <span className="flex-1 leading-relaxed">{error}</span>
              </div>
              {unverifiedEmail && (
                <div className="mt-4 pt-3 border-t border-red-500/20 flex flex-col gap-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <button
                      type="button"
                      onClick={() => navigate(`/verify-otp?email=${encodeURIComponent(unverifiedEmail)}&purpose=register`)}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-violet-600 hover:bg-violet-500 text-white text-xs font-semibold transition"
                    >
                      <KeyRound size={14} />
                      Enter Verification OTP
                    </button>
                    <button
                      type="button"
                      onClick={handleResendOtp}
                      disabled={resending}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/10 hover:bg-white/20 text-slate-200 text-xs font-medium transition disabled:opacity-50"
                    >
                      {resending ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
                      Resend Code to Email
                    </button>
                  </div>
                  {resendNotice && (
                    <p className="text-xs text-amber-300 mt-1">{resendNotice}</p>
                  )}
                </div>
              )}
            </div>
          )}

          {success && (
            <div className="mt-6 flex items-start gap-3 rounded-xl border border-emerald-500/20 bg-emerald-500/10 p-4 text-sm text-emerald-400">
              <CheckCircle2 size={18} className="mt-0.5 shrink-0" />
              <span>Authentication successful! Accessing platform...</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="mt-8 space-y-5">
            {/* Username or Email */}
            <div>
              <label className="mb-2 block text-sm text-slate-300">
                Username or Email address
              </label>
              <div className="relative">
                {username.includes("@") ? (
                  <Mail size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                ) : (
                  <User size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                )}
                <input
                  type="text"
                  placeholder="Username or you@example.com"
                  value={username}
                  disabled={loading || success}
                  onChange={(e) => setUsername(e.target.value)}
                  className="w-full rounded-xl border border-white/10 bg-slate-900/50 px-10 py-3 text-sm text-white outline-none focus:border-violet-500 disabled:opacity-50"
                  aria-label="Username or Email address"
                  autoComplete="username"
                />
              </div>
              <p className="mt-1.5 text-xs text-slate-500">
                Username must contain alphabets and letters (e.g. user123).
              </p>
            </div>

            {/* Password */}
            <div>
              <div className="mb-2 flex justify-between">
                <label className="text-sm text-slate-300">
                  Password
                </label>
                <Link to="/forgot-password" className="text-xs text-violet-400 hover:text-violet-300 transition">
                  Forgot password?
                </Link>
              </div>
              <div className="relative">
                <Lock size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                <input
                  type={showPassword ? "text" : "password"}
                  placeholder="••••••••"
                  value={password}
                  disabled={loading || success}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full rounded-xl border border-white/10 bg-slate-900/50 px-10 py-3 text-sm text-white outline-none focus:border-violet-500 disabled:opacity-50"
                  aria-label="Password"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 transition"
                  aria-label={showPassword ? "Hide password" : "Show password"}
                >
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={loading || success}
              className="group flex w-full items-center justify-center gap-2 rounded-xl bg-violet-600 py-3.5 font-semibold hover:bg-violet-500 transition disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <>
                  <Loader2 size={18} className="animate-spin" />
                  Signing In...
                </>
              ) : (
                <>
                  Sign In
                  <ArrowRight size={18} className="transition group-hover:translate-x-1" />
                </>
              )}
            </button>
          </form>

          {/* Call to Signup */}
          <p className="mt-7 text-center text-sm text-slate-400">
            Don't have an account?{" "}
            <Link to="/signup" className="font-medium text-violet-400 hover:text-violet-300 transition">
              Create account
            </Link>
          </p>
        </div>

        {/* Back Link */}
        <Link to="/" className="mt-6 text-center text-sm text-slate-500 hover:text-slate-300 transition">
          ← Back to DeepGuard AI
        </Link>

      </div>
    </div>
  );
}