import type { Meta, StoryObj } from '@storybook/react';
import { Button } from '../src/components/ui';

/**
 * HistoriAI Button component stories.
 * 
 * Demonstrates the Button component with all variants and states.
 * The Button component supports primary, secondary, ghost, and icon variants.
 */
const meta: Meta<typeof Button> = {
  title: 'Design System/Button',
  component: Button,
  tags: ['autodocs'],
  parameters: {
    docs: {
      description: {
        component: `
Button component for HistoriAI — Vietnamese historical research interface.

**Design rationale**: Uses brand coral (#cc785c) for primary actions,
with secondary and ghost variants for less prominent interactions.

**Accessibility**: Full keyboard navigation, ARIA labels, focus rings.
`
      }
    },
    layout: 'centered'
  },
  argTypes: {
    variant: {
      control: 'select',
      options: ['primary', 'secondary', 'ghost', 'icon'],
      description: 'Visual variant of the button'
    },
    size: {
      control: 'select',
      options: ['sm', 'md', 'lg'],
      description: 'Size of the button'
    },
    disabled: {
      control: 'boolean',
      description: 'Disabled state'
    }
  },
  args: {
    children: 'Tra cứu lịch sử',
    variant: 'primary',
    size: 'md'
  }
};

export default meta;
type Story = StoryObj<typeof meta>;

// ─── Stories ──────────────────────────────────────────────────────────────────

export const Primary: Story = {
  args: {
    children: 'Tra cứu lịch sử',
    variant: 'primary'
  }
};

export const Secondary: Story = {
  args: {
    children: 'Xem chi tiết',
    variant: 'secondary'
  }
};

export const Ghost: Story = {
  args: {
    children: 'Bỏ qua',
    variant: 'ghost'
  }
};

export const Disabled: Story = {
  args: {
    children: 'Không khả dụng',
    variant: 'primary',
    disabled: true
  }
};

export const SmallSize: Story = {
  args: {
    children: 'Nhỏ',
    variant: 'primary',
    size: 'sm'
  }
};

export const LargeSize: Story = {
  args: {
    children: 'Lớn',
    variant: 'primary',
    size: 'lg'
  }
};

export const AllVariants: Story = {
  render: () => (
    <div className="flex flex-wrap gap-4">
      <Button variant="primary">Tra cứu</Button>
      <Button variant="secondary">Xem thêm</Button>
      <Button variant="ghost">Bỏ qua</Button>
      <Button variant="primary" disabled>Không khả dụng</Button>
    </div>
  ),
  parameters: {
    controls: { disable: true }
  }
};

export const AllSizes: Story = {
  render: () => (
    <div className="flex items-center gap-4">
      <Button size="sm" variant="primary">Nhỏ</Button>
      <Button size="md" variant="primary">Trung bình</Button>
      <Button size="lg" variant="primary">Lớn</Button>
    </div>
  ),
  parameters: {
    controls: { disable: true }
  }
};
