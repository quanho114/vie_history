# Wiki Browser Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the Wiki Browser page (`WikiBrowserPage.tsx`) to make it look premium, clean, and highly interactive by adding a Bento Stats Header, a Right-side Slide-out Preview Drawer, and a Drag-and-Drop Markdown Auto-Parser.

**Architecture:** We will keep changes self-contained in `WikiBrowserPage.tsx` using local states, componentizing sub-views internally (e.g., Stats Header, Wiki Card, Preview Drawer), and animating the drawer and modals using Framer Motion. Clicking on a card will open the Preview Drawer in-place on the same screen, with a link to navigate to the full detail view if needed.

**Tech Stack:** React, Tailwind CSS, Lucide Icons (or existing project icons), Framer Motion (`framer-motion` or `motion/react`).

---

### Task 1: Initialize Redesign States and Imports

**Files:**
- Modify: `apps/web/src/pages/WikiBrowserPage.tsx`

- [ ] **Step 1: Check existing imports and add required UI icons and state variables**
  Add state variables at the beginning of the `WikiBrowserPage` component definition (around line 200) for selected page preview, stats visibility, and drag-and-drop state. Ensure icons like `IconBrain`, `IconChevronRight`, `IconTrash`, `IconExternalLink`, `IconMessageSquare` are imported or defined.
  
  ```tsx
  // Add these inside WikiBrowserPage component
  const [selectedWikiPage, setSelectedWikiPage] = useState<WikiPage | null>(null);
  const [isStatsVisible, setIsStatsVisible] = useState<boolean>(true);
  const [isDraggingFile, setIsDraggingFile] = useState<boolean>(false);
  ```

- [ ] **Step 2: Commit initial state additions**
  Run: `git commit -am "refactor(wiki): add new states for preview drawer and stats visibility"`

---

### Task 2: Implement Collapsible Bento Stats Header

**Files:**
- Modify: `apps/web/src/pages/WikiBrowserPage.tsx`

- [ ] **Step 1: Write helper function to compute stats**
  Add code before the JSX return of `WikiBrowserPage` to compute the total number of pages, period distribution, and projects.
  
  ```tsx
  const stats = useMemo(() => {
    const totalPages = allPages.length;
    const totalProjects = projects.length;
    // Count per period
    const periodCounts = allPages.reduce((acc, p) => {
      if (p.period) {
        acc[p.period] = (acc[p.period] || 0) + 1;
      }
      return acc;
    }, {} as Record<string, number>);
    
    return { totalPages, totalProjects, periodCounts };
  }, [allPages, projects]);
  ```

- [ ] **Step 2: Render Bento Stats Header**
  Insert the Bento Stats Header UI directly below the page `<header>` tag, using a clean layout with animated collapse.
  
  ```tsx
  {isStatsVisible && (
    <div className="px-8 py-4 grid grid-cols-1 md:grid-cols-3 gap-4 bg-[#fcfbf9] border-b border-[#e6dfd8] animate-fade-in flex-shrink-0">
      <div className="bg-white border border-[#e6dfd8] rounded-xl p-4 shadow-sm flex items-center justify-between">
        <div>
          <p className="text-xs text-[#8e8b82] uppercase tracking-wider font-semibold">Tổng quan</p>
          <h4 className="text-2xl font-display font-semibold text-[#141413] mt-1">{stats.totalPages} Trang</h4>
        </div>
        <div className="w-10 h-10 bg-[#f5f0e8] text-[#cc785c] rounded-xl flex items-center justify-center">
          <IconBook className="w-5 h-5" />
        </div>
      </div>
      <div className="bg-white border border-[#e6dfd8] rounded-xl p-4 shadow-sm flex items-center justify-between">
        <div>
          <p className="text-xs text-[#8e8b82] uppercase tracking-wider font-semibold">Dự án</p>
          <h4 className="text-2xl font-display font-semibold text-[#141413] mt-1">{stats.totalProjects} Chủ đề</h4>
        </div>
        <div className="w-10 h-10 bg-[#f5f0e8] text-[#cc785c] rounded-xl flex items-center justify-center">
          <IconBrain className="w-5 h-5" />
        </div>
      </div>
      <div className="bg-white border border-[#e6dfd8] rounded-xl p-4 shadow-sm flex flex-col justify-between">
        <p className="text-xs text-[#8e8b82] uppercase tracking-wider font-semibold">Tỷ lệ theo Thời kỳ</p>
        <div className="flex gap-1 mt-2.5 h-2 bg-[#f5f0e8] rounded-full overflow-hidden">
          {Object.entries(stats.periodCounts).map(([period, count], idx) => (
            <div 
              key={period} 
              style={{ width: `${(count / (stats.totalPages || 1)) * 100}%` }}
              className={cn(
                "h-full transition-all duration-300",
                idx % 3 === 0 ? "bg-[#cc785c]" : idx % 3 === 1 ? "bg-indigo-400" : "bg-emerald-400"
              )}
              title={`${period}: ${count}`}
            />
          ))}
        </div>
      </div>
    </div>
  )}
  ```

- [ ] **Step 3: Add stats toggle button in header**
  Add a stats toggle button right next to the "Duyệt bản thảo" button in the page `<header>`:
  
  ```tsx
  <button
    onClick={() => setIsStatsVisible(!isStatsVisible)}
    className="flex items-center gap-2 px-3 py-2 border border-[#e6dfd8] text-[#6c6a64] hover:text-[#cc785c] hover:border-[#cc785c]/40 text-sm font-medium rounded-xl transition-all bg-white"
  >
    {isStatsVisible ? "Ẩn Thống kê" : "Hiện Thống kê"}
  </button>
  ```

- [ ] **Step 4: Commit bento header updates**
  Run: `git commit -am "feat(wiki): implement Collapsible Bento Stats Header"`

---

### Task 3: Refactor Search, Filters, and Wiki Cards UI

**Files:**
- Modify: `apps/web/src/pages/WikiBrowserPage.tsx`

- [ ] **Step 1: Redesign filter bar with shortcut hint and clear button**
  Refactor the search layout:
  - Add search input shortcut indicator (`/` or `⌘K` overlay text).
  - Render a "Xóa bộ lọc" button when filters are active.
  
  ```tsx
  // Inside filter bar
  {(search || selectedProjectId || period) && (
    <button
      onClick={() => {
        setSearch("");
        setSelectedProjectId("");
        setPeriod("");
      }}
      className="text-xs font-semibold text-[#cc785c] hover:text-[#a9583e] flex items-center gap-1 transition-colors"
    >
      Xóa tất cả bộ lọc <IconClose className="w-3.5 h-3.5" />
    </button>
  )}
  ```

- [ ] **Step 2: Redesign WikiCard Component**
  Modify the `WikiCard` component (around line 874) to support custom hover styling and passing clicks to `setSelectedWikiPage(page)` instead of hard navigating:
  
  ```tsx
  // Inside WikiCard
  function WikiCard({ page, onClick, onAskAI }: { page: WikiPage; onClick: () => void; onAskAI: (e: React.MouseEvent) => void }) {
    return (
      <div
        className="group relative bg-white border border-[#e6dfd8] rounded-xl shadow-[0_1px_3px_rgba(0,0,0,0.02)] p-5 text-left hover:shadow-md hover:border-[#cc785c]/40 transition-all duration-200 animate-fade-in flex flex-col justify-between cursor-pointer"
        onClick={onClick}
      >
        <div>
          <div className="flex flex-wrap gap-1.5 mb-3">
            {page.period && (
              <span className={cn("text-[10px] font-semibold px-2 py-0.5 rounded-full border", getPeriodColor(page.period))}>
                {page.period.replace(/-/g, " ")}
              </span>
            )}
            {page.event_type && (
              <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-[#f5f0e8] text-[#6c6a64] border border-[#e6dfd8]">
                {page.event_type}
              </span>
            )}
          </div>
          <h3 className="font-display text-[15px] font-semibold text-[#141413] mb-2 group-hover:text-[#cc785c] transition-colors line-clamp-2 leading-snug">
            {page.title}
          </h3>
          <p className="text-xs text-[#6c6a64] line-clamp-3 leading-relaxed">
            {page.summary || "Chưa có tóm tắt."}
          </p>
        </div>
        <div className="mt-4 pt-3 border-t border-[#f5f0e8] flex items-center justify-between">
          <span className="text-[10px] text-[#8e8b82]">Độ dài: {page.content ? page.content.split(" ").length : 0} từ</span>
          <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
            <button
              onClick={(e) => {
                e.stopPropagation();
                onAskAI(e);
              }}
              className="p-1 text-[#6c6a64] hover:text-[#cc785c] hover:bg-[#f5f0e8] rounded-lg transition-colors"
              title="Hỏi AI về trang này"
            >
              <IconMessageSquare className="w-4 h-4" />
            </button>
            <span className="flex items-center gap-1 text-[#cc785c] text-xs font-semibold">
              Đọc nhanh <IconChevronRight className="w-3.5 h-3.5" />
            </span>
          </div>
        </div>
      </div>
    );
  }
  ```

- [ ] **Step 3: Update card grid render**
  Update the mapping in `WikiBrowserPage` to render cards using the new click-to-preview logic and linking Ask AI:
  
  ```tsx
  {allPages.map((page) => (
    <WikiCard 
      key={page.id} 
      page={page} 
      onClick={() => setSelectedWikiPage(page)} 
      onAskAI={() => navigate(`/chat?q=Hãy tóm tắt sự kiện lịch sử ${page.title}`)} 
    />
  ))}
  ```

- [ ] **Step 4: Commit UI refinements**
  Run: `git commit -am "style(wiki): refine search, filter hubs, and WikiCard component styles"`

---

### Task 4: Implement Slide-out Preview Drawer

**Files:**
- Modify: `apps/web/src/pages/WikiBrowserPage.tsx`

- [ ] **Step 1: Add slide-out Preview Drawer component code**
  Implement the right-side sliding drawer. Inside `WikiBrowserPage`, render the drawer side-by-side with the card grid.
  
  ```tsx
  {selectedWikiPage && (
    <div className="fixed inset-y-0 right-0 w-[45%] bg-white border-l border-[#e6dfd8] shadow-2xl z-40 flex flex-col animate-slide-in-right">
      {/* Drawer Header */}
      <div className="p-6 border-b border-[#e6dfd8] flex justify-between items-start flex-shrink-0 bg-[#faf9f5]">
        <div>
          <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full border bg-white border-[#e6dfd8] text-[#cc785c]">
            {selectedWikiPage.period?.replace(/-/g, " ") || "Chưa phân loại"}
          </span>
          <h2 className="text-xl font-display font-semibold text-[#141413] mt-2 leading-tight">
            {selectedWikiPage.title}
          </h2>
        </div>
        <button
          onClick={() => setSelectedWikiPage(null)}
          className="p-1.5 rounded-lg hover:bg-[#f5f0e8] text-[#8e8b82] hover:text-[#141413] transition-colors"
        >
          <IconClose className="w-5 h-5" />
        </button>
      </div>

      {/* Drawer Body (Scrollable) */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {/* Quick Summary Banner */}
        {selectedWikiPage.summary && (
          <div className="p-4 bg-[#f5f0e8]/50 border border-[#e6dfd8] rounded-xl text-sm text-[#6c6a64] leading-relaxed italic">
            {selectedWikiPage.summary}
          </div>
        )}

        {/* Sections parsing and rendering */}
        <div className="prose prose-sm max-w-none text-[#3d3d3a] space-y-4">
          {selectedWikiPage.content ? (
            <div className="whitespace-pre-line text-sm leading-relaxed">{selectedWikiPage.content}</div>
          ) : (
            <p className="text-xs text-[#8e8b82] italic">Nội dung chi tiết đang được cập nhật...</p>
          )}
        </div>
      </div>

      {/* Drawer Footer Actions */}
      <div className="p-5 border-t border-[#e6dfd8] flex items-center justify-between flex-shrink-0 bg-[#faf9f5]">
        <button
          onClick={() => navigate(`/chat?q=Hãy giải thích chi tiết về ${selectedWikiPage.title}`)}
          className="flex items-center gap-2 px-4 py-2 bg-[#cc785c] text-white text-sm font-semibold rounded-xl hover:bg-[#a9583e] transition-all shadow-sm"
        >
          <IconMessageSquare className="w-4 h-4" /> Hỏi AI về trang này
        </button>
        <div className="flex gap-2">
          <button
            onClick={() => navigate(`/wiki/${selectedWikiPage.slug}`)}
            className="flex items-center gap-1.5 px-4 py-2 border border-[#e6dfd8] text-[#6c6a64] hover:text-[#cc785c] text-sm font-semibold rounded-xl bg-white hover:bg-[#f5f0e8] transition-colors"
          >
            Đọc trang đầy đủ <IconExternalLink className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  )}
  ```

- [ ] **Step 2: Commit Drawer integration**
  Run: `git commit -am "feat(wiki): add Right-side Slide-out Preview Drawer for wiki cards"`

---

### Task 5: Refactor Propose Modal with Dropzone & Auto-Parser

**Files:**
- Modify: `apps/web/src/pages/WikiBrowserPage.tsx`

- [ ] **Step 1: Update modal layout to 2-column layout**
  Refactor the "Đề xuất trang mới" modal (around line 650) to support split columns on desktop (editor on the left, live HTML preview on the right).

- [ ] **Step 2: Integrate Drag & Drop Markdown File Uploader**
  Add drag enter, drag leave, and drop handlers. Render a visual drag zone when files are dragged onto the editor area.
  
  ```tsx
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDraggingFile(true);
  };

  const handleDragLeave = () => {
    setIsDraggingFile(false);
  };

  const handleDropFile = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDraggingFile(false);
    const file = e.dataTransfer.files[0];
    if (file && (file.name.endsWith(".md") || file.name.endsWith(".txt"))) {
      const reader = new FileReader();
      reader.onload = (event) => {
        const text = event.target?.result as string;
        const parsed = parseMarkdownToSections(text);
        setDraftSections(parsed);
      };
      reader.readAsText(file);
    }
  };
  ```

- [ ] **Step 3: Implement Drag Zone JSX UI**
  Add dropzone trigger handlers inside the form:
  
  ```tsx
  <div 
    onDragOver={handleDragOver}
    onDragLeave={handleDragLeave}
    onDrop={handleDropFile}
    className={cn(
      "border-2 border-dashed rounded-xl p-6 text-center transition-all cursor-pointer",
      isDraggingFile 
        ? "border-[#cc785c] bg-[#cc785c]/5"
        : "border-[#e6dfd8] hover:border-[#cc785c]/40 bg-white"
    )}
  >
    <IconUpload className="w-8 h-8 mx-auto text-[#8e8b82] mb-2" />
    <p className="text-xs font-semibold text-[#141413]">Kéo thả file Markdown (.md) vào đây</p>
    <p className="text-[10px] text-[#8e8b82] mt-1">Hệ thống sẽ tự động phân tích các đề mục (Bối cảnh, Diễn biến, v.v.)</p>
  </div>
  ```

- [ ] **Step 4: Commit uploader & parser enhancements**
  Run: `git commit -am "feat(wiki): add drag-and-drop markdown file auto-parser inside propose modal"`

---

### Task 6: Build Verification and Polish

**Files:**
- Run Verification

- [ ] **Step 1: Run application build to ensure no TypeScript or CSS errors**
  Run: `npm run build` in the workspace root or inside web app directory. Ensure success.

- [ ] **Step 2: Commit verified changes**
  Run: `git commit -am "chore: verify build correctness for new wiki page layout"`
