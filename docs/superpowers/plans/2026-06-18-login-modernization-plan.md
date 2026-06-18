# Login Page Modernization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Modernize the Login/Register Page (`apps/web/src/pages/LoginPage.tsx`) to "The Ethereal Archive" design system, replacing legacy light backgrounds and borders with high-end glassmorphism, deep teals, rotating watermarks, and smooth transitions.

**Architecture:** Update the JSX structure and Tailwind classes of the LoginPage, incorporating custom CSS keyframes for slow rotation and rising embers. Maintain the existing state machine and API integration to prevent functionality regression.

**Tech Stack:** React, TailwindCSS, Lucide icons, React Router, Zustand.

---

### Task 1: Add Custom CSS Keyframes for Embers and Spin
Modify the style block at the end of the `LoginPage.tsx` to include the required animation classes and keyframes.

**Files:**
- Modify: `apps/web/src/pages/LoginPage.tsx`

- [ ] **Step 1: Inspect style tag location in LoginPage.tsx**
Review the CSS styles around lines 649-657.

- [ ] **Step 2: Add animations for spinning and embers**
Update the `<style>` block in `apps/web/src/pages/LoginPage.tsx` (lines 649-657) to define:
- `animate-spin-slow` (180s linear spin)
- `.ember` styling with rising animation
- `.glow-path` or glow effects
Ensure the CSS reads exactly:
```css
      <style>{`
        .animate-fadeIn {
          animation: fadeIn 0.25s ease-out forwards;
        }
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(4px); }
          to { opacity: 1; transform: translateY(0); }
        }
        @keyframes spin-slow {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
        .animate-spin-slow {
          animation: spin-slow 180s linear infinite;
        }
        .ember {
          position: absolute;
          bottom: -20px;
          width: 3px;
          height: 3px;
          background: #cc785c;
          border-radius: 50%;
          opacity: 0.8;
          filter: blur(0.5px);
          box-shadow: 0 0 8px #cc785c, 0 0 15px #da251d;
          animation: rise infinite ease-in-out;
        }
        @keyframes rise {
          0% {
            transform: translateY(0) scale(1) translateX(0);
            opacity: 0;
          }
          10% {
            opacity: 0.8;
          }
          90% {
            opacity: 0.4;
          }
          100% {
            transform: translateY(-110vh) scale(0.3) translateX(60px);
            opacity: 0;
          }
        }
      `}</style>
```

- [ ] **Step 3: Commit the CSS updates**
```bash
git add apps/web/src/pages/LoginPage.tsx
git commit -m "style: add spin-slow and rising embers keyframes to login page"
```

---

### Task 2: Modernize the Main Layout and Left Showcase Panel
Update the background, colors, typography, and decorative elements of the main layout and left showcase column of the LoginPage.

**Files:**
- Modify: `apps/web/src/pages/LoginPage.tsx`

- [ ] **Step 1: Update the page wrapper styling**
Replace the page wrapper (around line 273):
```tsx
    <div className="min-h-screen w-full flex bg-[#051A1A] text-white selection:bg-[#cc785c]/10 selection:text-[#cc785c] overflow-hidden relative font-sans">
```

- [ ] **Step 2: Update the Left Showcase Panel layout and decorative background**
Replace the Left Showcase Panel div (around lines 275-281) to include:
- A radial gradient background (`bg-gradient-to-br from-[#0D3E3E] to-[#051A1A]`)
- Rotating Dong Son Bronze Drum watermark SVG
- Rising embers animation divs
- Ambient glows using teals and reds
The updated JSX should look exactly like:
```tsx
      {/* ── LEFT SHOWCASE PANEL (Visible on Medium+ screens) ──────────────────── */}
      <div className="hidden md:flex md:w-[50%] lg:w-[55%] bg-gradient-to-br from-[#0D3E3E] to-[#051A1A] text-[#efeae4] p-12 lg:p-16 flex-col justify-between relative overflow-hidden border-r border-white/5">
        {/* Dong Son Bronze Drum Background Watermark */}
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none opacity-[0.03] overflow-hidden">
          <svg 
            viewBox="0 0 500 500" 
            className="w-[120vh] h-[120vh] text-[#cc785c] animate-spin-slow"
            fill="none" 
            xmlns="http://www.w3.org/2000/svg"
          >
            <circle cx="250" cy="250" r="240" stroke="currentColor" strokeWidth="1" strokeDasharray="3 3" />
            <circle cx="250" cy="250" r="225" stroke="currentColor" strokeWidth="2" />
            <circle cx="250" cy="250" r="200" stroke="currentColor" strokeWidth="1" strokeDasharray="10 5" />
            <circle cx="250" cy="250" r="175" stroke="currentColor" strokeWidth="1.5" />
            <circle cx="250" cy="250" r="140" stroke="currentColor" strokeWidth="1" strokeDasharray="2 4" />
            <circle cx="250" cy="250" r="100" stroke="currentColor" strokeWidth="2.5" />
            <circle cx="250" cy="250" r="60" stroke="currentColor" strokeWidth="1" />
            <polygon 
              points="250,195 254,232 288,212 264,241 298,250 264,259 288,288 254,268 250,305 246,268 212,288 236,259 202,250 236,241 212,212 246,232" 
              fill="currentColor" 
              opacity="0.8"
            />
          </svg>
        </div>

        {/* Cinematic Rising Embers */}
        <div className="absolute inset-0 pointer-events-none overflow-hidden opacity-30">
          <span className="ember" style={{ left: "10%", animationDelay: "0s", animationDuration: "6s" }} />
          <span className="ember" style={{ left: "30%", animationDelay: "1.5s", animationDuration: "8s" }} />
          <span className="ember" style={{ left: "50%", animationDelay: "0.5s", animationDuration: "7s" }} />
          <span className="ember" style={{ left: "70%", animationDelay: "2s", animationDuration: "9s" }} />
          <span className="ember" style={{ left: "90%", animationDelay: "1s", animationDuration: "6s" }} />
        </div>

        {/* Ambient glows */}
        <div className="absolute top-[-10%] left-[-10%] w-[60%] h-[60%] rounded-full bg-[#cc785c]/10 blur-[130px] pointer-events-none" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] rounded-full bg-[#cc785c]/5 blur-[120px] pointer-events-none" />
```

- [ ] **Step 3: Update brand headers and copyright info in Left Showcase**
Change label colors to white-muted:
- Brand name: `text-white`
- Title description: `text-white/60`
- Feature item titles: `text-white/95`
- Feature item descriptions: `text-white/60`
- Copyright: `text-white/30 border-white/5`

- [ ] **Step 4: Commit Left Panel updates**
```bash
git add apps/web/src/pages/LoginPage.tsx
git commit -m "feat: modernize login left showcase panel layout and typography"
```

---

### Task 3: Modernize the Right Auth Panel and Glassmorphic Card
Update the right column container, forms, cards, tabs, and fields to meet glassmorphic criteria.

**Files:**
- Modify: `apps/web/src/pages/LoginPage.tsx`

- [ ] **Step 1: Update the Right Auth Panel background and text header**
- Right panel container background: `bg-transparent`
- Text header: Title `text-white`, description `text-white/60`
- Tab selector background: `bg-[#0B3030]/60 border border-white/10`
- Tab buttons: Active `bg-[#cc785c] text-white shadow-sm`, inactive `text-white/60 hover:text-white`

- [ ] **Step 2: Update the Form Card styling**
Change Form Card class (around line 400) to:
```tsx
            <div className="bg-[#0B3030]/40 backdrop-blur-md rounded-2xl border border-white/10 p-6 sm:p-8 shadow-[0_4px_30px_rgba(0,0,0,0.2)]">
```

- [ ] **Step 3: Update form input and button styles**
- Input labels: `text-white/60`
- Input elements (Email, Username, Password):
  ```tsx
  className="w-full bg-white/5 border border-white/10 rounded-xl py-2.5 pl-9 pr-4 text-sm text-white outline-none placeholder:text-white/30 focus:border-[#cc785c] focus:ring-2 focus:ring-[#cc785c]/10 transition-all box-border"
  ```
- Password visibility icon: `text-white/40 hover:text-white`
- Submit Button styling:
  ```tsx
  className="w-full bg-gradient-to-r from-[#cc785c] to-[#a8583c] hover:opacity-95 text-white py-2.5 px-4 rounded-xl text-xs font-semibold tracking-wide flex items-center justify-center gap-2 cursor-pointer shadow-md hover:shadow-lg disabled:cursor-not-allowed disabled:opacity-50 transition-all hover:scale-[1.01] active:scale-[0.99] mt-2 border-0"
  ```

- [ ] **Step 4: Update links, footer descriptions, and modal popup**
- "Quên mật khẩu?" link: `text-[#cc785c] hover:text-[#b86246]`
- Right Panel footer text: `text-white/40` and `text-white/30`
- Forgot Password Modal wrapper: `bg-[#0B3030]/90 border border-white/10 text-white`
- Forgot Password Modal form fields: inputs `bg-white/5 border border-white/10 text-white focus:border-[#cc785c]`, cancel button `bg-white/5 text-white/70 hover:bg-white/10 border-white/10`, submit button `bg-[#cc785c] hover:bg-[#b86246]`

- [ ] **Step 5: Commit Right Panel and form card updates**
```bash
git add apps/web/src/pages/LoginPage.tsx
git commit -m "feat: modernize right login panel, form inputs and glassmorphic card"
```

---

### Task 4: Modernize Transition Screens (Map, Flag, and Progress overlays)
Align the full-screen verification map and exit loader with the Ethereal Archive design aesthetic.

**Files:**
- Modify: `apps/web/src/pages/LoginPage.tsx`

- [ ] **Step 1: Modernize Successful Verification Overlay (isTransitioning)**
Update the background gradient, maps, and texts:
- Main overlay background: `bg-[#051A1A]`
- Vietnam Map container styling: `bg-[#0B3030]/30 border border-white/10 shadow-[0_0_50px_rgba(204,120,92,0.15)]`
- Rotating drum watermark: `text-[#cc785c]/5`
- Continue button styling:
  ```tsx
  className="mt-6 px-6 py-2.5 rounded-xl border border-[#cc785c]/40 bg-gradient-to-r from-[#cc785c]/10 to-[#b86246]/10 hover:from-[#cc785c]/25 hover:to-[#b86246]/25 text-[#cc785c] hover:text-white text-xs font-semibold tracking-wide transition-all duration-300 hover:scale-105 active:scale-95 shadow-[0_0_15px_rgba(204,120,92,0.1)] hover:shadow-[0_0_20px_rgba(204,120,92,0.25)] flex items-center gap-2 mx-auto cursor-pointer outline-none"
  ```

- [ ] **Step 2: Modernize Exit Loading Overlay (isExiting)**
Update the final app launching screen:
- Overlay background: `bg-[#051A1A]`
- Progress bar container: `bg-white/5 border-white/5`
- Progress bar fill: `bg-gradient-to-r from-[#cc785c] to-[#a8583c] shadow-[0_0_8px_#cc785c]`
- Text status updates: `text-white/60` and `text-white/95`

- [ ] **Step 3: Commit transition screens updates**
```bash
git add apps/web/src/pages/LoginPage.tsx
git commit -m "feat: modernize successful login maps, flags, and exit progress screen"
```

---

### Task 5: Verify Implementation and E2E Tests
Confirm that the modernized login page is correctly coded, does not throw compilation/syntax errors, and passes all E2E test scripts.

**Files:**
- Test: `apps/web/e2e/tests/auth.spec.ts`

- [ ] **Step 1: Check build and syntax errors**
Run: `npm run build` inside `apps/web` to confirm Vite compiles correctly.

- [ ] **Step 2: Run Playwright E2E tests**
Run: `npx playwright test e2e/tests/auth.spec.ts` inside `apps/web` to verify auth flows still succeed.
Expected: 3 tests passed.

- [ ] **Step 3: Final check and commit**
Ensure all changes are clean and committed.
