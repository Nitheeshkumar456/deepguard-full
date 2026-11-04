import { ArrowUpRight, ArrowDownRight } from "lucide-react";

interface StatCardProps {
  title: string;
  value: string | number;
  description?: string;
  icon?: React.ReactNode;
  trend?: {
    value: number;
    isPositive: boolean;
    label?: string;
  };
  status?: "default" | "success" | "warning" | "error";
  onClick?: () => void;
}

export default function StatCard({
  title,
  value,
  description,
  icon,
  trend,
  status = "default",
  onClick,
}: StatCardProps) {
  const getStatusBorder = () => {
    switch (status) {
      case "success":
        return "border-emerald-500/20 bg-emerald-500/[0.01] hover:border-emerald-500/40";
      case "warning":
        return "border-amber-500/20 bg-amber-500/[0.01] hover:border-amber-500/40";
      case "error":
        return "border-rose-500/20 bg-rose-500/[0.01] hover:border-rose-500/40";
      default:
        return "border-white/10 bg-white/[0.01] hover:border-violet-500/40";
    }
  };

  const getIconColor = () => {
    switch (status) {
      case "success":
        return "text-emerald-400 bg-emerald-500/10";
      case "warning":
        return "text-amber-400 bg-amber-500/10";
      case "error":
        return "text-rose-400 bg-rose-500/10";
      default:
        return "text-violet-400 bg-violet-500/10";
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (onClick && (e.key === "Enter" || e.key === " ")) {
      e.preventDefault();
      onClick();
    }
  };

  return (
    <div
      onClick={onClick}
      onKeyDown={handleKeyDown}
      role={onClick ? "button" : undefined}
      tabIndex={onClick ? 0 : undefined}
      className={`rounded-2xl border p-6 shadow-md transition-all duration-300 ${getStatusBorder()} ${
        onClick ? "cursor-pointer hover:-translate-y-0.5 hover:shadow-lg focus:outline-none focus:ring-2 focus:ring-violet-500/50" : ""
      }`}
    >
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-slate-400">{title}</span>
        {icon && (
          <div className={`flex h-10 w-10 items-center justify-center rounded-xl transition-colors duration-300 ${getIconColor()}`}>
            {icon}
          </div>
        )}
      </div>

      <div className="mt-4 flex items-baseline gap-2">
        <span className="text-3xl font-bold tracking-tight text-white">{value}</span>
        {trend && (
          <span
            className={`inline-flex items-center gap-0.5 rounded-full px-2 py-0.5 text-xs font-semibold ${
              trend.isPositive
                ? "bg-emerald-500/10 text-emerald-400"
                : "bg-rose-500/10 text-rose-400"
            }`}
          >
            {trend.isPositive ? <ArrowUpRight size={12} /> : <ArrowDownRight size={12} />}
            {trend.value}%
          </span>
        )}
      </div>

      {(description || (trend && trend.label)) && (
        <p className="mt-2 text-xs text-slate-500 leading-normal">
          {description || trend?.label}
        </p>
      )}
    </div>
  );
}
