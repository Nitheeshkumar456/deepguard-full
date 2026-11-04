import { useState } from "react";
import { ShieldCheck, Mail, ArrowLeft, Loader2, AlertCircle, CheckCircle2 } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { apiService } from "../services/api";

export default function ForgotPassword() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    // Validation
    if (!email) {
      setError("Please enter your email address.");
      return;
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      setError("Please enter a valid email address.");
      return;
    }

    setLoading(true);

    try {
      await apiService.forgotPassword(email);
      setSuccess(true);
      
      // Navigate to OTP verification page to enter code
      setTimeout(() => {
        navigate(`/verify-otp?email=${encodeURIComponent(email)}&purpose=reset`);
      }, 1000);
    } catch (err: any) {
      setError(err.message || "Failed to trigger recovery options.");
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
          <h2 className="text-2xl font-bold">Forgot your password?</h2>
          <p className="mt-2 text-sm leading-relaxed text-slate-400">
            Enter your email address and we'll send a 6-digit security code to verify your identity.
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
              <span>Security code sent! Redirecting to verification page...</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="mt-8 space-y-5">
            {/* Email Address */}
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

            {/* Submit Button */}
            <button
              type="submit"
              disabled={loading || success}
              className="flex w-full items-center justify-center gap-2 rounded-xl bg-violet-600 py-3.5 font-semibold hover:bg-violet-500 transition disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <>
                  <Loader2 size={18} className="animate-spin" />
                  Sending Code...
                </>
              ) : (
                "Send Verification Code"
              )}
            </button>
          </form>

          {/* Navigation Links */}
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