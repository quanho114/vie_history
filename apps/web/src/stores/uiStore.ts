import { create } from "zustand";

interface ToastState {
  isOpen: boolean;
  message: string;
  type: "success" | "error" | "info";
}

interface ModalState {
  isOpen: boolean;
  title: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  onConfirm: () => void | Promise<void>;
  onCancel?: () => void;
  isSubmitting?: boolean;
}

interface UIStore {
  toast: ToastState;
  modal: ModalState;
  showToast: (message: string, type?: "success" | "error" | "info") => void;
  hideToast: () => void;
  showConfirm: (options: Omit<ModalState, "isOpen" | "isSubmitting">) => void;
  confirmAction: () => Promise<void>;
  cancelAction: () => void;
}

export const useUIStore = create<UIStore>()((set, get) => {
  let toastTimeoutId: ReturnType<typeof setTimeout> | null = null;

  return {
    toast: {
      isOpen: false,
      message: "",
      type: "info",
    },
    modal: {
      isOpen: false,
      title: "",
      message: "",
      confirmText: "Xác nhận",
      cancelText: "Hủy",
      onConfirm: () => {},
    },
    showToast: (message, type = "info") => {
      if (toastTimeoutId) {
        clearTimeout(toastTimeoutId);
      }
      set({
        toast: {
          isOpen: true,
          message,
          type,
        },
      });
      toastTimeoutId = setTimeout(() => {
        get().hideToast();
        toastTimeoutId = null;
      }, 4000);
    },
    hideToast: () => {
      set((state) => ({
        toast: {
          ...state.toast,
          isOpen: false,
        },
      }));
    },
    showConfirm: (options) => {
      set({
        modal: {
          isOpen: true,
          title: options.title,
          message: options.message,
          confirmText: options.confirmText || "Xác nhận",
          cancelText: options.cancelText || "Hủy",
          onConfirm: options.onConfirm,
          onCancel: options.onCancel,
          isSubmitting: false,
        },
      });
    },
    confirmAction: async () => {
      const { onConfirm } = get().modal;
      set((state) => ({
        modal: {
          ...state.modal,
          isSubmitting: true,
        },
      }));
      try {
        await onConfirm();
      } catch (err) {
        console.error("Error inside modal confirmation action:", err);
      } finally {
        set((state) => ({
          modal: {
            ...state.modal,
            isOpen: false,
            isSubmitting: false,
          },
        }));
      }
    },
    cancelAction: () => {
      const { onCancel } = get().modal;
      if (onCancel) {
        onCancel();
      }
      set((state) => ({
        modal: {
          ...state.modal,
          isOpen: false,
        },
      }));
    },
  };
});
