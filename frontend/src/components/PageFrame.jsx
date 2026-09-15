export default function PageFrame() {
  return (
    <div className="pointer-events-none fixed inset-3 z-40 sm:inset-4" aria-hidden>
      <svg className="absolute inset-0 h-full w-full" preserveAspectRatio="none" viewBox="0 0 1600 900">
        <path
          d="M318 36 H1268 L1544 36 C1572 36 1578 58 1578 82 V818 C1578 852 1548 868 1514 868 H86 C52 868 22 848 22 814 V128 L22 78 L86 36 H318"
          fill="none"
          stroke="#02c39a"
          strokeWidth="2.4"
          vectorEffect="non-scaling-stroke"
          strokeLinejoin="round"
        />
        <path
          d="M1268 36 L1310 78 H1544"
          fill="none"
          stroke="#02c39a"
          strokeWidth="2.4"
          vectorEffect="non-scaling-stroke"
          opacity="0.55"
        />
      </svg>

      <svg className="absolute inset-x-8 bottom-6 h-40 w-auto max-w-none sm:inset-x-12" viewBox="0 0 1600 220" preserveAspectRatio="none">
        <path
          d="M0 180 C220 40 420 210 720 120 C980 40 1180 160 1600 70 L1600 220 L0 220 Z"
          fill="rgba(2,195,154,0.14)"
        />
        <path
          d="M0 200 C280 90 520 200 860 150 C1140 100 1340 170 1600 110 L1600 220 L0 220 Z"
          fill="rgba(2,195,154,0.1)"
        />
      </svg>

      <svg
        className="absolute right-5 top-[58%] hidden h-36 w-24 opacity-35 sm:block"
        viewBox="0 0 80 140"
        fill="none"
        stroke="#02c39a"
        strokeWidth="1.2"
      >
        <path d="M40 8 L62 21 V47 L40 60 L18 47 V21 Z" />
        <path d="M40 52 L62 65 V91 L40 104 L18 91 V65 Z" />
        <path d="M40 78 L62 91 V117 L40 130 L18 117 V91 Z" />
        <path d="M28 78 H52 M40 72 V84" opacity="0.8" />
        <rect x="34" y="100" width="12" height="14" rx="1.5" />
        <path d="M40 118 L34 124 H46 Z" />
      </svg>

      <img
        src="/hetu-icon.png?v=3"
        alt=""
        className="absolute bottom-20 left-6 w-36 opacity-[0.05] sm:left-8 sm:w-48"
      />
    </div>
  );
}
