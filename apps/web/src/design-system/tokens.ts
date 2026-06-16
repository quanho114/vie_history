/**
 * HistoriAI Design Token System
 *
 * Structure: Design Token → Component Token → CSS Variable
 * Supports: Light/Dark modes, Vietnamese cultural accent colors
 *
 * Brand colors are inspired by Vietnamese imperial aesthetics:
 * - Đỏ son cổ (Traditional vermillion red)
 * - Vàng son (Gilded gold)
 * - Xanh lục (Imperial green)
 */

export const tokens = {
  // ─── Color Semantics ────────────────────────────────────────────────────
  color: {
    // Brand — Vietnamese imperial-inspired colors
    brand: {
      primary:   { light: '#C41E3A', dark: '#E63950' }, // Đỏ son cổ (Traditional vermillion)
      secondary: { light: '#D4AF37', dark: '#E8C44A' }, // Vàng son cổ (Gilded gold)
      accent:     { light: '#2C5F2D', dark: '#4A9B4E' }, // Xanh lục cổ (Imperial green)
    },

    // Semantic colors for UI feedback
    semantic: {
      success:  { light: '#16A34A', dark: '#4ADE80' },
      warning:  { light: '#D97706', dark: '#F59E0B' },
      error:    { light: '#DC2626', dark: '#F87171' },
      info:     { light: '#2563EB', dark: '#60A5FA' },
    },

    // Neutral palette
    neutral: {
      0:   '#FFFFFF',
      50:  '#FAFAFA',
      100: '#F5F5F5',
      200: '#E5E5E5',
      300: '#D4D4D4',
      400: '#A3A3A3',
      500: '#737373',
      600: '#525252',
      700: '#404040',
      800: '#262626',
      900: '#171717',
      950: '#0A0A0A',
    },

    // Text colors
    text: {
      primary:   { light: '#171717', dark: '#FAFAFA' },
      secondary: { light: '#525252', dark: '#A3A3A3' },
      tertiary:  { light: '#737373', dark: '#737373' },
      inverse:   { light: '#FFFFFF', dark: '#171717' },
    },
  },

  // ─── Typography ────────────────────────────────────────────────────────
  typography: {
    fontFamily: {
      display: '"EB Garamond", "Playfair Display", "Noto Serif", Georgia, serif',
      body: '"Inter", "Noto Sans", system-ui, sans-serif',
      mono: '"JetBrains Mono", "Fira Code", ui-monospace, monospace',
    },
    fontSize: {
      xs:   '0.75rem',    // 12px
      sm:   '0.875rem',   // 14px
      base: '1rem',        // 16px
      lg:   '1.125rem',   // 18px
      xl:   '1.25rem',    // 20px
      '2xl': '1.5rem',    // 24px
      '3xl': '1.875rem',  // 30px
      '4xl': '2.25rem',   // 36px
      '5xl': '3rem',      // 48px
    },
    fontWeight: {
      normal:   400,
      medium:   500,
      semibold: 600,
      bold:     700,
    },
    lineHeight: {
      tight:   1.25,
      normal:  1.5,
      relaxed: 1.75,
    },
    letterSpacing: {
      tight:  '-0.025em',
      normal: '0',
      wide:   '0.025em',
    },
  },

  // ─── Spacing ───────────────────────────────────────────────────────────
  spacing: {
    0:   '0',
    px:  '1px',
    0.5: '0.125rem',  // 2px
    1:   '0.25rem',    // 4px
    1.5: '0.375rem',   // 6px
    2:   '0.5rem',     // 8px
    2.5: '0.625rem',   // 10px
    3:   '0.75rem',    // 12px
    3.5: '0.875rem',    // 14px
    4:   '1rem',        // 16px
    5:   '1.25rem',     // 20px
    6:   '1.5rem',      // 24px
    8:   '2rem',        // 32px
    10:  '2.5rem',      // 40px
    12:  '3rem',        // 48px
    16:  '4rem',        // 64px
  },

  // ─── Border Radius ─────────────────────────────────────────────────────
  radius: {
    none: '0',
    sm:   '0.25rem',   // 4px
    md:   '0.375rem',   // 6px
    lg:   '0.5rem',    // 8px
    xl:   '0.75rem',   // 12px
    '2xl': '1rem',     // 16px
    full: '9999px',
  },

  // ─── Shadows ───────────────────────────────────────────────────────────
  shadow: {
    sm:   '0 1px 2px 0 rgb(0 0 0 / 0.05)',
    md:   '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)',
    lg:   '0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)',
    xl:   '0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1)',
    inner: 'inset 0 2px 4px 0 rgb(0 0 0 / 0.05)',
  },

  // ─── Animation ─────────────────────────────────────────────────────────
  animation: {
    duration: {
      fast:   '150ms',
      normal: '300ms',
      slow:   '500ms',
    },
    easing: {
      default: 'cubic-bezier(0.4, 0, 0.2, 1)',
      in:      'cubic-bezier(0, 0, 0.2, 1)',
      out:     'cubic-bezier(0.4, 0, 1, 1)',
      bounce:  'cubic-bezier(0.68, -0.55, 0.265, 1.55)',
    },
  },

  // ─── Z-Index ────────────────────────────────────────────────────────────
  zIndex: {
    dropdown:        1000,
    sticky:          1020,
    fixed:           1030,
    modalBackdrop:   1040,
    modal:           1050,
    popover:         1060,
    tooltip:         1070,
  },
} as const;

export type Tokens = typeof tokens;
