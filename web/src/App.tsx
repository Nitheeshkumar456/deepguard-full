import { BrowserRouter, Routes, Route, Link, Navigate } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import ProtectedRoute from "./components/ProtectedRoute";
import GuestRoute from "./components/GuestRoute";
import Login from "./pages/Login";
import Signup from "./pages/Signup";
import ForgotPassword from "./pages/ForgotPassword";
import ResetPassword from "./pages/ResetPassword";
import VerifyOtp from "./pages/VerifyOtp";
import DashboardLayout from "./components/DashboardLayout";
import Dashboard from "./pages/Dashboard";
import Analyze from "./pages/Analyze";
import History from "./pages/History";
import Notifications from "./pages/Notifications";
import Profile from "./pages/Profile";
import Settings from "./pages/Settings";
import Subscription from "./pages/Subscription";
import Help from "./pages/Help";
import AnalysisDetails from "./pages/AnalysisDetails";
import AnalysisReport from "./pages/AnalysisReport";
import Cases from "./pages/Cases";
import CaseDetails from "./pages/CaseDetails";
import CompareMedia from "./pages/CompareMedia";
import { ShieldCheck, ScanSearch, LockKeyhole, ArrowRight } from "lucide-react";

// Landing Page Component
function Home() {
  return (
    <div className="min-h-screen bg-slate-950 text-white">
      {/* Navbar */}
      <nav className="border-b border-white/10">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-5">
          <Link to="/" className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-violet-600">
              <ShieldCheck size={24} />
            </div>
            <div>
              <h1 className="text-lg font-bold">DeepGuard AI</h1>
              <p className="text-xs text-slate-400">
                Multimodal Authenticity Platform
              </p>
            </div>
          </Link>

          <div className="hidden items-center gap-8 md:flex">
            <a href="#features" className="text-sm text-slate-300 hover:text-white transition">
              Features
            </a>
            <a href="#security" className="text-sm text-slate-300 hover:text-white transition">
              Security
            </a>
            <a href="#about" className="text-sm text-slate-300 hover:text-white transition">
              About
            </a>
            <Link 
              to="/login" 
              className="rounded-lg border border-white/15 px-5 py-2 text-sm hover:bg-white/10 transition"
            >
              Sign In
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <main>
        <section className="relative overflow-hidden">
          <div className="absolute left-1/2 top-20 h-96 w-96 -translate-x-1/2 rounded-full bg-violet-600/20 blur-3xl" />

          <div className="relative mx-auto max-w-7xl px-6 py-28 text-center">
            <div className="mx-auto mb-6 flex w-fit items-center gap-2 rounded-full border border-violet-500/30 bg-violet-500/10 px-4 py-2 text-sm text-violet-300 animate-pulse">
              <ScanSearch size={16} />
              AI-Powered Authenticity Detection
            </div>

            <h2 className="mx-auto max-w-4xl text-5xl font-bold leading-tight tracking-tight md:text-7xl">
              Detect Synthetic Media.
              <span className="block text-violet-400">
                Protect Digital Trust.
              </span>
            </h2>

            <p className="mx-auto mt-7 max-w-2xl text-lg leading-8 text-slate-400">
              DeepGuard AI analyzes images, videos and audio to identify
              deepfakes, synthetic content and potential authenticity threats.
            </p>

            <div className="mt-10 flex flex-col justify-center gap-4 sm:flex-row">
              <Link
                to="/login"
                className="group flex items-center justify-center gap-2 rounded-xl bg-violet-600 px-7 py-4 font-semibold transition hover:bg-violet-500"
              >
                Start Analysis
                <ArrowRight
                  size={18}
                  className="transition group-hover:translate-x-1"
                />
              </Link>

              <a 
                href="#features" 
                className="flex items-center justify-center rounded-xl border border-white/15 px-7 py-4 font-semibold text-slate-200 hover:bg-white/10 transition"
              >
                Learn More
              </a>
            </div>
          </div>
        </section>

        {/* Features */}
        <section id="features" className="border-t border-white/10 bg-slate-900/60">
          <div className="mx-auto max-w-7xl px-6 py-24">
            <div className="mb-14 text-center">
              <p className="text-sm font-semibold uppercase tracking-widest text-violet-400">
                Capabilities
              </p>
              <h3 className="mt-3 text-3xl font-bold md:text-4xl">
                Multimodal AI Protection
              </h3>
              <p className="mx-auto mt-4 max-w-2xl text-slate-400">
                Analyze multiple types of digital media through a unified
                authenticity platform.
              </p>
            </div>

            <div className="grid gap-6 md:grid-cols-3">
              <FeatureCard
                icon={<ScanSearch size={24} />}
                title="Image Detection"
                description="Analyze images for synthetic patterns, manipulation and AI-generated content."
              />
              <FeatureCard
                icon={<ShieldCheck size={24} />}
                title="Video Detection"
                description="Examine video frames and identify suspicious visual and temporal patterns."
              />
              <FeatureCard
                icon={<LockKeyhole size={24} />}
                title="Audio Detection"
                description="Analyze voice recordings for synthetic speech and manipulation indicators."
              />
            </div>
          </div>
        </section>

        {/* Security */}
        <section id="security" className="border-t border-white/10">
          <div className="mx-auto max-w-5xl px-6 py-24 text-center">
            <LockKeyhole className="mx-auto text-violet-400" size={42} />
            <h3 className="mt-6 text-3xl font-bold">
              Built With Security in Mind
            </h3>
            <p className="mx-auto mt-5 max-w-2xl leading-7 text-slate-400">
              DeepGuard AI is designed around secure authentication,
              protected media processing and privacy-conscious architecture.
            </p>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-white/10">
        <div className="mx-auto flex max-w-7xl flex-col gap-3 px-6 py-8 text-sm text-slate-500 md:flex-row md:items-center md:justify-between">
          <p>© 2026 DeepGuard AI</p>
          <p>Multimodal Authenticity Platform</p>
        </div>
      </footer>
    </div>
  );
}

// Feature Card Component
function FeatureCard({
  icon,
  title,
  description,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
}) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-7 transition hover:border-violet-500/40 hover:bg-white/[0.05]">
      <div className="mb-5 flex h-12 w-12 items-center justify-center rounded-xl bg-violet-500/10 text-violet-400">
        {icon}
      </div>
      <h4 className="text-xl font-semibold">{title}</h4>
      <p className="mt-3 leading-7 text-slate-400">{description}</p>
    </div>
  );
}

// Main App Router Config
export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Main Routes */}
          <Route path="/" element={<Home />} />
          
          {/* Guest Only Routes */}
          <Route element={<GuestRoute />}>
            <Route path="/login" element={<Login />} />
            <Route path="/signup" element={<Signup />} />
            <Route path="/forgot-password" element={<ForgotPassword />} />
            <Route path="/reset-password" element={<ResetPassword />} />
            <Route path="/verify-otp" element={<VerifyOtp />} />
          </Route>

          {/* Authenticated Dashboard Console Routes */}
          <Route element={<ProtectedRoute />}>
            <Route element={<DashboardLayout />}>
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/analyze" element={<Analyze />} />
              <Route path="/history" element={<History />} />
              <Route path="/analysis/:id" element={<AnalysisDetails />} />
              <Route path="/report/:id" element={<AnalysisReport />} />
              <Route path="/cases" element={<Cases />} />
              <Route path="/cases/:id" element={<CaseDetails />} />
              <Route path="/compare" element={<CompareMedia />} />
              <Route path="/notifications" element={<Notifications />} />
              <Route path="/profile" element={<Profile />} />
              <Route path="/settings" element={<Settings />} />
              <Route path="/subscription" element={<Subscription />} />
              <Route path="/help" element={<Help />} />
            </Route>
          </Route>

          {/* Fallbacks */}
          <Route path="/detect" element={<Navigate to="/analyze" replace />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}