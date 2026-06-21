import { useUIStore } from "@/stores/uiStore";

export function ConfirmModal() {
  const { modal, confirmAction, cancelAction } = useUIStore();

  if (!modal.isOpen) return null;

  return (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-stone-900/40 dark:bg-black/60 backdrop-blur-sm animate-fade-in"
        onClick={cancelAction}
      />

      {/* Modal Container */}
      <div className="relative w-full max-w-md bg-white dark:bg-stone-900 rounded-2xl border border-stone-200/60 dark:border-stone-800 p-6 shadow-2xl animate-scale-up text-left">
        <h3 className="text-lg font-bold text-stone-900 dark:text-stone-100 mb-2">
          {modal.title}
        </h3>
        <p className="text-[14.5px] text-stone-600 dark:text-stone-400 mb-6 leading-relaxed">
          {modal.message}
        </p>

        <div className="flex items-center justify-end gap-3">
          <button
            type="button"
            onClick={cancelAction}
            disabled={modal.isSubmitting}
            className="px-4 py-2 text-[13.5px] font-semibold text-stone-600 dark:text-stone-400 hover:bg-stone-50 dark:hover:bg-stone-850 rounded-xl transition-all border border-stone-200/50 dark:border-stone-800 disabled:opacity-50"
          >
            {modal.cancelText || "Hủy"}
          </button>
          <button
            type="button"
            onClick={confirmAction}
            disabled={modal.isSubmitting}
            className="px-5 py-2 text-[13.5px] font-semibold text-white bg-[#cc785c] hover:bg-[#b8664b] dark:bg-[#bf694f] dark:hover:bg-[#a6563c] rounded-xl shadow-md transition-all flex items-center gap-1.5 disabled:opacity-50"
          >
            {modal.isSubmitting && (
              <span className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
            )}
            {modal.confirmText || "Xác nhận"}
          </button>
        </div>
      </div>
    </div>
  );
}
