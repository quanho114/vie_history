# Design Spec: HistoriAI Wiki Sprint 1 — AI-Native Knowledge System Redesign

Author: AI Assistant & User Pair Programming
Date: 2026-06-18
Topic: HistoriAI Wiki System Redesign (Sprint 1)

---

## 1. Objectives

1.  **Chat Context Integration**: Connect the Wiki layer with the Agentic RAG chat by parsing context parameters in `ChatPage.tsx` and initializing agent state.
2.  **Toast & Custom Modal System**: Replace native browser `alert()` and `confirm()` calls with a custom, lightweight, Earth-tone UI system using Zustand state management.
3.  **Markdown Editor & Unified Renderer**: Provide a custom markdown editor inside the edit/propose flow and unify markdown rendering across both detail viewing and editing previews.

---

## 2. Technical Specifications

### 2.1 Chat Context Integration

#### URL Contract
```http
/chat?context_type=wiki&context_id=tran-hung-dao
```

#### Client Interface (`apps/web/src/pages/ChatPage.tsx`)
*   Read query parameters on mount using `useSearchParams`.
*   If `context_type` and `context_id` are present:
    1.  Call the backend API (or existing `wikiApi.getPage(slug)`) to load context data.
    2.  Set the active chat session context.
    3.  Prepopulate the chat interface with a helper prompt (e.g., `"Hãy cho tôi biết thêm về Trần Hưng Đạo"`).
    4.  Pass this structured context to the LLM agent to support context-aware answers and citations.

---

### 2.2 UI System: Toast & ConfirmModal

#### State Management (`apps/web/src/stores/uiStore.ts`)
```typescript
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
```

#### Global Containers
*   `<ToastContainer />` and `<ConfirmModalContainer />` rendered globally in `App.tsx` or `AppShell.tsx`.
*   Visual styles match the Earth-tone dark/light schema with smooth fade-in animations and glassmorphism.

---

### 2.3 Markdown Editor & Renderer

#### Unified Renderer (`apps/web/src/components/UI/MarkdownRenderer.tsx`)
*   Uses `react-markdown` with customized elements:
    *   **Headings (`h1`, `h2`, `h3`)**: styled with font-display and bottom borders.
    *   **Blockquotes**: custom quote blocks for historical references.
    *   **Tables**: structured data tables for comparing figures or timelines.
    *   **Links / Citations**: custom styled highlights.

#### Editor Component (`apps/web/src/components/UI/MarkdownEditor.tsx`)
*   Tabbed interface: **Soạn thảo** (Write) and **Xem trước** (Preview).
*   Preview tab renders via `<MarkdownRenderer />`.
*   **Toolbar buttons**: Bold, H1, H2, Quote, Table, Link, Image. Clicking these inserts corresponding markdown template tags at the textarea cursor.

---

## 3. Implementation Checklist & Schedule

*   **Day 1-2**: Implement Chat Context URL Contract, router changes, and API loading in `ChatPage.tsx`.
*   **Day 3**: Implement `uiStore.ts`, custom `Toast` and `ConfirmModal` UI components, and replace native alert/confirms in the Wiki pages.
*   **Day 4-6**: Create `MarkdownRenderer.tsx` and `MarkdownEditor.tsx` with its toolbar, and integrate them into the Wiki detail and proposal modals.
*   **Day 7**: CSS Polish, animation tune-up, responsiveness checks, and manual browser verification.
