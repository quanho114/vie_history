/**
 * HistoriAI Theme System
 *
 * Resolves design tokens to concrete values based on color mode.
 * Used for generating CSS custom properties or direct value access.
 */

import { tokens } from './tokens';
import type { Tokens } from './tokens';

export type ColorMode = 'light' | 'dark';

interface ResolvedTheme {
  color: {
    brand: {
      primary: string;
      secondary: string;
      accent: string;
    };
    semantic: {
      success: string;
      warning: string;
      error: string;
      info: string;
    };
    neutral: typeof tokens.color.neutral;
    text: {
      primary: string;
      secondary: string;
      tertiary: string;
      inverse: string;
    };
  };
  typography: typeof tokens.typography;
  spacing: typeof tokens.spacing;
  radius: typeof tokens.radius;
  shadow: typeof tokens.shadow;
  animation: typeof tokens.animation;
  zIndex: typeof tokens.zIndex;
}

/**
 * Resolves the theme tokens to concrete values based on the color mode.
 * This is useful for generating CSS custom properties or for components
 * that need direct token value access.
 */
export function getTheme(mode: ColorMode): ResolvedTheme {
  const isDark = mode === 'dark';

  return {
    color: {
      brand: {
        primary:   isDark ? tokens.color.brand.primary.dark   : tokens.color.brand.primary.light,
        secondary: isDark ? tokens.color.brand.secondary.dark  : tokens.color.brand.secondary.light,
        accent:    isDark ? tokens.color.brand.accent.dark     : tokens.color.brand.accent.light,
      },
      semantic: {
        success: isDark ? tokens.color.semantic.success.dark  : tokens.color.semantic.success.light,
        warning: isDark ? tokens.color.semantic.warning.dark  : tokens.color.semantic.warning.light,
        error:   isDark ? tokens.color.semantic.error.dark    : tokens.color.semantic.error.light,
        info:    isDark ? tokens.color.semantic.info.dark     : tokens.color.semantic.info.light,
      },
      neutral: tokens.color.neutral,
      text: {
        primary:   isDark ? tokens.color.text.primary.dark   : tokens.color.text.primary.light,
        secondary: isDark ? tokens.color.text.secondary.dark : tokens.color.text.secondary.light,
        tertiary:  isDark ? tokens.color.text.tertiary.dark  : tokens.color.text.tertiary.light,
        inverse:   isDark ? tokens.color.text.inverse.dark   : tokens.color.text.inverse.light,
      },
    },
    typography: tokens.typography,
    spacing: tokens.spacing,
    radius: tokens.radius,
    shadow: tokens.shadow,
    animation: tokens.animation,
    zIndex: tokens.zIndex,
  };
}

/**
 * Generates CSS custom properties string for the given mode.
 * Use this to inject theme tokens as CSS variables.
 */
export function generateCSSVariables(mode: ColorMode): string {
  const theme = getTheme(mode);
  const css: string[] = [];

  // Brand colors
  css.push(`--color-brand-primary: ${theme.color.brand.primary};`);
  css.push(`--color-brand-secondary: ${theme.color.brand.secondary};`);
  css.push(`--color-brand-accent: ${theme.color.brand.accent};`);

  // Semantic colors
  css.push(`--color-success: ${theme.color.semantic.success};`);
  css.push(`--color-warning: ${theme.color.semantic.warning};`);
  css.push(`--color-error: ${theme.color.semantic.error};`);
  css.push(`--color-info: ${theme.color.semantic.info};`);

  // Neutral colors
  Object.entries(theme.color.neutral).forEach(([key, value]) => {
    css.push(`--color-neutral-${key}: ${value};`);
  });

  // Text colors
  css.push(`--color-text-primary: ${theme.color.text.primary};`);
  css.push(`--color-text-secondary: ${theme.color.text.secondary};`);
  css.push(`--color-text-tertiary: ${theme.color.text.tertiary};`);
  css.push(`--color-text-inverse: ${theme.color.text.inverse};`);

  // Typography
  Object.entries(theme.typography.fontFamily).forEach(([key, value]) => {
    css.push(`--font-family-${key}: ${value};`);
  });
  Object.entries(theme.typography.fontSize).forEach(([key, value]) => {
    css.push(`--font-size-${key}: ${value};`);
  });
  Object.entries(theme.typography.fontWeight).forEach(([key, value]) => {
    css.push(`--font-weight-${key}: ${value};`);
  });

  // Spacing
  Object.entries(theme.spacing).forEach(([key, value]) => {
    css.push(`--spacing-${key}: ${value};`);
  });

  // Radius
  Object.entries(theme.radius).forEach(([key, value]) => {
    css.push(`--radius-${key}: ${value};`);
  });

  // Shadows
  Object.entries(theme.shadow).forEach(([key, value]) => {
    css.push(`--shadow-${key}: ${value};`);
  });

  // Animation
  Object.entries(theme.animation.duration).forEach(([key, value]) => {
    css.push(`--animation-duration-${key}: ${value};`);
  });
  Object.entries(theme.animation.easing).forEach(([key, value]) => {
    css.push(`--animation-easing-${key}: ${value};`);
  });

  // Z-Index
  Object.entries(theme.zIndex).forEach(([key, value]) => {
    css.push(`--z-index-${key}: ${value};`);
  });

  return css.join('\n');
}

// Re-export tokens for convenience
export { tokens };
export type { Tokens };
