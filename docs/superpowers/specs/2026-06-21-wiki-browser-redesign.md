# Design Specification: Wiki Browser Page Redesign

This document outlines the design specification for redesigning the **Kho Wiki Lịch Sử** (Wiki Browser) page. The goal is to make the interface look highly premium, clean, cohesive, and integrate interactive features that enhance user experience.

---

## 1. Aesthetic and Style Guide

To avoid typical generic AI layouts, the redesigned interface adopts a **Warm Editorial + Premium SaaS** vibe.

*   **Colors & Surfaces:**
    *   Background: Muted off-white/warm-paper background (`bg-[#FAF9F5]`).
    *   Text: Slate-charcoal (`text-[#1C2120]`) for high readability without harsh contrast.
    *   Accent: Historical terracotta copper (`text-[#cc785c]`, `bg-[#cc785c]`).
    *   Borders: Sparse, light-tan hairlines (`border-[#e6dfd8]`).
*   **Typography:**
    *   Display/Headings: Clean geometric sans-serif Display fonts.
    *   Body text: Highly legible sans-serif (`Inter`) with comfortable reading heights (`leading-relaxed`).
*   **Card design:**
    *   Rounded corners: `rounded-xl` (12px) for cards, `rounded-2xl` (16px) for modals and panels.
    *   Transitions: Hover scale and shadow shift (`hover:-translate-y-0.5 hover:shadow-md hover:border-[#cc785c]/30 duration-200`).
*   **Anti-Slop constraints:**
    *   No neon text shadows or artificial button glows.
    *   No em-dashes (`—`) in headlines or metadata.
    *   No raw black color `#000000`.

---

## 2. Component Specifications

The redesign consists of four main additions and layout overhauls in `WikiBrowserPage.tsx`:

### A. Collapsible Bento Stats Header
*   A premium dashboard strip at the top of the wiki browser page:
    *   **Tile 1 (Total Pages):** A simple tile showing the total number of pages.
    *   **Tile 2 (Pending Drafts):** A tile showing the number of draft revisions awaiting approval, linking straight to the Review page.
    *   **Tile 3 (Giai đoạn):** A small chart or visual bar illustrating document distribution by historical period.
*   **Interactivity:** Toggled using a subtle button to show/hide to maximize screen real estate when browsing.

### B. Filter & Search Hub
*   Unified filter bar with shortcut keys badge (e.g. `⌘K` or `/` indicator).
*   Compact project selection dropdown and period selection pills.
*   "Clear Filters" button that only renders when search queries or period/project filters are active.

### C. Refined Wiki Card
*   Visual hierarchy upgrades with high-contrast text and desaturated, color-coded badges for periods:
    *   `khang-chien-chong-phap`: Muted indigo-blue.
    *   `khang-chien-chong-my`: Muted rose-red.
    *   `thong-nhat`: Muted emerald-green.
*   **Hover Action Overlay:** Smoothly slides in a small "Hỏi AI" (Ask AI) or "Xem nhanh" (Quick View) button when mouse hovers over the card.

### D. Slide-out Preview Drawer
*   A right-side sliding panel (Drawer) that opens when a user clicks on any Wiki Card:
    *   **Layout:** 40-45% width of the viewport, sliding from the right edge with backdrop-blur.
    *   **Features:**
        *   **Table of Contents (ToC):** Fast-nav jump links for sections (Bối cảnh, Nguyên nhân, Diễn biến, Kết quả, Ý nghĩa, v.v.).
        *   **Ask AI Shortcut:** A prominent button "Hỏi AI về sự kiện này" which routes the user to the `/chat` page and pre-loads the event's markdown content as a context prompt.
        *   **Edit Article:** A direct edit button for Administrators/Editors to open the editor.
*   **Benefit:** Users can read and analyze wiki entries instantly without full page reloads, keeping them in their search/analysis flow.

### E. Propose Modal with Markdown Auto-Parser
*   Split pane layout inside the modal: Left side is the Markdown Editor, right side is the rendered HTML Preview.
*   **Drag-and-Drop Dropzone:** A beautiful visual box to drop `.md` files.
*   **Auto-Parser:** Reads the markdown content, parses top-level sections (e.g. `# Bối cảnh`, `# Nguyên nhân`), and populates the respective fields automatically to save manual entry.

---

## 3. Data flow & Code Safety

*   All changes will be isolated within `WikiBrowserPage.tsx`.
*   Uses `motion` (Framer Motion) for sliding animations (Drawer and Modals).
*   No new backend dependencies required; uses existing API endpoints (`wikiApi`, `projectsApi`, `draftsApi`).
