# Design Spec: HistoriAI Login Modernization (The Ethereal Archive)

**Date**: 2026-06-18  
**Topic**: Modernization of the Login/Register Page to "The Ethereal Archive" design style.

---

## 1. Product Overview

- **The Pitch**: A high-end academic entry point for HistoriAI. It uses an Apple-like glassmorphic split screen to marry modern spatial computing aesthetics with Vietnamese historical symbols.
- **Audience**: Historians, academic researchers, and serious history enthusiasts.
- **Core Aesthetic**: Deep teals, frosted glass paneling, gold/bronze highlights, slowly rotating cultural watermarks, and smooth cinematic transitions.

---

## 2. Page Layout & Structure

The interface adapts responsively across devices:

### 2.1 Desktop Layout (50/50 Split)
- **Left Column (Showcase)**: 
  - 50% screen width, sticky.
  - Background: Centered radial gradient blending from dark forest/teal `#0D3E3E` at the top-left to a near-black obsidian teal `#051A1A` at the bottom-right.
  - Content:
    - Slowly rotating SVG watermark of the Dong Son Bronze Drum in the background.
    - Rising cinematic embers using custom CSS keyframes.
    - A decorative glowing border framing a container containing the Vietnam Map and national symbol transitions.
- **Right Column (Auth Form)**:
  - 50% screen width.
  - Form wrapper centered on the page.
  - Form resides in a multi-layered glassmorphic panel (`bg-[#0B3030]/40 backdrop-blur-md border border-white/10 shadow-[0_4px_30px_rgba(0,0,0,0.2)]`).

### 2.2 Mobile/Tablet Layout (Single Column Stack)
- The Left Column (Showcase) is hidden to preserve screen real estate.
- The background gradient of the page becomes the full-screen radial teal gradient.
- The auth form card sits centered horizontally and vertically on the viewport, filling the available space up to a maximum width of `420px`.

---

## 3. Colors & Typography (Tokens)

All color tokens leverage the existing design system variables from `index.css` or fall back to high-end CSS values matching "The Ethereal Archive":

- **Brand Primary (Bronze/Gold)**: `#cc785c` (falls back to `var(--color-primary)`).
- **Secondary Accent (Amber/Gold)**: `#d4af37`.
- **Obsidian Dark (Deep Teal)**: `#051A1A`.
- **Forest Highlight**: `#0D3E3E`.
- **Glass Card Background**: `rgba(11, 48, 48, 0.4)` / `rgba(255, 255, 255, 0.03)` with `backdrop-blur-md`.
- **Glass Card Border**: `rgba(255, 255, 255, 0.1)` (matching `var(--color-surface-border)`).
- **Text (Header/Active)**: `#ffffff` / `rgba(255, 255, 255, 0.95)` (matching `var(--color-text)`).
- **Text (Muted/Placeholder)**: `rgba(255, 255, 255, 0.6)` (matching `var(--color-muted)`).

---

## 4. Interactive States

### 4.1 Form Inputs (Email, Username, Password)
- **Normal State**: `bg-white/5 border border-white/10 text-white rounded-xl`.
- **Focus State**: `border-[#cc785c] bg-white/10 ring-2 ring-[#cc785c]/10 outline-none transition-all duration-200`.

### 4.2 Submit Buttons
- **Normal State**: Gradient background `from-[#cc785c] to-[#a8583c]`, bold white text, subtle shadow.
- **Hover State**: Slight zoom (`scale-[1.01]`), increased shadow blur.
- **Active State**: Slight shrink (`scale-[0.99]`) for tactical feedback.

### 4.3 Tabs (Login / Register)
- Tab selector switches with a sliding indicator or transition-based active class (`bg-[#cc785c] text-white shadow-sm` vs. `text-white/60 hover:text-white`).

---

## 5. Transition States & Success Flows

Upon successful login or registration, the application triggers a two-phase cinematic transition sequence:

### 5.1 Successful Verification Page Transition (`isTransitioning === true`)
1. **Right Column (Form)**: Fades out smoothly (`opacity-0 pointer-events-none`).
2. **Left Column (Showcase)**: Expands dynamically via flex/width animations to cover 100% of the viewport width.
3. **Showcase Visuals**:
   - The Vietnam Map container scales up gracefully.
   - The Sacred Flag emblem gains a subtle shimmering satin overlay.
   - The user is presented with historical loading quotes (e.g. *„Sông núi nước Nam vua Nam ở...”*), transitioning every 1000ms.
4. **Interactivity**: The user can click "Tiếp tục tiến vào hệ thống" to trigger the application startup sequence.

### 5.2 Application Boot Transition (`isExiting === true`)
1. An overlay with ambient glowing lights (`#cc785c/10`) centers on a spinning lotus logo.
2. A thin, gold-gradient progress bar tracks preparation from 0% to 100% over 2.4s.
3. Preparation status texts cycle automatically:
   - `0% - 30%`: "Đang kết nối thư viện tri thức..."
   - `30% - 65%`: "Đang phân tích bản đồ tri thức lịch sử..."
   - `65% - 88%`: "Đang khởi tạo tác nhân nghiên cứu AI..."
   - `88% - 100%`: "Đang đồng bộ hóa phiên làm việc..."
4. Once progress reaches 100%, the app store updates state, triggering the route redirect to `/chat`.

---

## 6. Verification Plan

- Check layout responsiveness on desktop vs. mobile resolutions using Chrome DevTools.
- Verify that password toggle (visibility/hidden eye icon) functions without layout shift.
- Test login form submission fails gracefully with a styled glassmorphic alert box.
- Verify that successful validation triggers the `isTransitioning` state, expanding the left panel to full-screen width with correct map paths and flag borders.
- Check that the `isExiting` progress bar runs smoothly to 100% and then redirects to `/chat` successfully.
