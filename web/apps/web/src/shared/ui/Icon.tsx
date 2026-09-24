import type { ReactNode, SVGProps } from "react";

export type IconName =
  | "alertCircle"
  | "caption"
  | "clock"
  | "checkCircle"
  | "chevronDown"
  | "chevronUp"
  | "download"
  | "edit"
  | "more"
  | "paperclip"
  | "pause"
  | "play"
  | "refresh"
  | "trash"
  | "x";

interface Props extends SVGProps<SVGSVGElement> {
  name: IconName;
  size?: number;
}

const paths: Record<IconName, ReactNode> = {
  alertCircle: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 8v4" />
      <path d="M12 16h.01" />
    </>
  ),
  caption: (
    <>
      <rect x="3" y="5" width="18" height="14" rx="2" />
      <path d="M7 10h4" />
      <path d="M13 10h4" />
      <path d="M7 14h3" />
      <path d="M12 14h5" />
    </>
  ),
  clock: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3 2" />
    </>
  ),
  checkCircle: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="m8 12 2.5 2.5L16 9" />
    </>
  ),
  chevronDown: <path d="m7 10 5 5 5-5" />,
  chevronUp: <path d="m7 14 5-5 5 5" />,
  download: (
    <>
      <path d="M12 4v10" />
      <path d="m8 10 4 4 4-4" />
      <path d="M5 19h14" />
    </>
  ),
  edit: (
    <>
      <path d="M4 20h4L19 9l-4-4L4 16v4Z" />
      <path d="m13.5 6.5 4 4" />
    </>
  ),
  more: (
    <>
      <circle cx="5" cy="12" r="1.2" />
      <circle cx="12" cy="12" r="1.2" />
      <circle cx="19" cy="12" r="1.2" />
    </>
  ),
  paperclip: (
    <path d="m8.5 12.5 5.6-5.6a3.2 3.2 0 1 1 4.5 4.5l-6.8 6.8a4.8 4.8 0 0 1-6.8-6.8l6.3-6.3" />
  ),
  pause: (
    <>
      <path d="M8 5v14" />
      <path d="M16 5v14" />
    </>
  ),
  play: <path d="m9 6 9 6-9 6V6Z" />,
  refresh: (
    <>
      <path d="M20 11a8 8 0 1 0 1 4" />
      <path d="M20 5v6h-6" />
    </>
  ),
  trash: (
    <>
      <path d="M5 7h14" />
      <path d="M9 7V4h6v3" />
      <path d="M7 7l1 13h8l1-13" />
      <path d="M10 11v5" />
      <path d="M14 11v5" />
    </>
  ),
  x: (
    <>
      <path d="m7 7 10 10" />
      <path d="m17 7-10 10" />
    </>
  ),
};

export default function Icon({ name, size = 16, ...props }: Props) {
  return (
    <svg
      aria-hidden="true"
      data-icon={name}
      fill="none"
      focusable="false"
      height={size}
      stroke="currentColor"
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth="1.8"
      viewBox="0 0 24 24"
      width={size}
      {...props}
    >
      {paths[name]}
    </svg>
  );
}
