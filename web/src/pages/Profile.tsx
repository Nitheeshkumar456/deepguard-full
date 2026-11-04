import { useState, useEffect } from "react";
import PageHeader from "../components/PageHeader";
import { User, Mail, Save, CheckCircle, AlertCircle } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { apiService } from "../services/api";

export default function Profile() {
  const { user, refreshProfile } = useAuth();
  const [name, setName] = useState(user?.name || "");
  const [bio, setBio] = useState(() => localStorage.getItem("dg_user_bio") || "");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ text: string; isError: boolean } | null>(null);

  useEffect(() => {
    if (user?.name) {
      setName(user.name);
    }
  }, [user?.name]);

  const getInitials = () => {
    if (!user || !user.name) return "DG";
    const parts = user.name.split(" ");
    if (parts.length >= 2) {
      return (parts[0][0] + parts[1][0]).toUpperCase();
    }
    return user.name.substring(0, 2).toUpperCase();
  };

  const getRegistrationDate = () => {
    if (!user || !user.created_at) return "Aug 27, 2026";
    try {
      const d = new Date(user.created_at);
      return d.toLocaleDateString("en-US", {
        year: "numeric",
        month: "short",
        day: "numeric",
      });
    } catch {
      return "Aug 27, 2026";
    }
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    setSaving(true);
    setMessage(null);
    try {
      await apiService.updateProfile(name.trim(), (user as any)?.version);
      localStorage.setItem("dg_user_bio", bio);
      await refreshProfile();
      setMessage({ text: "Profile updated successfully.", isError: false });
    } catch (err: any) {
      if (err.status === 409) {
        setMessage({ text: "Conflict: Profile was updated on another client. Refreshing latest...", isError: true });
        await refreshProfile();
      } else {
        setMessage({ text: err.message || "Failed to update profile.", isError: true });
      }
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="My Profile"
        description="Manage your account profile details, credentials, and authentication preferences."
      />

      <div className="grid gap-6 md:grid-cols-3">
        {/* Left Card: Summary */}
        <div className="rounded-2xl border border-white/10 bg-white/[0.01] p-6 text-center space-y-4">
          <div className="mx-auto flex h-20 w-20 items-center justify-center rounded-full bg-violet-600/20 text-violet-400 font-bold border-2 border-violet-500/30 text-2xl">
            {getInitials()}
          </div>
          <div>
            <h3 className="text-lg font-bold text-white">{user?.name || "DeepGuard User"}</h3>
            <p className="text-sm text-slate-500 mt-1">Platform Account</p>
          </div>
          <div className="pt-4 border-t border-white/5 space-y-2 text-left text-xs text-slate-400">
            <p className="flex justify-between">
              <span>Account Status:</span>
              <span className={user?.is_active ? "text-emerald-400 font-semibold" : "text-rose-400 font-semibold"}>
                {user?.is_active ? "Active" : "Inactive"}
              </span>
            </p>
            <p className="flex justify-between">
              <span>Verification Status:</span>
              <span className={user?.is_verified ? "text-emerald-400 font-semibold" : "text-amber-400 font-semibold"}>
                {user?.is_verified ? "Verified" : "Unverified"}
              </span>
            </p>
            <p className="flex justify-between">
              <span>Registered:</span>
              <span className="text-white">{getRegistrationDate()}</span>
            </p>
          </div>
        </div>

        {/* Right Form: Details */}
        <div className="md:col-span-2 rounded-2xl border border-white/10 bg-white/[0.01] p-6 space-y-6">
          <h3 className="text-lg font-semibold text-white">Profile Details</h3>

          {message && (
            <div
              className={`flex items-center gap-2 p-3 rounded-xl text-sm ${
                message.isError
                  ? "bg-rose-500/10 border border-rose-500/20 text-rose-300"
                  : "bg-emerald-500/10 border border-emerald-500/20 text-emerald-300"
              }`}
            >
              {message.isError ? <AlertCircle size={16} /> : <CheckCircle size={16} />}
              <span>{message.text}</span>
            </div>
          )}

          <form className="space-y-5" onSubmit={handleSave}>
            <div className="grid gap-5 sm:grid-cols-2">
              <div>
                <label className="mb-2 block text-sm text-slate-300">Full Name</label>
                <div className="relative">
                  <User size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                  <input
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="w-full rounded-xl border border-white/10 bg-slate-900 px-9 py-2.5 text-sm text-white outline-none focus:border-violet-500"
                  />
                </div>
              </div>
              <div>
                <label className="mb-2 block text-sm text-slate-300">Email Address</label>
                <div className="relative">
                  <Mail size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                  <input
                    type="email"
                    value={user?.email || ""}
                    disabled
                    className="w-full rounded-xl border border-white/10 bg-slate-900/50 px-9 py-2.5 text-sm text-slate-500 outline-none cursor-not-allowed"
                  />
                </div>
              </div>
            </div>

            <div>
              <label className="mb-2 block text-sm text-slate-300">Bio / Notes</label>
              <textarea
                value={bio}
                onChange={(e) => setBio(e.target.value)}
                placeholder="Developer sandbox user for DeepGuard authenticity testing..."
                rows={3}
                className="w-full rounded-xl border border-white/10 bg-slate-900 px-4 py-2.5 text-sm text-white outline-none focus:border-violet-500 resize-none"
              />
            </div>

            <div className="pt-4 border-t border-white/5 flex justify-end">
              <button
                type="submit"
                disabled={saving || !name.trim()}
                className="flex items-center gap-2 rounded-xl bg-violet-600 px-5 py-2.5 text-sm font-semibold hover:bg-violet-500 transition disabled:opacity-50"
              >
                <Save size={16} />
                {saving ? "Saving..." : "Save Changes"}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}

