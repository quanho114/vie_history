import { cn } from "@/lib/utils/cn";

/* ========================================
   Callout Card (Coral Full-bleed)
   ======================================== */

interface CalloutCoralProps {
  children: React.ReactNode;
  className?: string;
}

export function CalloutCoral({ children, className }: CalloutCoralProps) {
  return (
    <div className={cn("callout-coral", className)}>
      {children}
    </div>
  );
}

/* ========================================
   Callout Card Variants
   ======================================== */

interface CalloutCardProps {
  children: React.ReactNode;
  variant?: "info" | "warning" | "success" | "error";
  className?: string;
}

export function CalloutCard({ children, variant = "info", className }: CalloutCardProps) {
  const variantStyles = {
    info: "bg-surface-card border border-hairline",
    warning: "bg-amber/10 border border-amber/30",
    success: "bg-success/10 border border-success/30",
    error: "bg-error/10 border border-error/30",
  };

  return (
    <div
      className={cn(
        "rounded-lg p-4 my-4",
        variantStyles[variant],
        className
      )}
    >
      {children}
    </div>
  );
}

/* ========================================
   Badge Components
   ======================================== */

interface BadgeProps {
  children: React.ReactNode;
  variant?: "default" | "coral" | "teal" | "amber";
  className?: string;
}

export function Badge({ children, variant = "default", className }: BadgeProps) {
  const variantStyles = {
    default: "bg-surface-card text-ink",
    coral: "bg-coral text-on-primary",
    teal: "bg-teal/10 text-teal border border-teal/30",
    amber: "bg-amber/10 text-amber border border-amber/30",
  };

  return (
    <span
      className={cn(
        "inline-flex items-center px-2.5 py-1",
        "text-[11px] font-medium rounded-full",
        variantStyles[variant],
        className
      )}
    >
      {children}
    </span>
  );
}

/* ========================================
   Button Components
   ======================================== */

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost" | "icon";
  size?: "sm" | "md" | "lg";
  children: React.ReactNode;
}

export function Button({
  variant = "primary",
  size = "md",
  children,
  className,
  ...props
}: ButtonProps) {
  const variantStyles = {
    primary: "btn-primary",
    secondary: "btn-secondary",
    ghost: "bg-transparent border-none hover:bg-surface-soft",
    icon: "btn-icon",
  };

  const sizeStyles = {
    sm: "h-8 px-3 text-[13px]",
    md: "h-10 px-5 text-[14px]",
    lg: "h-12 px-6 text-[15px]",
  };

  return (
    <button
      className={cn(
        "btn",
        variantStyles[variant],
        variant !== "icon" && sizeStyles[size],
        className
      )}
      {...props}
    >
      {children}
    </button>
  );
}

/* ========================================
   Icon Button
   ======================================== */

interface IconButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  icon: React.ReactNode;
  size?: "sm" | "md" | "lg";
  variant?: "default" | "ghost";
}

export function IconButton({
  icon,
  size = "md",
  variant = "default",
  className,
  ...props
}: IconButtonProps) {
  const sizeStyles = {
    sm: "w-8 h-8",
    md: "w-9 h-9",
    lg: "w-10 h-10",
  };

  const variantStyles = {
    default: "border border-hairline bg-canvas hover:bg-surface-card",
    ghost: "border-none bg-transparent hover:bg-surface-soft",
  };

  return (
    <button
      className={cn(
        "rounded-full flex items-center justify-center",
        "text-muted hover:text-ink transition-colors",
        sizeStyles[size],
        variantStyles[variant],
        className
      )}
      {...props}
    >
      {icon}
    </button>
  );
}

/* ========================================
   Search Input
   ======================================== */

interface SearchInputProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  className?: string;
}

export function SearchInput({
  value,
  onChange,
  placeholder = "Tìm kiếm...",
  className,
}: SearchInputProps) {
  return (
    <div className={cn("relative", className)}>
      <svg
        className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-soft pointer-events-none"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <circle cx="11" cy="11" r="8" />
        <line x1="21" y1="21" x2="16.65" y2="16.65" />
      </svg>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className={cn(
          "w-full pl-9 pr-4 py-2",
          "border border-hairline rounded-md",
          "bg-canvas text-body-text text-[13px]",
          "placeholder:text-soft",
          "focus:outline-none focus:border-coral focus:ring-3 focus:ring-[rgba(204,120,92,.12)]",
          "transition-all duration-150"
        )}
      />
    </div>
  );
}

/* ========================================
   Divider
   ======================================== */

interface DividerProps {
  orientation?: "horizontal" | "vertical";
  className?: string;
}

export function Divider({ orientation = "horizontal", className }: DividerProps) {
  return (
    <div
      className={cn(
        orientation === "horizontal" ? "border-t border-hairline" : "border-l border-hairline",
        className
      )}
    />
  );
}

/* ========================================
   Tag Component
   ======================================== */

interface TagProps {
  children: React.ReactNode;
  onClick?: () => void;
  variant?: "default" | "coral";
  className?: string;
}

export function Tag({ children, onClick, variant = "default", className }: TagProps) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "tag",
        variant === "coral" && "border-coral text-coral",
        className
      )}
      disabled={!onClick}
    >
      {children}
    </button>
  );
}

/* ========================================
   Tooltip Wrapper
   ======================================== */

interface TooltipProps {
  children: React.ReactNode;
  content: string;
  position?: "top" | "bottom" | "left" | "right";
}

export function Tooltip({ children, content, position = "top" }: TooltipProps) {
  const positionStyles = {
    top: "bottom-full left-1/2 -translate-x-1/2 mb-2",
    bottom: "top-full left-1/2 -translate-x-1/2 mt-2",
    left: "right-full top-1/2 -translate-y-1/2 mr-2",
    right: "left-full top-1/2 -translate-y-1/2 ml-2",
  };

  return (
    <div className="relative group inline-block">
      {children}
      <div
        className={cn(
          "absolute z-50 px-2 py-1",
          "bg-surface-dark text-on-dark text-[12px]",
          "rounded whitespace-nowrap",
          "opacity-0 group-hover:opacity-100 transition-opacity",
          positionStyles[position]
        )}
      >
        {content}
      </div>
    </div>
  );
}

/* ========================================
   Loading Spinner
   ======================================== */

interface SpinnerProps {
  size?: "sm" | "md" | "lg";
  className?: string;
}

export function Spinner({ size = "md", className }: SpinnerProps) {
  const sizeStyles = {
    sm: "w-4 h-4",
    md: "w-5 h-5",
    lg: "w-6 h-6",
  };

  return (
    <svg
      className={cn("animate-spin text-coral", sizeStyles[size], className)}
      viewBox="0 0 24 24"
      fill="none"
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
      />
    </svg>
  );
}

/* ========================================
   Avatar Component
   ======================================== */

interface AvatarProps {
  name?: string;
  src?: string;
  size?: "sm" | "md" | "lg";
  className?: string;
}

export function Avatar({ name, src, size = "md", className }: AvatarProps) {
  const initials = name?.[0]?.toUpperCase() || "?";
  const sizeStyles = {
    sm: "w-8 h-8 text-xs",
    md: "w-10 h-10 text-sm",
    lg: "w-12 h-12 text-base",
  };

  if (src) {
    return (
      <img
        src={src}
        alt={name || "Avatar"}
        className={cn("rounded-full object-cover", sizeStyles[size], className)}
      />
    );
  }

  return (
    <div
      className={cn(
        "rounded-full bg-coral flex items-center justify-center text-on-primary font-medium",
        sizeStyles[size],
        className
      )}
    >
      {initials}
    </div>
  );
}

/* ========================================
   Status Dot
   ======================================== */

interface StatusDotProps {
  status: "online" | "offline" | "busy" | "away";
  className?: string;
}

export function StatusDot({ status, className }: StatusDotProps) {
  const statusColors = {
    online: "bg-success",
    offline: "bg-soft",
    busy: "bg-error",
    away: "bg-amber",
  };

  return (
    <span
      className={cn(
        "w-2 h-2 rounded-full",
        statusColors[status],
        className
      )}
    />
  );
}

/* ========================================
   Empty State Component
   ======================================== */

interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: React.ReactNode;
  className?: string;
}

export function EmptyState({
  icon,
  title,
  description,
  action,
  className,
}: EmptyStateProps) {
  return (
    <div className={cn("empty-state", className)}>
      {icon && <div className="mb-4">{icon}</div>}
      <h3 className="font-display text-[18px] font-normal text-ink mb-2">{title}</h3>
      {description && <p className="text-[14px] text-muted mb-6">{description}</p>}
      {action}
    </div>
  );
}

/* ========================================
   Card Component
   ======================================== */

interface CardProps {
  children: React.ReactNode;
  className?: string;
  padding?: "none" | "sm" | "md" | "lg";
  hover?: boolean;
}

export function Card({
  children,
  className,
  padding = "md",
  hover = false,
}: CardProps) {
  const paddingStyles = {
    none: "",
    sm: "p-3",
    md: "p-4",
    lg: "p-6",
  };

  return (
    <div
      className={cn(
        "bg-surface-card border border-hairline rounded-lg",
        paddingStyles[padding],
        hover && "hover:border-coral/30 transition-colors cursor-pointer",
        className
      )}
    >
      {children}
    </div>
  );
}

// ─── Re-export Skeleton Components ──────────────────────────────────────────
export {
  Skeleton,
  ChatMessageSkeleton,
  UserMessageSkeleton,
  AIMessageSkeleton,
  DocumentCardSkeleton,
  ChatSkeleton,
  AgentTraceSkeleton,
  PageSkeleton,
  TableRowSkeleton,
  TableSkeleton,
} from './skeleton';
