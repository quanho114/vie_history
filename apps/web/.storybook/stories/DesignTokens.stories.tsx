import type { Meta, StoryObj } from '@storybook/react';
import { tokens, getTheme } from '../src/design-system';

/**
 * Design System Tokens for HistoriAI.
 * 
 * These tokens define the visual language of the HistoriAI interface,
 * including colors, typography, spacing, and more.
 * 
 * The design system supports:
 * - Light and dark color modes
 * - Vietnamese cultural accent colors (đỏ son, vàng son)
 * - Consistent spacing and typography
 */
const meta: Meta = {
  title: 'Design System/Tokens',
  tags: ['autodocs'],
  parameters: {
    docs: {
      description: {
        component: `
## HistoriAI Design Token System

This story demonstrates the design tokens used throughout the HistoriAI interface.

### Token Structure

\`\`\`
Design Token → Component Token → CSS Variable
\`\`\`

### Color Modes

The design system supports both light and dark modes.
Colors automatically adjust based on the current color scheme.
`
      }
    }
  },
  render: () => {
    const lightTheme = getTheme('light');
    const darkTheme = getTheme('dark');

    return (
      <div className="p-8 space-y-12 max-w-4xl">
        {/* Brand Colors */}
        <section>
          <h2 className="text-xl font-bold mb-4 font-display">Brand Colors</h2>
          <div className="grid grid-cols-3 gap-4">
            <ColorSwatch
              name="Primary"
              light={lightTheme.color.brand.primary}
              dark={darkTheme.color.brand.primary}
              description="Đỏ son cổ - Traditional vermillion"
            />
            <ColorSwatch
              name="Secondary"
              light={lightTheme.color.brand.secondary}
              dark={darkTheme.color.brand.secondary}
              description="Vàng son cổ - Gilded gold"
            />
            <ColorSwatch
              name="Accent"
              light={lightTheme.color.brand.accent}
              dark={darkTheme.color.brand.accent}
              description="Xanh lục cổ - Imperial green"
            />
          </div>
        </section>

        {/* Semantic Colors */}
        <section>
          <h2 className="text-xl font-bold mb-4 font-display">Semantic Colors</h2>
          <div className="grid grid-cols-4 gap-4">
            <ColorSwatch
              name="Success"
              light={lightTheme.color.semantic.success}
              dark={darkTheme.color.semantic.success}
            />
            <ColorSwatch
              name="Warning"
              light={lightTheme.color.semantic.warning}
              dark={darkTheme.color.semantic.warning}
            />
            <ColorSwatch
              name="Error"
              light={lightTheme.color.semantic.error}
              dark={darkTheme.color.semantic.error}
            />
            <ColorSwatch
              name="Info"
              light={lightTheme.color.semantic.info}
              dark={darkTheme.color.semantic.info}
            />
          </div>
        </section>

        {/* Typography */}
        <section>
          <h2 className="text-xl font-bold mb-4 font-display">Typography</h2>
          <div className="space-y-4">
            <div style={{ fontFamily: lightTheme.typography.fontFamily.display }}>
              <span className="text-sm text-gray-500">Display: </span>
              <span className="text-lg">HistoriAI - Vietnamese Historical Research</span>
            </div>
            <div style={{ fontFamily: lightTheme.typography.fontFamily.body }}>
              <span className="text-sm text-gray-500">Body: </span>
              <span className="text-base">Tra cứu lịch sử Việt Nam 1945-1975</span>
            </div>
            <div style={{ fontFamily: lightTheme.typography.fontFamily.mono }}>
              <span className="text-sm text-gray-500">Mono: </span>
              <code className="text-sm">const histori = "research";</code>
            </div>
          </div>
        </section>

        {/* Font Sizes */}
        <section>
          <h2 className="text-xl font-bold mb-4 font-display">Font Sizes</h2>
          <div className="space-y-2">
            {Object.entries(lightTheme.typography.fontSize).map(([key, value]) => (
              <div key={key} className="flex items-baseline gap-4">
                <span className="w-16 text-xs text-gray-500">{key}</span>
                <span style={{ fontSize: value }}>Chiến dịch Điện Biên Phủ</span>
              </div>
            ))}
          </div>
        </section>

        {/* Spacing */}
        <section>
          <h2 className="text-xl font-bold mb-4 font-display">Spacing</h2>
          <div className="flex items-end gap-2">
            {Object.entries(lightTheme.spacing).slice(0, 8).map(([key, value]) => (
              <div
                key={key}
                style={{
                  width: value,
                  height: value,
                  backgroundColor: 'var(--coral)',
                  opacity: 0.6
                }}
                title={`${key}: ${value}`}
              />
            ))}
          </div>
        </section>

        {/* Border Radius */}
        <section>
          <h2 className="text-xl font-bold mb-4 font-display">Border Radius</h2>
          <div className="flex items-center gap-4">
            {Object.entries(lightTheme.radius).map(([key, value]) => (
              <div
                key={key}
                style={{
                  width: 40,
                  height: 40,
                  backgroundColor: 'var(--coral)',
                  borderRadius: value
                }}
                title={`${key}: ${value}`}
              />
            ))}
          </div>
        </section>
      </div>
    );
  }
};

export default meta;
type Story = StoryObj<typeof meta>;

// Color Swatch Component
interface ColorSwatchProps {
  name: string;
  light: string;
  dark: string;
  description?: string;
}

function ColorSwatch({ name, light, dark, description }: ColorSwatchProps) {
  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      <div className="flex h-20">
        <div
          className="flex-1"
          style={{ backgroundColor: light }}
          title={`Light: ${light}`}
        />
        <div
          className="flex-1"
          style={{ backgroundColor: dark }}
          title={`Dark: ${dark}`}
        />
      </div>
      <div className="p-3 bg-white">
        <div className="font-medium text-sm">{name}</div>
        <div className="text-xs text-gray-500">
          {light} / {dark}
        </div>
        {description && (
          <div className="text-xs text-gray-400 mt-1">{description}</div>
        )}
      </div>
    </div>
  );
}

export const Default: Story = {};
