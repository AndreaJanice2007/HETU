import { useLocation } from "react-router-dom";

export default function PageFrame() {
  const pathname = useLocation().pathname;
  const standalone = pathname.startsWith("/guest-judge") || pathname.startsWith("/doctor/signup");
  if (standalone) return null;
  const hideCaptions = pathname === "/";

  return (
    <div className="pointer-events-none fixed inset-0 z-0 overflow-hidden" aria-hidden>
      <div className="absolute inset-0 bg-[#e7faf4]" />

      <svg className="absolute inset-0 h-full w-full" preserveAspectRatio="none" viewBox="0 0 1600 900">
        <path
          d="M0 210 C240 40 460 250 780 130 C1080 20 1280 190 1600 80 L1600 900 L0 900 Z"
          fill="rgba(2,195,154,0.22)"
        />
        <path
          d="M0 320 C300 140 540 340 900 230 C1180 150 1380 280 1600 180 L1600 900 L0 900 Z"
          fill="rgba(2,195,154,0.16)"
        />
        <path
          d="M318 28 H1248 L1528 28 C1558 28 1572 48 1572 78 V822 C1572 858 1540 874 1504 874 H96 C58 874 28 854 28 816 V118 L28 72 L96 28 H318"
          fill="none"
          stroke="#02c39a"
          strokeWidth="3.2"
          vectorEffect="non-scaling-stroke"
          strokeLinejoin="round"
        />
        <path
          d="M1248 28 L1298 78 H1528"
          fill="none"
          stroke="#02c39a"
          strokeWidth="3.2"
          vectorEffect="non-scaling-stroke"
        />
      </svg>

      {hideCaptions ? null : (
        <div className="absolute right-10 top-6 hidden items-center gap-3 text-[10px] font-semibold uppercase tracking-[0.2em] text-charcoal/55 sm:flex">
          <span>People</span>
          <span className="text-mint">|</span>
          <span>Context</span>
          <span className="text-mint">|</span>
          <span>Better care</span>
          <span className="h-px w-8 bg-mint" />
          <span className="h-2 w-2 rounded-full bg-mint" />
        </div>
      )}

      <svg
        className="absolute right-6 top-[38%] hidden h-52 w-28 text-mint sm:block"
        viewBox="0 0 80 160"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.6"
      >
        <path d="M40 8 L66 23 V53 L40 68 L14 53 V23 Z" />
        <path d="M28 36 H52 M40 28 V44" />
        <path d="M40 58 L66 73 V103 L40 118 L14 103 V73 Z" />
        <rect x="32" y="82" width="16" height="18" rx="1.5" />
        <path d="M40 108 L32 116 H48 Z" />
        <path d="M40 108 L66 123 V153 L40 168 L14 153 V123 Z" opacity="0.85" />
        <path d="M40 138 L50 146 L40 154 L30 146 Z" />
      </svg>

      {hideCaptions ? null : (
        <>
          <div className="absolute bottom-6 left-10 hidden text-[10px] font-semibold uppercase tracking-[0.22em] text-charcoal/50 sm:block">
            Understand <span className="mx-2 text-mint">|</span> Connect{" "}
            <span className="mx-2 text-mint">|</span> Heal
          </div>
          <div className="absolute bottom-6 right-10 hidden items-center gap-3 text-[10px] font-semibold uppercase tracking-[0.18em] text-charcoal/50 sm:flex">
            <span className="h-px w-10 bg-mint" />
            A more complete patient story
          </div>
        </>
      )}
    </div>
  );
}
