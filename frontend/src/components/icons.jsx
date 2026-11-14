// Small inline icons (24px grid, stroke = currentColor). All are decorative;
// the surrounding control provides the accessible name.
const base = {
  width: 20,
  height: 20,
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 2,
  strokeLinecap: 'round',
  strokeLinejoin: 'round',
  'aria-hidden': true,
  focusable: false,
};

export const MicIcon = (props) => (
  <svg {...base} {...props}>
    <rect x="9" y="2" width="6" height="12" rx="3" />
    <path d="M5 10a7 7 0 0 0 14 0M12 17v4M8 21h8" />
  </svg>
);

export const PhoneOffIcon = (props) => (
  <svg {...base} {...props}>
    <path d="M10.7 13.3a16 16 0 0 0 3.4 2.4l1.6-1.6a1.5 1.5 0 0 1 1.6-.4c1 .4 2 .6 3.1.7a1.5 1.5 0 0 1 1.4 1.5v3a1.5 1.5 0 0 1-1.6 1.5A19 19 0 0 1 2.6 4.1 1.5 1.5 0 0 1 4.1 2.5h3a1.5 1.5 0 0 1 1.5 1.4c.1 1.1.3 2.1.7 3.1a1.5 1.5 0 0 1-.4 1.6L7.3 10.2" />
    <path d="M2 2l20 20" />
  </svg>
);

export const SunIcon = (props) => (
  <svg {...base} {...props}>
    <circle cx="12" cy="12" r="4" />
    <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
  </svg>
);

export const MoonIcon = (props) => (
  <svg {...base} {...props}>
    <path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" />
  </svg>
);

export const MonitorIcon = (props) => (
  <svg {...base} {...props}>
    <rect x="2" y="3" width="20" height="14" rx="2" />
    <path d="M8 21h8M12 17v4" />
  </svg>
);

export const CopyIcon = (props) => (
  <svg {...base} {...props}>
    <rect x="9" y="9" width="12" height="12" rx="2" />
    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
  </svg>
);

export const CheckIcon = (props) => (
  <svg {...base} {...props}>
    <path d="M20 6 9 17l-5-5" />
  </svg>
);

export const XIcon = (props) => (
  <svg {...base} {...props}>
    <path d="M18 6 6 18M6 6l12 12" />
  </svg>
);

export const AlertIcon = (props) => (
  <svg {...base} {...props}>
    <circle cx="12" cy="12" r="10" />
    <path d="M12 8v4M12 16h.01" />
  </svg>
);

export const RefreshIcon = (props) => (
  <svg {...base} {...props}>
    <path d="M21 12a9 9 0 1 1-2.6-6.4L21 8M21 3v5h-5" />
  </svg>
);

export const ChatIcon = (props) => (
  <svg {...base} {...props}>
    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
  </svg>
);

export const LogoMark = (props) => (
  <svg viewBox="0 0 64 64" width="32" height="32" aria-hidden="true" focusable="false" {...props}>
    <circle cx="32" cy="32" r="30" fill="#c2410c" />
    <rect x="26" y="14" width="12" height="24" rx="6" fill="#fff" />
    <path
      d="M20 32a12 12 0 0 0 24 0"
      fill="none"
      stroke="#fff"
      strokeWidth="4"
      strokeLinecap="round"
    />
    <path d="M32 44v6" stroke="#fff" strokeWidth="4" strokeLinecap="round" />
  </svg>
);
