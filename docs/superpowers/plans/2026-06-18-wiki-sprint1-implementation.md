# HistoriAI Wiki Sprint 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Modernize the HistoriAI Wiki System by integrating chat contexts, transitioning native browser alerts/confirms to a custom Zustand UI store/components, and introducing a unified Markdown Renderer and tabbed Editor with a quick toolbar.

**Architecture:** 
1. **Chat Context**: Add `/wiki/{slug}/context` backend endpoint. In `ChatPage.tsx`, parse `context_type` and `context_id` from search params, fetch the context payload, pre-populate the chat input, and set up LLM agent filters.
2. **Toast & Modal**: Build `uiStore.ts` for global notification state. Create `Toast.tsx` and `ConfirmModal.tsx` components, render them globally, and replace all window-blocking native dialogs.
3. **Markdown Editor & Renderer**: Build a central `MarkdownRenderer.tsx` and a toolbar-equipped `MarkdownEditor.tsx` (using `react-markdown`), applying them across details and editor tabs.

**Tech Stack:** ReactJS, TypeScript, Tailwind CSS, Zustand, react-router-dom, react-markdown

---

### Task 1: Backend & Frontend Chat Context Endpoint

**Files:**
- Create/Modify: `apps/api/app/api/routes/wiki.py`
- Modify: `apps/web/src/lib/api/brain.ts`

- [ ] **Step 1: Write backend unit/integration test for the wiki context endpoint**
  Add test under `apps/api/tests/integration/test_api.py` or similar to verify context API response.

- [ ] **Step 2: Implement `/api/v1/wiki/{slug}/context` endpoint in backend**
  Add the route in `apps/api/app/api/routes/wiki.py`:
  ```python
  @router.get("/{slug}/context", summary="Get context for wiki page")
  async def get_wiki_context(
      slug: str,
      current_user: CurrentUser,
      db: AsyncSession = Depends(get_db),
  ):
      page = await wiki_service.get_page_by_slug(db, slug)
      if page is None:
          raise HTTPException(
              status_code=status.HTTP_404_NOT_FOUND,
              detail=f"Wiki page with slug '{slug}' not found",
          )
      entities = []
      if page.period:
          entities.append(page.period)
      if page.event_type:
          entities.append(page.event_type)
      sources = []
      if page.content and "references" in page.content:
          refs = page.content["references"]
          if isinstance(refs, str):
              for ref in refs.split("\n"):
                  if ref.strip():
                      sources.append({"title": ref.strip(), "page": 1})
      return {
          "context": {
              "title": page.title,
              "summary": page.summary or "",
              "entities": entities
          },
          "sources": sources
      }
  ```

- [ ] **Step 3: Run pytest to verify the context route**
  Run: `pytest apps/api/tests/` or equivalent backend test execution. Verify status: PASS.

- [ ] **Step 4: Update frontend `wikiApi` client in `apps/web/src/lib/api/brain.ts`**
  Add `getContext` function:
  ```typescript
  getContext(slug: string): Promise<{
    context: {
      title: string;
      summary: string;
      entities: string[];
    };
    sources: Array<{ title: string; page?: number }>;
  }> {
    return request(`/wiki/${slug}/context`);
  },
  ```

- [ ] **Step 5: Commit changes**
  ```bash
  git add apps/api/app/api/routes/wiki.py apps/web/src/lib/api/brain.ts
  git commit -m "feat: add backend and frontend wiki context endpoints"
  ```

---

### Task 2: ChatPage Context Integration

**Files:**
- Modify: `apps/web/src/pages/ChatPage.tsx`

- [ ] **Step 1: Import `useSearchParams` and read query parameters on ChatPage mount**
  In `ChatPage.tsx`, parse `context_type` and `context_id` search params.
  If present:
  1. Clear the query parameters from URL using `window.history.replaceState`.
  2. Fetch context payload using `wikiApi.getContext(contextId)`.
  3. Prepopulate the query input box with `"Hãy cho tôi biết thêm về [Title]"` and execute the chat or let the user hit Send.

- [ ] **Step 2: Commit changes**
  ```bash
  git add apps/web/src/pages/ChatPage.tsx
  git commit -m "feat: integrate agent chat context parser in ChatPage"
  ```

---

### Task 3: Global Zustand uiStore

**Files:**
- Create: `apps/web/src/stores/uiStore.ts`

- [ ] **Step 1: Write `uiStore.ts` state manager**
  Create store with support for showing custom toasts and action-confirm modals.
  ```typescript
  import { create } from "zustand"

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
  }

  interface UIStore {
    toast: ToastState;
    modal: ModalState;
    isSubmitting: boolean;
    showToast: (message: string, type?: "success" | "error" | "info") => void;
    hideToast: () => void;
    showConfirm: (options: Omit<ModalState, "isOpen">) => void;
    confirmAction: () => Promise<void>;
    cancelAction: () => void;
  }

  export const useUIStore = create<UIStore>((set, get) => ({
    toast: { isOpen: false, message: "", type: "info" },
    modal: { isOpen: false, title: "", message: "", onConfirm: () => {} },
    isSubmitting: false,
    showToast: (message, type = "info") => {
      set({ toast: { isOpen: true, message, type } });
      setTimeout(() => get().hideToast(), 4000);
    },
    hideToast: () => set({ toast: { isOpen: false, message: "", type: "info" } }),
    showConfirm: (options) => {
      set({ modal: { ...options, isOpen: true }, isSubmitting: false });
    },
    confirmAction: async () => {
      set({ isSubmitting: true });
      try {
        await get().modal.onConfirm();
      } finally {
        set({ modal: { isOpen: false, title: "", message: "", onConfirm: () => {} }, isSubmitting: false });
      }
    },
    cancelAction: () => {
      if (get().modal.onCancel) get().modal.onCancel?.();
      set({ modal: { isOpen: false, title: "", message: "", onConfirm: () => {} } });
    }
  }));
  ```

- [ ] **Step 2: Commit changes**
  ```bash
  git add apps/web/src/stores/uiStore.ts
  git commit -m "feat: create zustand uiStore for Toasts and ConfirmModals"
  ```

---

### Task 4: Toast & ConfirmModal UI Components

**Files:**
- Create: `apps/web/src/components/UI/Toast.tsx`
- Create: `apps/web/src/components/UI/ConfirmModal.tsx`
- Modify: `apps/web/src/App.tsx` (or other app root file)

- [ ] **Step 1: Implement global Toast component**
  Write custom styled toast under `apps/web/src/components/UI/Toast.tsx` reading state from `useUIStore`. Apply Earth-tone styling and animations.

- [ ] **Step 2: Implement custom ConfirmModal component**
  Write beautiful modal box reading state from `useUIStore`, styling headers, message body, confirmation/cancel action buttons, and loading spinner during submission.

- [ ] **Step 3: Render both Toast & ConfirmModal at App root**
  Open `apps/web/src/App.tsx` and place `<Toast />` and `<ConfirmModal />` globally.

- [ ] **Step 4: Commit changes**
  ```bash
  git add apps/web/src/components/UI/Toast.tsx apps/web/src/components/UI/ConfirmModal.tsx apps/web/src/App.tsx
  git commit -m "feat: add global Toast and ConfirmModal markup and styling"
  ```

---

### Task 5: Replace Native browser alerts/confirms

**Files:**
- Modify: `apps/web/src/pages/WikiBrowserPage.tsx`
- Modify: `apps/web/src/pages/WikiDetailPage.tsx`
- Modify: `apps/web/src/pages/DraftsReviewPage.tsx`
- Modify: `apps/web/src/components/layout/Sidebar.tsx`

- [ ] **Step 1: Replace all `alert()` and `confirm()` calls**
  Import `useUIStore` and replace all browser calls.
  Example replacement for `confirm`:
  ```typescript
  showConfirm({
    title: "Xác nhận xóa",
    message: "Bạn có chắc chắn muốn xóa toàn bộ lịch sử?",
    onConfirm: async () => {
      await handleDeleteAllSessions();
      showToast("Đã xóa tất cả cuộc hội thoại", "success");
    }
  });
  ```
  Example replacement for `alert`:
  ```typescript
  showToast("Phê duyệt bản thảo thành công!", "success");
  ```

- [ ] **Step 2: Commit changes**
  ```bash
  git add apps/web/src/pages/WikiBrowserPage.tsx apps/web/src/pages/WikiDetailPage.tsx apps/web/src/pages/DraftsReviewPage.tsx apps/web/src/components/layout/Sidebar.tsx
  git commit -m "refactor: replace browser alert and confirm with custom UI systems"
  ```

---

### Task 6: Unified MarkdownRenderer & Editor

**Files:**
- Create: `apps/web/src/components/UI/MarkdownRenderer.tsx`
- Create: `apps/web/src/components/UI/MarkdownEditor.tsx`
- Modify: `apps/web/src/pages/WikiDetailPage.tsx`
- Modify: `apps/web/src/pages/WikiBrowserPage.tsx`

- [ ] **Step 1: Create `MarkdownRenderer.tsx`**
  Uses `react-markdown` with refined styles for headers, paragraphs, lists, and tables matching the Earth-tone theme.

- [ ] **Step 2: Create `MarkdownEditor.tsx`**
  Includes a text textarea, toolbar (Bold, H1, H2, Blockquote, Table, Link, Image), and "Soạn thảo" vs "Xem trước" tabs (using `<MarkdownRenderer />` for the preview).

- [ ] **Step 3: Integrate editor & renderer into Wiki forms**
  Replace standard raw textareas inside Wiki propose/edit models with the new `<MarkdownEditor />`.

- [ ] **Step 4: Commit changes**
  ```bash
  git add apps/web/src/components/UI/MarkdownRenderer.tsx apps/web/src/components/UI/MarkdownEditor.tsx apps/web/src/pages/WikiDetailPage.tsx apps/web/src/pages/WikiBrowserPage.tsx
  git commit -m "feat: implement unified MarkdownRenderer and MarkdownEditor with preview tabs"
  ```
