import { useUIStore } from "@/stores/uiStore";
import { X, CheckCircle, AlertCircle, Info } from "lucide-react";

export function ToastContainer() {
  const { toast, hideToast } = useUIStore();

  if (!toast.isOpen) return null;

  const styles = {
    success: {
      bg: "bg-emerald-50/95 dark:bg-emerald-950/30",
      border: "border-emerald-100 dark:border-emerald-900/50",
      text: "text-emerald-800 dark:text-emerald-300",
      icon: <CheckCircle className="w-5 h-5 text-emerald-600 shrink-0" />,
    },
    error: {
      bg: "bg-rose-50/95 dark:bg-rose-950/30",
      border: "border-rose-100 dark:border-rose-900/50",
      text: "text-rose-800 dark:text-rose-300",
      icon: <AlertCircle className="w-5 h-5 text-rose-600 shrink-0" />,
    },
    info: {
      bg: "bg-orange-50/95 dark:bg-stone-900/80",
      border: "border-orange-100 dark:border-stone-850",
      text: "text-[#6f675d] dark:text-stone-300",
      icon: <Info className="w-5 h-5 text-[#cc785c] shrink-0" />,
    },
  }[toast.type];

  return (
    <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-[9999] animate-slide-up">
      <div className={`flex items-center gap-3 px-4 py-3 rounded-xl border backdrop-blur-md shadow-lg max-w-md ${styles.bg} ${styles.border} ${styles.text}`}>
        {styles.icon}
        <span className="text-[13.5px] font-medium leading-relaxed">{toast.message}</span>
        <button
          onClick={hideToast}
          className="text-stone-400 hover:text-stone-600 dark:hover:text-stone-200 p-0.5 rounded-full transition-colors shrink-0"
        >
          <X className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
