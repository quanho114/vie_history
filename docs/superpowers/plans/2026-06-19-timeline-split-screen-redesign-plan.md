# Timeline Split-Screen Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the TimelinePage to use a split-screen 60/40 layout on desktop, featuring an ultra-compact event list on the left and a sticky, rich AI Insights Panel on the right.

**Architecture:** Restructure the main container using CSS grid. Make the left timeline column scroll independently while the right panel remains sticky. Design the right panel to show period statistics when no event is selected, and details when selected. Use responsive classes so it becomes a slide-out drawer on mobile.

**Tech Stack:** React, Tailwind CSS, Lucide Icons.

---

### Task 1: Layout Restructuring & Scrolling Isolation

**Files:**
- Modify: `apps/web/src/pages/TimelinePage.tsx:263-375`

- [ ] **Step 1: Wrap workspace in a CSS Grid**
  Replace the main scrollable workspace container with a non-scrollable layout containing a 10-column grid. The left column (6 columns) will hold the timeline list and will be scrollable, while the right column (4 columns) will hold the details panel.

  Modify `apps/web/src/pages/TimelinePage.tsx` to structure the grid:
  ```tsx
  {/* ── MAIN WORKSPACE: Vertical Historical Stream ── */}
  <div className="flex-1 bg-[#faf8f3] p-6 overflow-hidden">
    <div className="grid grid-cols-1 lg:grid-cols-10 gap-6 h-full overflow-hidden">
      
      {/* Left Column: Timeline List */}
      <div className="col-span-1 lg:col-span-6 h-full overflow-y-auto pr-2 scrollbar-thin text-left flex flex-col">
        {loading ? (
          <div className="h-full flex items-center justify-center">
            <div className="flex flex-col items-center gap-2 text-[#8c8275] animate-pulse">
              <div className="w-8 h-8 rounded-full border-2 border-[#cc785c] border-t-transparent animate-spin" />
              <span className="text-xs font-semibold uppercase tracking-wider">Đang tải biên niên sử...</span>
            </div>
          </div>
        ) : error ? (
          <div className="max-w-md mx-auto mt-8 bg-red-50 border border-red-100 rounded-sm p-5 text-red-600 text-sm flex items-center gap-2.5">
            <Info size={16} />
            <span>{error}</span>
          </div>
        ) : filteredEvents.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center max-w-sm mx-auto">
            <div className="w-14 h-14 rounded-sm bg-white border border-[#e8ddd0] flex items-center justify-center mb-4 text-[#8c8275] shadow-sm">
              <BookOpen size={20} />
            </div>
            <h3 className="font-serif text-sm font-bold text-[#1c1a17]">Không tìm thấy mốc lịch sử nào</h3>
            <p className="text-xs text-[#8c8275] mt-1">Hãy thử tìm kiếm với từ khóa khác hoặc đổi bộ lọc thời kỳ.</p>
          </div>
        ) : (
          <div className="relative pl-6 border-l-2 border-[#e8ddd0] ml-4 space-y-8 max-w-full text-left py-2">
            {uniqueYears.map((year) => {
              const yearEvents = eventsByYear[year]
              return (
                <div key={year} className="relative">
                  {/* Year marker line header */}
                  <div className="flex items-center gap-3 mb-3 -ml-[31px]">
                    <div className="w-3 h-3 rounded-full border-2 border-[#cc785c] bg-[#faf8f3] flex-shrink-0 z-10" />
                    <span className="font-mono text-[11px] font-bold text-[#cc785c] tracking-[0.1em] uppercase">
                      {year < 0 ? `TCN ${Math.abs(year)}` : year}
                    </span>
                    <div className="flex-1 h-px bg-[#e8ddd0]" />
                  </div>

                  {/* Events list placeholder for task 2 */}
                  <div className="space-y-2">
                    {/* Render cards here */}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* Right Column: AI Insights Panel will reside here */}
    </div>
  </div>
  ```

- [ ] **Step 2: Hide drawer overlay backdrop on desktop**
  Update the drawer backdrop overlay to only display on mobile screens (`lg:hidden`).
  Modify line 364 in `apps/web/src/pages/TimelinePage.tsx`:
  ```tsx
  {/* ── DRAWER BACKDROP OVERLAY ── */}
  {expandedEvent && (
    <div 
      className="fixed inset-0 bg-black/10 backdrop-blur-xs z-40 transition-opacity duration-300 lg:hidden"
      onClick={() => setExpandedEvent(null)}
    />
  )}
  ```

- [ ] **Step 3: Commit changes**
  Run:
  ```bash
  git add apps/web/src/pages/TimelinePage.tsx
  git commit -m "refactor: restructure timeline layout with independent scroll grids"
  ```

---

### Task 2: Implementing Compact Timeline Cards

**Files:**
- Modify: `apps/web/src/pages/TimelinePage.tsx:307-353`

- [ ] **Step 1: Replace old card markup with compact design**
  Simplify the card content. Remove the summary block, the bottom border line, and the explorer link text. Tighter padding, smaller fonts, and clean selected and hover states will make it clean and neat.
  
  Replace the event list mapping inside `uniqueYears.map` in `apps/web/src/pages/TimelinePage.tsx`:
  ```tsx
  {/* Events list */}
  <div className="space-y-2">
    {yearEvents.map((ev) => {
      const isSelected = expandedEvent === ev.id
      const cat = getEventCategory(ev.title)
      
      return (
        <div
          key={ev.id}
          onClick={() => setExpandedEvent(isSelected ? null : ev.id)}
          className={cn(
            "relative p-2.5 pl-3.5 pr-2.5 bg-white border border-[#e8ddd0] transition-all duration-200 cursor-pointer text-left rounded-sm group",
            isSelected 
              ? "border-[#cc785c] bg-[#cc785c]/5 shadow-[0_2px_12px_rgba(204,120,92,0.05)] translate-x-0.5" 
              : "hover:bg-[#faf8f3] hover:border-[#cc785c]/45 hover:translate-x-0.5"
          )}
        >
          <div className={cn(
            "absolute left-0 top-0 bottom-0 w-[3px] rounded-l-sm transition-colors",
            isSelected ? "bg-[#cc785c]" : "bg-transparent group-hover:bg-[#cc785c]/45"
          )} />
          
          <div className="flex items-center justify-between gap-2 mb-1">
            <span className={cn("text-[9px] font-bold tracking-wider uppercase px-1.5 py-0.5 rounded-sm", cat.color)}>
              {cat.icon} {cat.label}
            </span>
            <span className="font-mono text-[9px] text-[#a09589]">
              {formatEventDate(ev)}
            </span>
          </div>

          <h3 className={cn(
            "font-serif text-[13px] font-bold leading-snug transition-colors",
            isSelected ? "text-[#cc785c]" : "text-[#1c1a17] group-hover:text-[#cc785c]"
          )}>
            {ev.title}
          </h3>
        </div>
      )
    })}
  </div>
  ```

- [ ] **Step 2: Commit changes**
  Run:
  ```bash
  git add apps/web/src/pages/TimelinePage.tsx
  git commit -m "feat: design compact timeline cards without summaries and footers"
  ```

---

### Task 3: Dual-State AI Insights Panel (Default & Selection States)

**Files:**
- Modify: `apps/web/src/pages/TimelinePage.tsx:372-579`

- [ ] **Step 1: Compute filter period statistics**
  At the beginning of `TimelinePage` (e.g., right before returns), calculate the metrics and category breakdown of the current list of events.
  
  Add this logic around line 180 of `apps/web/src/pages/TimelinePage.tsx`:
  ```tsx
  // Compute stats for current period
  const stats = { total: filteredEvents.length, military: 0, diplomacy: 0, politics: 0, culture: 0, general: 0 }
  filteredEvents.forEach(ev => {
    const cat = getEventCategory(ev.title).label
    if (cat === "Quân sự") stats.military++
    else if (cat === "Ngoại giao") stats.diplomacy++
    else if (cat === "Chính trị") stats.politics++
    else if (cat === "Văn hóa") stats.culture++
    else stats.general++
  })
  const maxStat = Math.max(stats.military, stats.diplomacy, stats.politics, stats.culture, stats.general) || 1
  ```

- [ ] **Step 2: Update details panel container and render Default State**
  Refactor the panel container to reside inside the Grid on desktop (`lg:static lg:col-span-4 lg:translate-x-0 lg:shadow-none lg:border-l lg:h-full lg:w-full`) while remaining a slide-over panel on mobile/tablet.
  If `expandedEvent` is null, render the Default State containing the current era label, event statistics, category distribution breakdown bars, and quick AI prompts.

  Replace the panel markup:
  ```tsx
  {/* ── DRAWER PANEL CONTAINER (Slide-over RAG explorer / Static Panel on Desktop) ── */}
  <div className={cn(
    "fixed top-0 right-0 h-full w-[400px] max-w-[90vw] bg-[#faf8f3] border-l border-[#e8ddd0] shadow-[-8px_0_24px_rgba(28,26,23,0.08)] z-50 transition-transform duration-300 transform flex flex-col",
    "lg:static lg:col-span-4 lg:h-full lg:w-full lg:max-w-none lg:shadow-none lg:border-l lg:z-0 lg:transform-none lg:transition-none",
    expandedEvent ? "translate-x-0" : "translate-x-full"
  )}>
    {!expandedEvent ? (
      /* Default State */
      <div className="flex-1 flex flex-col overflow-hidden text-left p-6 space-y-6">
        <div className="flex items-center gap-2.5 pb-4 border-b border-[#e8ddd0]/50">
          <span className="text-xl bg-white w-8 h-8 rounded-sm flex items-center justify-center border border-[#e8ddd0] shadow-xs">
            🏛️
          </span>
          <div>
            <span className="text-[9px] font-bold uppercase tracking-[0.2em] text-[#8c8275]">
              Thời kỳ đang chọn
            </span>
            <div className="text-sm font-bold text-[#cc785c] mt-0.5">
              {selectedPeriod === "all" ? "Toàn bộ lịch sử Việt Nam" : (PERIOD_LABELS[selectedPeriod] || selectedPeriod)}
            </div>
          </div>
        </div>

        {/* Stats Section */}
        <div className="space-y-3.5">
          <h4 className="text-[10px] font-bold uppercase tracking-[0.2em] text-[#8c8275]">
            Thống kê thời kỳ
          </h4>
          <div className="p-4 bg-white border border-[#e8ddd0] rounded-sm space-y-3">
            <div className="flex justify-between items-center text-xs font-semibold text-[#1c1a17]">
              <span>Tổng số mốc sự kiện</span>
              <span className="font-mono text-sm text-[#cc785c]">{stats.total}</span>
            </div>
            
            {/* Horizontal visual breakdown bars */}
            <div className="space-y-2 pt-2 border-t border-[#f0eae1]">
              <div className="space-y-1">
                <div className="flex justify-between text-[10px] text-[#5c544a] font-medium">
                  <span>⚔️ Quân sự</span>
                  <span className="font-mono">{stats.military}</span>
                </div>
                <div className="h-1.5 w-full bg-[#f0eae1] rounded-full overflow-hidden">
                  <div className="h-full bg-red-400 rounded-full" style={{ width: `${(stats.military / maxStat) * 100}%` }} />
                </div>
              </div>

              <div className="space-y-1">
                <div className="flex justify-between text-[10px] text-[#5c544a] font-medium">
                  <span>🤝 Ngoại giao</span>
                  <span className="font-mono">{stats.diplomacy}</span>
                </div>
                <div className="h-1.5 w-full bg-[#f0eae1] rounded-full overflow-hidden">
                  <div className="h-full bg-sky-400 rounded-full" style={{ width: `${(stats.diplomacy / maxStat) * 100}%` }} />
                </div>
              </div>

              <div className="space-y-1">
                <div className="flex justify-between text-[10px] text-[#5c544a] font-medium">
                  <span>🏛️ Chính trị</span>
                  <span className="font-mono">{stats.politics}</span>
                </div>
                <div className="h-1.5 w-full bg-[#f0eae1] rounded-full overflow-hidden">
                  <div className="h-full bg-amber-500 rounded-full" style={{ width: `${(stats.politics / maxStat) * 100}%` }} />
                </div>
              </div>

              <div className="space-y-1">
                <div className="flex justify-between text-[10px] text-[#5c544a] font-medium">
                  <span>📜 Văn hóa</span>
                  <span className="font-mono">{stats.culture}</span>
                </div>
                <div className="h-1.5 w-full bg-[#f0eae1] rounded-full overflow-hidden">
                  <div className="h-full bg-emerald-500 rounded-full" style={{ width: `${(stats.culture / maxStat) * 100}%` }} />
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* AI Quick Prompts */}
        <div className="p-4 bg-[#cc785c]/5 border border-[#cc785c]/10 rounded-sm space-y-3">
          <div className="text-[10px] font-bold text-[#cc785c] uppercase tracking-[0.1em] flex items-center gap-1.5">
            <Sparkles size={13} />
            Hỏi AI về Thời kỳ này
          </div>
          <div className="space-y-2">
            <button
              onClick={() => navigate(`/chat?q=${encodeURIComponent(`Hãy tóm tắt các diễn biến lịch sử quan trọng nhất trong giai đoạn ${selectedPeriod === "all" ? "Lịch sử Việt Nam" : (PERIOD_LABELS[selectedPeriod] || selectedPeriod)}`)}`)}
              className="w-full p-2.5 bg-white hover:bg-stone-50 border border-[#e8ddd0] hover:border-[#cc785c] rounded-sm text-left text-xs font-medium text-[#1c1a17] flex items-center justify-between group transition-all cursor-pointer"
            >
              <span>Xem tóm tắt diễn biến thời kỳ?</span>
              <ArrowRight size={12} className="text-[#8c8275] group-hover:translate-x-0.5 transition-transform" />
            </button>
            <button
              onClick={() => navigate(`/chat?q=${encodeURIComponent(`Các nhân vật lịch sử nào có tầm ảnh hưởng lớn nhất trong giai đoạn ${selectedPeriod === "all" ? "Lịch sử Việt Nam" : (PERIOD_LABELS[selectedPeriod] || selectedPeriod)}?`)}`)}
              className="w-full p-2.5 bg-white hover:bg-stone-50 border border-[#e8ddd0] hover:border-[#cc785c] rounded-sm text-left text-xs font-medium text-[#1c1a17] flex items-center justify-between group transition-all cursor-pointer"
            >
              <span>Nhân vật tầm ảnh hưởng lớn?</span>
              <ArrowRight size={12} className="text-[#8c8275] group-hover:translate-x-0.5 transition-transform" />
            </button>
          </div>
        </div>
      </div>
    ) : (
      /* Selected Event Detail State (Keep existing code from lines 376-578) */
      <div className="flex-1 flex flex-col overflow-hidden text-left">
        {/* Context Panel Header */}
        <div className="px-6 py-4 bg-[#f4ece1] border-b border-[#e8ddd0] flex items-center justify-between flex-shrink-0">
          <div className="flex items-center gap-2.5">
            <span className="text-xl bg-white w-8 h-8 rounded-sm flex items-center justify-center border border-[#e8ddd0] shadow-xs">
              {getEventCategory(expandedData.title).icon}
            </span>
            <div className="text-left">
              <span className="text-[9px] font-bold uppercase tracking-[0.2em] text-[#8c8275]">
                AI Context Panel
              </span>
              <div className="text-xs font-bold text-[#cc785c] mt-0.5">
                {formatEventDate(expandedData)}
              </div>
            </div>
          </div>
          <button
            onClick={() => setExpandedEvent(null)}
            className="w-7 h-7 rounded-full flex items-center justify-center text-[#8c8275] hover:bg-white hover:text-[#1c1a17] border border-transparent hover:border-[#e8ddd0] transition-all cursor-pointer bg-white/50"
          >
            <X size={14} />
          </button>
        </div>

        {/* Panel Content Scrollable */}
        <div className="flex-1 overflow-y-auto px-6 py-6 space-y-6">
          <div className="text-left space-y-1">
            <div className="inline-block px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider rounded-sm bg-[#f0eae1] text-[#5c544a]">
              {getEraLabel(expandedData.period) || "Sự kiện lịch sử"}
            </div>
            <h3 className="font-serif text-lg font-bold text-[#1c1a17] leading-snug">
              {expandedData.title}
            </h3>
          </div>

          {expandedData.summary && (
            <div className="text-left space-y-2">
              <h4 className="text-[10px] font-bold uppercase tracking-[0.2em] text-[#8c8275]">
                Tại sao quan trọng?
              </h4>
              <div className="p-4 rounded-sm bg-white border border-[#e8ddd0] shadow-xs">
                <p className="text-[12.5px] text-[#1c1a17]/90 leading-relaxed font-serif italic">
                  "{expandedData.summary}"
                </p>
              </div>
            </div>
          )}

          {/* Sơ đồ Liên kết Tri thức */}
          <div className="text-left space-y-2">
            <h4 className="text-[10px] font-bold uppercase tracking-[0.2em] text-[#8c8275] flex items-center gap-1">
              <span>🕸️</span> Sơ đồ Liên kết Tri thức
            </h4>
            <div className="p-4 rounded-sm bg-white border border-[#e8ddd0] flex flex-col items-center justify-center min-h-[220px] relative overflow-hidden">
              <div className="absolute inset-0 opacity-[0.02] pointer-events-none" 
                   style={{ backgroundImage: "radial-gradient(#cc785c 1px, transparent 1px)", backgroundSize: "16px 16px" }} />
              {loadingContext ? (
                <div className="flex flex-col items-center gap-2 text-[#8c8275]">
                  <div className="w-5 h-5 rounded-full border-2 border-[#cc785c] border-t-transparent animate-spin" />
                  <span className="text-xs">Đang lập sơ đồ kết nối...</span>
                </div>
              ) : wikiContext?.context?.entities && wikiContext.context.entities.length > 0 ? (
                <div className="relative w-full h-48 flex items-center justify-center">
                  <div className="absolute z-20 w-16 h-16 rounded-full bg-[#cc785c] text-white flex items-center justify-center text-center p-1.5 shadow-md border-2 border-white scale-100 hover:scale-105 transition-transform">
                    <span className="text-[8px] font-serif font-bold leading-tight line-clamp-3">
                      {expandedData.title}
                    </span>
                  </div>
                  {wikiContext.context.entities.slice(0, 5).map((entity: string, idx: number) => {
                    const angle = (idx * 2 * Math.PI) / Math.min(wikiContext.context.entities.slice(0, 5).length, 5)
                    const radius = 68
                    const x = Math.round(radius * Math.cos(angle))
                    const y = Math.round(radius * Math.sin(angle))
                    const icon = getEntityIcon(entity)
                    return (
                      <div key={idx} className="absolute z-10" style={{ transform: `translate(${x}px, ${y}px)` }}>
                        <svg className="absolute top-1/2 left-1/2 w-48 h-48 -translate-x-1/2 -translate-y-1/2 pointer-events-none z-0" style={{ overflow: "visible" }}>
                          <line x1="0" y1="0" x2={-x} y2={-y} stroke="#e8ddd0" strokeWidth="1.5" strokeDasharray="3 3"/>
                        </svg>
                        <button
                          onClick={() => navigate(`/chat?q=${encodeURIComponent(`Hãy kể cho tôi nghe về ${entity}`)}`)}
                          title={`Hỏi AI về ${entity}`}
                          className="w-10 h-10 rounded-full bg-white hover:bg-[#faf8f3] border border-[#e8ddd0] hover:border-[#cc785c] shadow-sm flex items-center justify-center text-base transition-all cursor-pointer relative group"
                        >
                          <span>{icon}</span>
                          <span className="absolute -bottom-5 left-1/2 -translate-x-1/2 bg-stone-900 text-white text-[8px] px-1 rounded opacity-0 group-hover:opacity-100 whitespace-nowrap pointer-events-none z-30 transition-opacity">
                            {entity}
                          </span>
                        </button>
                      </div>
                    )
                  })}
                </div>
              ) : (
                <div className="text-xs text-[#8c8275] italic">
                  Không tìm thấy thực thể liên quan trực tiếp.
                </div>
              )}
            </div>
          </div>

          {/* Connected Entity Buttons */}
          {wikiContext?.context?.entities && wikiContext.context.entities.length > 0 && (
            <div className="text-left space-y-2">
              <h4 className="text-[10px] font-bold uppercase tracking-[0.2em] text-[#8c8275]">
                Thực thể Lịch sử liên kết
              </h4>
              <div className="flex flex-wrap gap-1.5">
                {wikiContext.context.entities.map((entity: string, idx: number) => {
                  const icon = getEntityIcon(entity)
                  return (
                    <button
                      key={idx}
                      onClick={() => navigate(`/chat?q=${encodeURIComponent(`Hãy phân tích mối liên hệ của nhân vật/sự kiện "${entity}" đối với sự kiện "${expandedData.title}"`)}`)}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white hover:bg-[#f0eae1] border border-[#e8ddd0] hover:border-[#cc785c] rounded-sm text-xs font-semibold text-[#1c1a17] transition-all cursor-pointer"
                    >
                      <span>{icon}</span>
                      <span>{entity}</span>
                      <ArrowUpRight size={10} className="text-[#8c8275]" />
                    </button>
                  )
                })}
              </div>
            </div>
          )}

          {/* RAG Quick Ask suggestions */}
          <div className="p-4 bg-[#cc785c]/5 border border-[#cc785c]/10 rounded-sm text-left space-y-3">
            <div className="text-[10px] font-bold text-[#cc785c] uppercase tracking-[0.1em] flex items-center gap-1.5">
              <Sparkles size={13} />
              Trợ lý Lịch sử AI RAG
            </div>
            <div className="space-y-2">
              <button
                onClick={() => navigate(`/chat?q=${encodeURIComponent(`Giải thích bối cảnh lịch sử và nguyên nhân chính dẫn đến sự kiện "${expandedData.title}"?`)}&context_type=wiki&context_id=${expandedData.wiki_page_slug || ""}`)}
                className="w-full p-3 bg-white hover:bg-stone-50 border border-[#e8ddd0] hover:border-[#cc785c] rounded-sm text-left text-xs font-medium text-[#1c1a17] flex items-center justify-between group transition-all cursor-pointer"
              >
                <span className="line-clamp-1">Giải thích nguyên nhân & bối cảnh chính?</span>
                <ArrowRight size={13} className="text-[#8c8275] group-hover:translate-x-0.5 transition-transform shrink-0 ml-2" />
              </button>
              <button
                onClick={() => navigate(`/chat?q=${encodeURIComponent(`Phân tích ảnh hưởng lâu dài và tầm quan trọng lịch sử của sự kiện "${expandedData.title}"?`)}&context_type=wiki&context_id=${expandedData.wiki_page_slug || ""}`)}
                className="w-full p-3 bg-white hover:bg-stone-50 border border-[#e8ddd0] hover:border-[#cc785c] rounded-sm text-left text-xs font-medium text-[#1c1a17] flex items-center justify-between group transition-all cursor-pointer"
              >
                <span className="line-clamp-1">Ảnh hưởng lâu dài đến lịch sử Việt Nam?</span>
                <ArrowRight size={13} className="text-[#8c8275] group-hover:translate-x-0.5 transition-transform shrink-0 ml-2" />
              </button>
            </div>
          </div>
        </div>

        {/* Context Panel Footer Actions */}
        <div className="p-4 border-t border-[#e8ddd0] bg-[#f4ece1] flex gap-2.5 flex-shrink-0">
          {expandedData.wiki_page_slug && (
            <button
              onClick={() => navigate(`/wiki/${expandedData.wiki_page_slug}`)}
              className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2.5 bg-white hover:bg-stone-50 text-[#1c1a17] text-xs font-bold rounded-sm border border-[#e8ddd0] transition-all cursor-pointer shadow-xs"
            >
              📖 Đọc tài liệu Wiki
            </button>
          )}
          <button
            onClick={() => navigate(`/chat?q=${encodeURIComponent(`Hãy kể cho tôi nghe chi tiết về ${expandedData.title}`)}&context_type=wiki&context_id=${expandedData.wiki_page_slug || ""}`)}
            className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2.5 bg-[#cc785c] hover:bg-[#b0674c] text-white text-xs font-bold rounded-sm transition-all shadow-sm cursor-pointer border-none"
          >
            💬 Hỏi AI Assistant
          </button>
        </div>
      </div>
    )}
  </div>
  ```

- [ ] **Step 3: Commit changes**
  Run:
  ```bash
  git add apps/web/src/pages/TimelinePage.tsx
  git commit -m "feat: implement dual-state AI Insights Panel with period statistics"
  ```

---

### Task 4: UI Verification & Optimization

**Files:**
- Test: manual verification on `http://localhost:12702`

- [ ] **Step 1: Verify layout and scroll behavior**
  Open the app in the browser. Go to `/timeline`. Verify that:
  - The left column (Timeline List) scrolls independently without scrolling the right column (AI Insights Panel).
  - The right column stays sticky and shows Period statistics when no card is clicked.

- [ ] **Step 2: Verify compact card details**
  Ensure cards contain only title, category badge, and date. Check that hover and selected states work smoothly (slight right translation, colored borders).

- [ ] **Step 3: Verify dynamic loading in details panel**
  Click on a card. Verify that the AI Insights Panel immediately updates with the clicked event details, knowledge graph, and quick AI prompts.

- [ ] **Step 4: Verify responsive styling**
  Resize the viewport to mobile width (<1024px).
  Verify that the layout collapses to 1 column. Clicking an event should slide the panel in as a drawer overlay. Clicking the background overlay should dismiss the drawer.
