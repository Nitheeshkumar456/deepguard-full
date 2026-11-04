import { useState } from "react";
import { ShieldCheck, Mail, Lock, ArrowRight, Eye, EyeOff, Loader2, AlertCircle, CheckCircle2 } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Login() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    // Validation
    if (!email || !password) {
      setError("Please enter both email and password.");
      return;
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      setError("Please enter a valid email address.");
      return;
    }

    if (password.length < 8) {
      setError("Password must be at least 8 characters long.");
      return;
    }

    setLoading(true);

    try {
      await login(email, password);
      setSuccess(true);
      setTimeout(() => {
        navigate("/dashboard");
      }, 1000);
    } catch (err: any) {
      setError(err.message || "Invalid email or password.");
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
            <div className="mt-6 flex items-start gap-3 rounded-xl border border-red-500/20 bg-red-500/10 p-4 text-sm text-red-400 animate-pulse">
              <AlertCircle size={18} className="mt-0.5 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {success && (
            <div className="mt-6 flex items-start gap-3 rounded-xl border border-emerald-500/20 bg-emerald-500/10 p-4 text-sm text-emerald-400">
              <CheckCircle2 size={18} className="mt-0.5 shrink-0" />
              <span>Authentication successful! Accessing platform...</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="mt-8 space-y-5">
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