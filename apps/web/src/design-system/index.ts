/**
 * HistoriAI Design System
 *
 * A comprehensive token-based design system for the HistoriAI
 * Vietnamese historical research interface.
 *
 * @example
 * import { tokens, getTheme } from '@/design-system';
 *
 * // Access tokens directly
 * const primary = tokens.color.brand.primary.light;
 *
 * // Get resolved theme for current mode
 * const theme = getTheme('dark');
 */

export { tokens } from './tokens';
export { getTheme, generateCSSVariables } from './theme';
export type { Tokens } from './tokens';
export type { ColorMode, ResolvedTheme } from './theme';
