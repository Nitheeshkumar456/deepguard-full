import { AlertTriangle, Loader2, Inbox } from "lucide-react";

interface EmptyStateProps {
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
  icon?: React.ReactNode;
}

export function EmptyState({
  title,
  description,
  actionLabel,
  onAction,
  icon,
}: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-white/10 bg-white/[0.01] p-12 text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-slate-900/50 text-slate-500 mb-4">
        {icon || <Inbox size={24} />}
      </div>
      <h3 className="text-lg font-semibold text-white">{title}</h3>
      <p className="mt-2 max-w-sm text-sm text-slate-400 leading-relaxed">{description}</p>
      {actionLabel && onAction && (
        <button
          onClick={onAction}
          className="mt-6 rounded-xl bg-violet-600 px-5 py-2.5 text-sm font-semibold hover:bg-violet-500 transition"
        >
          {actionLabel}
        </button>
      )}
    </div>
  );
}

interface LoadingStateProps {
  message?: string;
}

export function LoadingState({ message = "Loading data..." }: LoadingStateProps) {
  return (
    <div className="flex flex-col items-center justify-center p-12 text-center">
      <Loader2 size={36} className="animate-spin text-violet-500 mb-4" />
      <p className="text-sm text-slate-400 font-medium">{message}</p>
    </div>
  );
}

interface ErrorStateProps {
  title?: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
}

export function ErrorState({
  title = "Something went wrong",
  description,
  actionLabel,
  onAction,
}: ErrorStateProps) {
  return (
    <div className="flex flex-col items-center justify-center rounded-2xl border border-red-500/20 bg-red-500/5 p-12 text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-red-500/10 text-red-400 mb-4">
        <AlertTriangle size={24} />
      </div>
      <h3 className="text-lg font-semibold text-white">{title}</h3>
      <p className="mt-2 max-w-sm text-sm text-slate-400 leading-relaxed">{description}</p>
      {actionLabel && onAction && (
        <button
          onClick={onAction}
          className="mt-6 rounded-xl border border-red-500/20 bg-red-500/10 px-5 py-2.5 text-sm font-semibold text-red-400 hover:bg-red-500/20 transition"
        >
          {actionLabel}
        </button>
      )}
    </div>
  );
}
