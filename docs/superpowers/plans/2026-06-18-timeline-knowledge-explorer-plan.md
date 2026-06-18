# Historical Knowledge Explorer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor the Timeline page into a premium vertical timeline explorer with slide-over drawer details and museum exhibit cards.

**Architecture:** 
- Initialize the sidebar in collapsed mode by default to act as a slim 64px nav rail.
- Remove horizontal timeline components and bottom list to unify flow under the vertical timeline stream.
- Re-architect the AI Context Panel into an absolute-positioned floating drawer with backdrop overlay.
- Style the cards with sharp corners, left accent border, and reduced horizontal borders.

**Tech Stack:** React, Tailwind CSS, Lucide icons, Vite.

---

### Task 1: Initialize Slim Sidebar Navigation Rail
Make the collapsible sidebar start in the collapsed state (slim nav rail) by default unless the user explicitly toggles it open.

**Files:**
- Modify: `apps/web/src/components/layout/AppShell.tsx:13-15`

- [ ] **Step 1: Update the sidebarCollapsed initialization**
  Replace lines 13-15 in `AppShell.tsx` to check if `localStorage` has a value, defaulting to `true` (collapsed) if not:
  ```typescript
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => {
    const val = localStorage.getItem("sidebar_collapsed");
    return val === null ? true : val === "true";
  });
  ```

- [ ] **Step 2: Commit changes**
  ```bash
  git add apps/web/src/components/layout/AppShell.tsx
  git commit -m "feat: default sidebar to collapsed slim rail layout"
  ```

---

### Task 2: Streamline Timeline Main Layout & Vertical Focus
Clean up elements and double-lines, eliminating the horizontal slider and bottom list completely.

**Files:**
- Modify: `apps/web/src/pages/TimelinePage.tsx`

- [ ] **Step 1: Edit the main container and remove horizontal timeline references**
  Remove any horizontal timeline state, container height bounds, and extra horizontal divider lines. Emphasize a clean vertical flow with maximum screen height.
  Modify the outer container layout in `TimelinePage.tsx` to support a full-height scrollable left column and a right-aligned floating drawer.

- [ ] **Step 2: Remove horizontal lines from filters and headers**
  Change borders from `border-b border-[#e8ddd0]` to custom soft margin spaces or very light transparent lines `border-b border-[#e8ddd0]/40` to achieve a 40% reduction in horizontal divider lines.

- [ ] **Step 3: Commit changes**
  ```bash
  git add apps/web/src/pages/TimelinePage.tsx
  git commit -m "style: vertical stream focus and horizontal border reduction"
  ```

---

### Task 3: Redesign Cards to "Museum Exhibit Labels"
Implement sharp corners, thin borders, left gold-accent indicators, and editorial-focused typography.

**Files:**
- Modify: `apps/web/src/pages/TimelinePage.tsx`

- [ ] **Step 1: Refactor the card styling**
  Find the event cards mapped in `TimelinePage.tsx` and change their CSS classes to use sharp corners (`rounded-none` or `rounded-xs`), an absolute accent line (`absolute left-0 top-0 bottom-0 w-1 bg-[#cc785c]`), a thin border (`border-[#e8ddd0]`), and high-contrast serif typography:
  ```typescript
  <div
    key={ev.id}
    onClick={() => setExpandedEvent(isSelected ? null : ev.id)}
    className={cn(
      "relative p-6 bg-white border border-[#e8ddd0] transition-all duration-300 cursor-pointer text-left rounded-xs",
      isSelected 
        ? "border-[#cc785c] shadow-[0_4px_20px_rgba(204,120,92,0.04)] translate-x-1" 
        : "hover:border-[#cc785c]/60"
    )}
  >
    <div className="absolute left-0 top-0 bottom-0 w-1 bg-[#cc785c]" />
    
    <div className="flex items-center justify-between gap-3 mb-2">
      <span className={cn("text-[9px] font-bold tracking-wider uppercase px-2 py-0.5 border border-transparent rounded-xs", cat.color)}>
        {cat.icon} {cat.label}
      </span>
      <span className="font-mono text-xs text-[#8c8275] bg-[#f0eae1] px-1.5 py-0.5 rounded-xs">
        {formatEventDate(ev)}
      </span>
    </div>

    <h3 className="font-serif text-[17px] font-bold text-[#1c1a17] leading-snug group-hover:text-[#cc785c] transition-colors mt-1">
      {ev.title}
    </h3>

    {ev.summary && (
      <p className="text-[12.5px] text-[#5c544a] mt-2.5 leading-relaxed font-serif italic text-justify opacity-95">
        "{ev.summary}"
      </p>
    )}

    <div className="mt-4 pt-3.5 border-t border-[#f0eae1]/50 flex items-center justify-between text-[10px] text-[#cc785c] font-bold">
      <span className="flex items-center gap-1">
        👤 {ev.wiki_page_slug ? "Xem liên kết & phân tích →" : "Xem chi tiết →"}
      </span>
    </div>
  </div>
  ```

- [ ] **Step 2: Commit changes**
  ```bash
  git add apps/web/src/pages/TimelinePage.tsx
  git commit -m "style: redesign event cards to museum exhibit labels"
  ```

---

### Task 4: Implement Slide-Over AI Context Drawer
Reposition the AI Context Panel to act as a floating slide-over drawer coming from the right when an event is selected.

**Files:**
- Modify: `apps/web/src/pages/TimelinePage.tsx`

- [ ] **Step 1: Implement overlay backdrop and slide-over transition styles**
  Replace the right-hand panel container with a fixed, absolute-positioned drawer wrapper that transitions off-screen on the right when `selectedEvent` is null. Add a clickable dark/blur overlay behind it:
  ```typescript
  {/* Drawer Backdrop Overlay */}
  {expandedEvent && (
    <div 
      className="fixed inset-0 bg-black/10 backdrop-blur-xs z-40 transition-opacity duration-300 animate-fade-in"
      onClick={() => setExpandedEvent(null)}
    />
  )}

  {/* Drawer Panel Container */}
  <div className={cn(
    "fixed top-0 right-0 h-full w-[380px] bg-[#faf8f3] border-l border-[#e8ddd0] shadow-[-8px_0_24px_rgba(28,26,23,0.08)] z-50 transition-transform duration-300 transform flex flex-col",
    expandedEvent ? "translate-x-0" : "translate-x-full"
  )}>
    {/* Inside goes the existing AI Context Panel Content */}
    {expandedData && (
      ...
    )}
  </div>
  ```

- [ ] **Step 2: Commit changes**
  ```bash
  git add apps/web/src/pages/TimelinePage.tsx
  git commit -m "feat: transform AI Context panel into slide-over drawer"
  ```

---

### Task 5: Final Validation & Build Verification
Verify everything builds and loads correctly without any lint or compilation errors.

**Files:**
- None

- [ ] **Step 1: Build the application locally**
  Run: `npm run build` in the `apps/web` directory.
  Expected: Successful exit code 0.

- [ ] **Step 2: Commit final refactoring**
  ```bash
  git commit -am "chore: finalize historical knowledge explorer redesign" --allow-empty
  ```
