import { useState } from "react";
import { ShieldCheck, User, Mail, Lock, ArrowRight, Eye, EyeOff, Loader2, AlertCircle, CheckCircle2 } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { apiService } from "../services/api";

export default function Signup() {
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  // Password checks computed directly
  const checks = {
    length: password.length >= 8,
    lower: /[a-z]/.test(password),
    upper: /[A-Z]/.test(password),
    number: /\d/.test(password),
    special: /[^A-Za-z0-9]/.test(password),
  };

  const allChecksPassed = Object.values(checks).every(Boolean);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    // Validation
    if (!name || !email || !password) {
      setError("Please fill in all fields.");
      return;
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      setError("Please enter a valid email address.");
      return;
    }

    if (!allChecksPassed) {
      setError("Please satisfy all password complexity rules.");
      return;
    }

    setLoading(true);

    try {
      await apiService.register(name, email, password);
      setSuccess(true);
      
      // Navigate to OTP verification page to complete signup
      setTimeout(() => {
        navigate(`/verify-otp?email=${encodeURIComponent(email)}&purpose=register`);
      }, 1000);
    } catch (err: any) {
      setError(err.message || "Registration failed. Please try again.");
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
          <h2 className="text-2xl font-bold">Create your account</h2>
          <p className="mt-2 text-sm text-slate-400">
            Start detecting synthetic media with DeepGuard AI.
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
              <span>Account created! Sending verification code...</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="mt-8 space-y-5">
            {/* Full Name */}
            <div>
              <label className="mb-2 block text-sm text-slate-300">
                Full name
              </label>
              <div className="relative">
                <User size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                <input
                  type="text"
                  placeholder="Your name"
                  value={name}
                  disabled={loading || success}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full rounded-xl border border-white/10 bg-slate-900/50 px-10 py-3 text-sm text-white outline-none focus:border-violet-500 disabled:opacity-50"
                  aria-label="Full name"
                />
              </div>
            </div>

            {/* Email */}
            <div>
              <label className="mb-2 block text-sm text-slate-300">
                Email address
              </label>
              <div className="relative">
                <Mail size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                <input
                  type="email"
                  placeholder="you@example.com"
                  value={email}
                  disabled={loading || success}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full rounded-xl border border-white/10 bg-slate-900/50 px-10 py-3 text-sm text-white outline-none focus:border-violet-500 disabled:opacity-50"
                  aria-label="Email address"
                />
              </div>
            </div>

            {/* Password */}
            <div>
              <label className="mb-2 block text-sm text-slate-300">
                Password
              </label>
              <div className="relative">
                <Lock size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                <input
                  type={showPassword ? "text" : "password"}
                  placeholder="Create a strong password"
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

            {/* Password Complexity checklist */}
            <div className="rounded-xl border border-white/5 bg-slate-900/20 p-4 space-y-2 text-xs text-slate-400">
              <p className="font-semibold text-slate-300 mb-1">Complexity Requirements:</p>
              <div className="flex items-center gap-2">
                <div className={`h-1.5 w-1.5 rounded-full ${checks.length ? "bg-emerald-500" : "bg-slate-700"}`} />
                <span className={checks.length ? "text-emerald-400" : ""}>At least 8 characters</span>
              </div>
              <div className="flex items-center gap-2">
                <div className={`h-1.5 w-1.5 rounded-full ${checks.lower ? "bg-emerald-500" : "bg-slate-700"}`} />
                <span className={checks.lower ? "text-emerald-400" : ""}>One lowercase letter</span>
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

            {/* Submit Button */}
            <button
              type="submit"
              disabled={loading || success}
              className="group flex w-full items-center justify-center gap-2 rounded-xl bg-violet-600 py-3.5 font-semibold hover:bg-violet-500 transition disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <>
                  <Loader2 size={18} className="animate-spin" />
                  Creating Account...
                </>
              ) : (
                <>
                  Create Account
                  <ArrowRight size={18} className="transition group-hover:translate-x-1" />
                </>
              )}
            </button>
          </form>

          {/* Call to Login */}
          <p className="mt-7 text-center text-sm text-slate-400">
            Already have an account?{" "}
            <Link to="/login" className="font-medium text-violet-400 hover:text-violet-300 transition">
              Sign in
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