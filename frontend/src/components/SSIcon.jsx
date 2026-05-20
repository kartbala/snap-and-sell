export default function SSIcon({ name, size = 16, stroke = 2 }) {
  const props = {
    width: size,
    height: size,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: stroke,
    strokeLinecap: "round",
    strokeLinejoin: "round",
  };
  switch (name) {
    case "pin":
      return (
        <svg {...props}>
          <path d="M12 21s-7-6.5-7-12a7 7 0 0114 0c0 5.5-7 12-7 12z" />
          <circle cx="12" cy="9" r="2.5" />
        </svg>
      );
    case "sms":
      return (
        <svg {...props}>
          <path d="M21 12a8 8 0 01-11.5 7.2L4 21l1.8-5.4A8 8 0 1121 12z" />
        </svg>
      );
    case "check":
      return (
        <svg {...props}>
          <path d="M5 12.5l4.5 4.5L19 7" />
        </svg>
      );
    case "x":
      return (
        <svg {...props}>
          <path d="M6 6l12 12M18 6L6 18" />
        </svg>
      );
    case "review":
      return (
        <svg {...props}>
          <circle cx="12" cy="12" r="9" />
          <path d="M12 8v4M12 16h.01" />
        </svg>
      );
    case "meetup":
      return (
        <svg {...props}>
          <path d="M17 11a5 5 0 11-10 0 5 5 0 0110 0z" />
          <path d="M3 21a9 9 0 0118 0" />
        </svg>
      );
    case "home":
      return (
        <svg {...props}>
          <path d="M3 11l9-7 9 7v9a2 2 0 01-2 2h-4v-7H9v7H5a2 2 0 01-2-2v-9z" />
        </svg>
      );
    case "chev-l":
      return (
        <svg {...props}>
          <path d="M15 6l-6 6 6 6" />
        </svg>
      );
    default:
      return null;
  }
}
