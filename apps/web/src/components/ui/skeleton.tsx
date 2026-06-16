import { cn } from '@/lib/utils/cn';

/* ========================================
   Skeleton Component
   ======================================== */

interface SkeletonProps {
  className?: string;
}

export function Skeleton({ className }: SkeletonProps) {
  return (
    <div
      className={cn(
        'animate-pulse rounded-md bg-[var(--hairline)] dark:bg-[var(--surface-soft)]',
        className
      )}
      aria-hidden="true"
    />
  );
}

/* ========================================
   Chat Message Skeleton
   ======================================== */

export function ChatMessageSkeleton() {
  return (
    <div
      className="flex gap-3 p-4"
      aria-busy="true"
      aria-label="Đang tải tin nhắn"
    >
      {/* Avatar skeleton */}
      <Skeleton className="h-10 w-10 rounded-full shrink-0" />

      {/* Content skeleton */}
      <div className="flex-1 space-y-2">
        <Skeleton className="h-4 w-3/4" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-2/3" />
      </div>
    </div>
  );
}

/* ========================================
   User Message Skeleton
   ======================================== */

export function UserMessageSkeleton() {
  return (
    <div
      className="flex justify-end p-4"
      aria-busy="true"
      aria-label="Đang tải tin nhắn người dùng"
    >
      <Skeleton className="h-12 w-3/4 rounded-2xl rounded-br-md" />
    </div>
  );
}

/* ========================================
   AI Message Skeleton
   ======================================== */

export function AIMessageSkeleton() {
  return (
    <div
      className="flex gap-3 p-4"
      aria-busy="true"
      aria-label="Đang tải phản hồi AI"
    >
      {/* Avatar skeleton */}
      <Skeleton className="h-10 w-10 rounded-full shrink-0" />

      {/* Content skeleton */}
      <div className="flex-1 space-y-3">
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-5/6" />
        <Skeleton className="h-4 w-4/6" />

        {/* Citation skeleton */}
        <div className="pt-3 border-t border-[var(--hairline)]">
          <div className="flex gap-2">
            <Skeleton className="h-6 w-20 rounded-full" />
            <Skeleton className="h-6 w-32 rounded-full" />
          </div>
        </div>
      </div>
    </div>
  );
}

/* ========================================
   Document Card Skeleton
   ======================================== */

export function DocumentCardSkeleton() {
  return (
    <div
      className="p-4 border border-[var(--hairline)] rounded-lg space-y-3"
      aria-busy="true"
      aria-label="Đang tải thông tin tài liệu"
    >
      <Skeleton className="h-5 w-3/4" />
      <Skeleton className="h-4 w-full" />
      <Skeleton className="h-4 w-full" />
      <div className="flex gap-2 pt-2">
        <Skeleton className="h-6 w-16 rounded-full" />
        <Skeleton className="h-6 w-20 rounded-full" />
      </div>
      <Skeleton className="h-3 w-1/2" />
    </div>
  );
}

/* ========================================
   Full Chat Skeleton (Initial Load)
   ======================================== */

export function ChatSkeleton() {
  return (
    <div
      className="flex flex-col gap-4 p-6"
      aria-busy="true"
      aria-label="Đang tải cuộc trò chuyện"
    >
      {/* User message */}
      <div className="flex justify-end">
        <Skeleton className="h-12 w-2/3 rounded-2xl rounded-br-md" />
      </div>

      {/* AI message with citation */}
      <div className="flex gap-3">
        <Skeleton className="h-10 w-10 rounded-full shrink-0" />
        <div className="flex-1 space-y-3">
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-5/6" />
          <Skeleton className="h-4 w-4/6" />
          <div className="pt-2 border-t border-[var(--hairline)]">
            <div className="flex gap-2">
              <Skeleton className="h-6 w-20 rounded-full" />
              <Skeleton className="h-6 w-24 rounded-full" />
            </div>
          </div>
        </div>
      </div>

      {/* Second user message */}
      <div className="flex justify-end">
        <Skeleton className="h-10 w-1/2 rounded-2xl rounded-br-md" />
      </div>

      {/* Second AI message */}
      <div className="flex gap-3">
        <Skeleton className="h-10 w-10 rounded-full shrink-0" />
        <div className="flex-1 space-y-3">
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-3/4" />
        </div>
      </div>
    </div>
  );
}

/* ========================================
   Agent Trace Skeleton
   ======================================== */

export function AgentTraceSkeleton() {
  return (
    <div
      className="mt-4 border border-[var(--hairline)] rounded-xl bg-white overflow-hidden"
      aria-busy="true"
      aria-label="Đang tải quá trình suy luận"
    >
      {/* Header */}
      <div className="px-4 py-3 bg-[var(--surface-soft)] border-b border-[var(--hairline)]">
        <div className="flex items-center gap-2.5">
          <Skeleton className="h-6 w-6 rounded-lg" />
          <div className="space-y-1">
            <Skeleton className="h-3 w-32" />
            <Skeleton className="h-2 w-48" />
          </div>
        </div>
      </div>

      {/* Expanded content */}
      <div className="p-5 space-y-4">
        {/* Agent steps skeleton */}
        {[1, 2, 3].map((i) => (
          <div key={i} className="flex items-start gap-4">
            <Skeleton className="h-7 w-7 rounded-full" />
            <div className="flex-1 bg-[var(--surface-soft)] border border-[var(--hairline)] rounded-xl p-3.5">
              <div className="flex justify-between items-center mb-1">
                <Skeleton className="h-3.5 w-24" />
                <Skeleton className="h-4 w-16 rounded-full" />
              </div>
              <Skeleton className="h-3 w-full" />
              <Skeleton className="h-3 w-4/5 mt-1" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ========================================
   Page Skeleton
   ======================================== */

export function PageSkeleton() {
  return (
    <div
      className="flex items-center justify-center h-screen"
      role="status"
      aria-label="Đang tải"
    >
      <div className="animate-pulse flex flex-col items-center gap-4">
        <Skeleton className="w-12 h-12 rounded-full" />
        <Skeleton className="h-4 w-32" />
      </div>
    </div>
  );
}

/* ========================================
   Table Row Skeleton
   ======================================== */

interface TableRowSkeletonProps {
  columns?: number;
}

export function TableRowSkeleton({ columns = 4 }: TableRowSkeletonProps) {
  return (
    <tr aria-busy="true" aria-label="Đang tải hàng">
      {Array.from({ length: columns }).map((_, i) => (
        <td key={i} className="px-4 py-3">
          <Skeleton className="h-4 w-full" />
        </td>
      ))}
    </tr>
  );
}

export function TableSkeleton({ rows = 5, columns = 4 }: TableRowSkeletonProps & { rows?: number }) {
  return (
    <div className="border border-[var(--hairline)] rounded-lg overflow-hidden">
      <table className="w-full">
        <thead className="bg-[var(--surface-soft)]">
          <tr>
            {Array.from({ length: columns }).map((_, i) => (
              <th key={i} className="px-4 py-3 text-left">
                <Skeleton className="h-3 w-20" />
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {Array.from({ length: rows }).map((_, i) => (
            <TableRowSkeleton key={i} columns={columns} />
          ))}
        </tbody>
      </table>
    </div>
  );
}
