import { useState, useRef, useEffect } from "react";
import { Bell, Menu, User, Settings, LogOut, ChevronDown } from "lucide-react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

interface TopbarProps {
  onMenuClick: () => void;
}

export default function Topbar({ onMenuClick }: TopbarProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout } = useAuth();
  const [showDropdown, setShowDropdown] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setShowDropdown(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleLogout = async () => {
    setShowDropdown(false);
    await logout();
    navigate("/login");
  };

  const getPageTitle = () => {
    const path = location.pathname;
    if (path.startsWith("/dashboard")) return "Dashboard";
    if (path.startsWith("/analyze")) return "Analyze Media";
    if (path.startsWith("/history")) return "Scan History";
    if (path.startsWith("/notifications")) return "Notifications";
    if (path.startsWith("/profile")) return "My Profile";
    if (path.startsWith("/settings")) return "Settings";
    if (path.startsWith("/subscription")) return "Subscription";
    if (path.startsWith("/help")) return "Help & Support";
    if (path.startsWith("/analysis/")) return "Analysis Audit";
    if (path.startsWith("/report/")) return "Classification Report";
    return "Console";
  };

  const getInitials = () => {
    if (!user || !user.name) return "DG";
    const parts = user.name.split(" ");
    if (parts.length >= 2) {
      return (parts[0][0] + parts[1][0]).toUpperCase();
    }
    return user.name.substring(0, 2).toUpperCase();
  };

  return (
    <header className="sticky top-0 z-10 flex h-16 shrink-0 items-center justify-between border-b border-white/10 bg-slate-950/80 px-4 md:px-6 backdrop-blur-md">
      {/* Left: Mobile Toggle & Page Title */}
      <div className="flex items-center gap-4">
        <button
          onClick={onMenuClick}
          className="rounded-lg p-1.5 text-slate-400 hover:bg-white/5 hover:text-white lg:hidden transition"
          aria-label="Toggle mobile menu"
        >
          <Menu size={20} />
        </button>
        <span className="font-semibold text-lg text-white hidden sm:inline-block">
          {getPageTitle()}
        </span>
      </div>

      {/* Right: Actions */}
      <div className="flex items-center gap-4">
        {/* Notifications Icon with Badge */}
        <Link
          to="/notifications"
          className="relative rounded-lg p-2 text-slate-400 hover:bg-white/5 hover:text-white transition"
          aria-label="View notifications"
        >
          <Bell size={20} />
          <span className="absolute right-1.5 top-1.5 flex h-2 w-2 rounded-full bg-violet-500" />
        </Link>

        {/* Vertical Separator */}
        <div className="h-6 w-px bg-white/10" />

        {/* User Profile Dropdown */}
        <div className="relative" ref={dropdownRef}>
          <button
            onClick={() => setShowDropdown(!showDropdown)}
            className="flex items-center gap-2 rounded-xl p-1.5 hover:bg-white/5 transition"
            aria-expanded={showDropdown}
            aria-haspopup="true"
          >
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-violet-600/20 text-violet-400 font-bold border border-violet-500/20 text-xs">
              {getInitials()}
            </div>
            <span className="hidden md:inline-block text-sm font-semibold text-slate-300">
              {user?.email || "anonymous@deepguard.ai"}
            </span>
            <ChevronDown size={14} className="text-slate-500 hidden md:inline-block" />
          </button>

          {showDropdown && (
            <div className="absolute right-0 mt-2 w-48 origin-top-right rounded-xl border border-white/10 bg-slate-900 p-1.5 shadow-2xl z-30 animate-in fade-in slide-in-from-top-2 duration-200">
              <Link
                to="/profile"
                onClick={() => setShowDropdown(false)}
                className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-slate-300 hover:bg-white/5 hover:text-white transition"
              >
                <User size={16} />
                My Profile
              </Link>
              <Link
                to="/settings"
                onClick={() => setShowDropdown(false)}
                className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-slate-300 hover:bg-white/5 hover:text-white transition"
              >
                <Settings size={16} />
                Settings
              </Link>
              <div className="my-1 border-t border-white/5" />
              <button
                onClick={handleLogout}
                className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-rose-400 hover:bg-rose-500/10 hover:text-rose-300 transition text-left"
              >
                <LogOut size={16} />
                Sign Out
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
