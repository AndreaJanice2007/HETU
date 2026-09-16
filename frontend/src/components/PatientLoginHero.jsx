export function FeatureIcon({ name }) {
  const common = {
    width: 22,
    height: 22,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.8,
    strokeLinecap: "round",
    strokeLinejoin: "round",
    "aria-hidden": true,
  };
  if (name === "records") {
    return (
      <svg {...common}>
        <rect x="6" y="3.5" width="12" height="17" rx="2" />
        <path d="M9 8h6M9 12h6M9 16h4" />
      </svg>
    );
  }
  if (name === "care") {
    return (
      <svg {...common}>
        <circle cx="9" cy="8" r="2.4" />
        <circle cx="16" cy="8.5" r="2" />
        <path d="M4.5 18.5c.6-2.8 2.4-4.4 4.5-4.4 1.3 0 2.4.6 3.2 1.5" />
        <path d="M13 18.2c.5-2 1.9-3.2 3.4-3.2 1.8 0 3.3 1.2 3.8 3.2" />
      </svg>
    );
  }
  if (name === "insights") {
    return (
      <svg {...common}>
        <path d="M12 19s-6.2-3.8-6.2-8A3.4 3.4 0 0 1 12 8.2 3.4 3.4 0 0 1 18.2 10c0 4.2-6.2 8-6.2 8z" />
        <path d="M8 12h1.6l1.1-1.8 1.5 3.4 1.1-1.8H15" />
      </svg>
    );
  }
  if (name === "heart") {
    return (
      <svg {...common}>
        <path d="M12 18s-6.2-3.8-6.2-8A3.4 3.4 0 0 1 12 8.2 3.4 3.4 0 0 1 18.2 10c0 4.2-6.2 8-6.2 8z" />
        <path d="M4.5 12h2.2l1.4-2.2 1.8 4.2 1.4-2.4H12" />
      </svg>
    );
  }
  if (name === "share") {
    return (
      <svg {...common}>
        <circle cx="6.5" cy="12" r="2.1" />
        <circle cx="17" cy="7" r="2.1" />
        <circle cx="17" cy="17" r="2.1" />
        <path d="M8.4 11.2 14.9 8.2M8.4 12.8 14.9 15.8" />
      </svg>
    );
  }
  if (name === "chart") {
    return (
      <svg {...common}>
        <path d="M6 18V10M11 18V7M16 18v-5M20 18H4" />
      </svg>
    );
  }
  return (
    <svg {...common}>
      <path d="M6 18V10M11 18V7M16 18v-5M20 18H4" />
    </svg>
  );
}

const FEATURES = [
  {
    name: "records",
    title: "Your Health Records",
    copy: "See notes, prescriptions and history",
  },
  {
    name: "care",
    title: "Connected Care",
    copy: "Stay in sync with your care team",
  },
  {
    name: "insights",
    title: "Smarter Insights",
    copy: "Understand your health, make better decisions",
  },
];

export function OrbitingChips({ icons }) {
  return (
    <div className="login-orbit" aria-hidden>
      {icons.map((name, index) => (
        <span key={name} className="login-orbit-item" style={{ "--i": index }}>
          <span className="login-orbit-chip">
            <FeatureIcon name={name} />
          </span>
        </span>
      ))}
    </div>
  );
}

export function PatientLoginFigure() {
  return (
    <div className="relative mx-auto hidden h-[min(42vh,19rem)] w-full max-w-[15rem] lg:block">
      <div className="absolute left-1/2 top-8 h-40 w-40 -translate-x-1/2 rounded-full bg-white/55 ring-1 ring-mint/20" />
      <img
        src="/login-patient.png?v=4"
        alt=""
        className="relative z-[1] mx-auto h-full w-auto object-contain"
      />
      <OrbitingChips icons={["records", "heart", "share", "chart"]} />
      <p
        className="absolute bottom-1 left-0 max-w-[9rem] text-sm italic leading-tight text-charcoal/70"
        style={{ fontFamily: '"Instrument Serif", Georgia, serif' }}
      >
        A Healthier Tomorrow, Together.
      </p>
    </div>
  );
}

export default function PatientLoginHero() {
  return (
    <div className="relative w-full max-w-xl text-left">
      <h1 className="text-[2rem] font-bold leading-[1.08] tracking-tight text-charcoal sm:text-4xl">
        Your <span className="text-mint">Health Journey,</span>
        <br />
        All in One Place
      </h1>
      <p className="mt-3 max-w-lg text-sm leading-relaxed text-charcoal/55">
        Access your records, get insights, communicate with your care team, and take control of your health.
      </p>
      <ul className="mt-6 grid gap-3">
        {FEATURES.map((item) => (
          <li key={item.name} className="flex items-start gap-3">
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-mint/12 text-mint">
              <FeatureIcon name={item.name} />
            </span>
            <span>
              <span className="block text-sm font-semibold text-charcoal">{item.title}</span>
              <span className="mt-0.5 block text-sm leading-snug text-charcoal/50">{item.copy}</span>
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
