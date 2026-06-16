import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        /* Canvas & Surfaces */
        canvas: "var(--canvas)",
        "surface-soft": "var(--surface-soft)",
        "surface-card": "var(--surface-card)",
        "surface-strong": "var(--surface-strong)",
        "surface-dark": "var(--surface-dark)",
        "surface-dark-el": "var(--surface-dark-el)",
        "surface-dark-soft": "var(--surface-dark-soft)",

        /* Ingest & Document Pages Scales */
        surface: {
          50: "var(--canvas)",
          100: "var(--surface-soft)",
          200: "var(--hairline)",
          300: "var(--surface-card)",
          400: "var(--soft)",
          500: "var(--muted)",
          600: "var(--body-text)",
          700: "var(--body-strong)",
          800: "var(--ink)",
          900: "var(--surface-dark)",
        },

        primary: {
          50: "#fdf8f6",
          100: "#fbeee9",
          200: "#f7ddd4",
          300: "#f2c5b7",
          400: "#e9a48f",
          500: "var(--coral)",
          600: "var(--coral-hover)",
          700: "#994d34",
          800: "#7f402b",
          900: "#6a3726",
          DEFAULT: "var(--coral)",
        },

        /* Accent */
        coral: {
          DEFAULT: "var(--coral)",
          hover: "var(--coral-hover)",
          disabled: "var(--coral-disabled)",
        },
        teal: "var(--teal)",
        amber: "var(--amber)",

        /* Text */
        ink: "var(--ink)",
        "body-strong": "var(--body-strong)",
        "body-text": "var(--body-text)",
        muted: "var(--muted)",
        soft: "var(--soft)",
        "on-primary": "var(--on-primary)",
        "on-dark": "var(--on-dark)",
        "on-dark-soft": "var(--on-dark-soft)",

        /* Border */
        hairline: "var(--hairline)",
        "hairline-soft": "var(--hairline-soft)",

        /* Semantic */
        success: "var(--success)",
        warning: "var(--warning)",
        error: "var(--error)",
      },
      fontFamily: {
        display: ["EB Garamond", "Tiempos Headline", "Cormorant Garamond", "Georgia", "Times New Roman", "serif"],
        sans: ["Inter", "-apple-system", "BlinkMacSystemFont", "Segoe UI", "Roboto", "sans-serif"],
        mono: ["JetBrains Mono", "Fira Code", "monospace"],
      },
      fontSize: {
        "display-sm": ["18px", { lineHeight: "1.2", letterSpacing: "-0.3px" }],
        "display-md": ["22px", { lineHeight: "1.15", letterSpacing: "-0.5px" }],
        "display-lg": ["32px", { lineHeight: "1.1", letterSpacing: "-0.8px" }],
        "body-xs": ["11px", { lineHeight: "1.4" }],
        "body-sm": ["13px", { lineHeight: "1.4" }],
      },
      spacing: {
        "space-xxs": "4px",
        "space-xs": "8px",
        "space-sm": "12px",
        "space-md": "16px",
        "space-lg": "24px",
        "space-xl": "32px",
        "space-xxl": "48px",
        "space-section": "96px",
      },
      borderRadius: {
        xs: "4px",
        sm: "6px",
        md: "8px",
        lg: "12px",
        xl: "16px",
        pill: "9999px",
      },
      boxShadow: {
        focus: "0 0 0 3px rgba(204,120,92,.12)",
        "focus-lg": "0 0 0 3px rgba(204,120,92,.1)",
      },
      maxWidth: {
        chat: "820px",
      },
    },
  },
  plugins: [],
} satisfies Config;
