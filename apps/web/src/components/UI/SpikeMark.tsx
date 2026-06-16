interface SpikeMarkProps {
  size?: number;
  color?: string;
  style?: React.CSSProperties;
}

export function SpikeMark({ size = 16, color = "currentColor", style = {} }: SpikeMarkProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 16 16"
      fill="none"
      style={style}
      aria-hidden="true"
    >
      <path
        d="M8 1v14M1 8h14M2.9 2.9l10.2 10.2M13.1 2.9L2.9 13.1"
        stroke={color}
        strokeWidth="1.6"
        strokeLinecap="round"
      />
    </svg>
  );
}
