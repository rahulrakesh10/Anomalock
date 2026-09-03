type IconProps = { className?: string };

const base = {
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.8,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
};

export function ShieldIcon({ className }: IconProps) {
  return (
    <svg {...base} className={className}>
      <path d="M12 3l7 3v6c0 4.5-3 7.7-7 9-4-1.3-7-4.5-7-9V6l7-3z" />
      <path d="M9 12l2 2 4-4" />
    </svg>
  );
}

export function UserCheckIcon({ className }: IconProps) {
  return (
    <svg {...base} className={className}>
      <circle cx="9" cy="8" r="3.2" />
      <path d="M3.5 20c0-3.6 2.5-6 5.5-6s5.5 2.4 5.5 6" />
      <path d="M16 11l2 2 3.5-3.5" />
    </svg>
  );
}

export function DeviceSwitchIcon({ className }: IconProps) {
  return (
    <svg {...base} className={className}>
      <rect x="3" y="4" width="12" height="9" rx="1.5" />
      <path d="M3 16h12" />
      <rect x="17" y="9" width="5" height="9" rx="1" />
    </svg>
  );
}

export function PlaneIcon({ className }: IconProps) {
  return (
    <svg {...base} className={className}>
      <path d="M2.5 12.5l19-6.5-6.5 19-2.3-8.2-8.2-2.3z" />
      <path d="M12.7 11.3l-3.7 3.7" />
    </svg>
  );
}

export function PulseIcon({ className }: IconProps) {
  return (
    <svg {...base} className={className}>
      <path d="M2 12h4l2 6 4-14 3 8h7" />
    </svg>
  );
}

export function ChartIcon({ className }: IconProps) {
  return (
    <svg {...base} className={className}>
      <path d="M4 20V10" />
      <path d="M11 20V4" />
      <path d="M18 20v-7" />
      <path d="M2 20h20" />
    </svg>
  );
}

export function PlayIcon({ className }: IconProps) {
  return (
    <svg {...base} className={className} fill="currentColor" stroke="none">
      <path d="M6 4.5v15l13-7.5-13-7.5z" />
    </svg>
  );
}
