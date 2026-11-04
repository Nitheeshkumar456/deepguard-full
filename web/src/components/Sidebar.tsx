import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  ScanSearch,
  History,
  FolderGit2,
  Scale,
  Bell,
  User,
  Settings,
  CreditCard,
  HelpCircle,
  ShieldCheck,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";

const navigation = [
  { name: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { name: "Analyze Media", href: "/analyze", icon: ScanSearch },
  { name: "Scan History", href: "/history", icon: History },
  { name: "Investigation Cases", href: "/cases", icon: FolderGit2 },
  { name: "Compare Media", href: "/compare", icon: Scale },
  { name: "Notifications", href: "/notifications", icon: Bell },
  { name: "My Profile", href: "/profile", icon: User },
  { name: "Settings", href: "/settings", icon: Settings },
  { name: "Subscription", href: "/subscription", icon: CreditCard },
  { name: "Help & Docs", href: "/help", icon: HelpCircle },
];

export default function Sidebar() {
  const { user } = useAuth();

  const getInitials = () => {
    if (!user || !user.name) return "DG";
    const parts = user.name.split(" ");
    if (parts.length >= 2) {
      return (parts[0][0] + parts[1][0]).toUpperCase();
    }
    return user.name.substring(0, 2).toUpperCase();
  };

  return (
    <aside className="fixed inset-y-0 left-0 hidden w-64 border-r border-white/10 bg-slate-950/80 backdrop-blur-md lg:flex lg:flex-col z-20">
      {/* Brand Logo */}
      <div className="flex h-16 shrink-0 items-center gap-3 px-6 border-b border-white/10">
        <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-violet-600">
          <ShieldCheck size={20} className="text-white" />
        </div>
        <div>
          <span className="font-bold text-white text-base leading-none block">DeepGuard AI</span>
          <span className="text-[10px] text-slate-500 font-semibold uppercase tracking-wider block mt-0.5">Console</span>
        </div>
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 space-y-1.5 px-4 py-6 overflow-y-auto">
        {navigation.map((item) => (
          <NavLink
            key={item.name}
            to={item.href}
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-xl px-4 py-3 text-sm font-semibold transition-all duration-200 group ${
                isActive
                  ? "bg-violet-600 text-white shadow-md shadow-violet-600/10"
                  : "text-slate-400 hover:bg-white/5 hover:text-white"
              }`
            }
          >
            {({ isActive }) => (
              <>
                <item.icon
                  size={18}
                  className={`shrink-0 transition-transform duration-200 group-hover:scale-105 ${
                    isActive ? "text-white" : "text-slate-500 group-hover:text-slate-300"
                  }`}
                />
                <span>{item.name}</span>
              </>
            )}
          </NavLink>
        ))}
      </nav>

      {/* Bottom Profile Info */}
      <div className="border-t border-white/10 p-4">
        <NavLink
          to="/profile"
          className="flex items-center gap-3 rounded-xl p-2 text-left hover:bg-white/5 transition"
        >
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-violet-600/20 text-violet-400 font-bold border border-violet-500/20 text-sm">
            {getInitials()}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-white truncate">{user?.name || "DeepGuard User"}</p>
            <p className="text-xs text-slate-500 truncate">{user?.email || "user@deepguard.ai"}</p>
          </div>
        </NavLink>
      </div>
    </aside>
  );
}
