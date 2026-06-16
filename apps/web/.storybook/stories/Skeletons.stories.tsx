import type { Meta, StoryObj } from '@storybook/react';
import { Skeleton, ChatMessageSkeleton, DocumentCardSkeleton, PageSkeleton } from '../src/components/ui/skeleton';

/**
 * Skeleton loading components for HistoriAI.
 * 
 * These components provide visual feedback during loading states,
 * improving perceived performance and user experience.
 */
const meta: Meta = {
  title: 'Design System/Skeletons',
  tags: ['autodocs'],
  parameters: {
    docs: {
      description: {
        component: `
Skeleton components provide loading placeholders that maintain
layout stability while content is being fetched.

**Usage**: Wrap these in a container with \`aria-busy="true"\` for accessibility.
`
      }
    }
  }
};

export default meta;

// ─── Stories ──────────────────────────────────────────────────────────────────

export const DefaultSkeleton: StoryObj = {
  render: () => (
    <div className="w-64 space-y-4">
      <Skeleton className="h-4 w-full" />
      <Skeleton className="h-4 w-3/4" />
      <Skeleton className="h-4 w-1/2" />
    </div>
  )
};

export const AvatarSkeleton: StoryObj = {
  render: () => (
    <div className="flex items-center gap-3">
      <Skeleton className="h-10 w-10 rounded-full" />
      <div className="space-y-2">
        <Skeleton className="h-4 w-32" />
        <Skeleton className="h-3 w-24" />
      </div>
    </div>
  )
};

export const ChatMessage: StoryObj = {
  render: () => (
    <div className="w-full max-w-md">
      <ChatMessageSkeleton />
    </div>
  )
};

export const DocumentCard: StoryObj = {
  render: () => (
    <div className="w-full max-w-sm">
      <DocumentCardSkeleton />
    </div>
  )
};

export const PageLoading: StoryObj = {
  render: () => <PageSkeleton />
};

export const MultipleChatMessages: StoryObj = {
  render: () => (
    <div className="w-full max-w-lg space-y-4">
      <div className="flex justify-end">
        <Skeleton className="h-12 w-2/3 rounded-2xl rounded-br-md" />
      </div>
      <ChatMessageSkeleton />
      <ChatMessageSkeleton />
      <div className="flex justify-end">
        <Skeleton className="h-10 w-1/2 rounded-2xl rounded-br-md" />
      </div>
    </div>
  )
};
