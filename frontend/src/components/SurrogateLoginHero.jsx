import { FeatureIcon, OrbitingChips } from "./PatientLoginHero";

const FEATURES = [
  {
    name: "records",
    title: "Stay Informed",
    copy: "View your loved one’s health records",
  },
  {
    name: "care",
    title: "Support Their Care",
    copy: "Coordinate with the care team",
  },
  {
    name: "insights",
    title: "Make Confident Decisions",
    copy: "Get clearer insights, together",
  },
];

export function SurrogateLoginFigure() {
  return (
    <div className="relative mx-auto hidden h-[min(42vh,19rem)] w-full max-w-[16rem] lg:block">
      <div className="absolute left-1/2 top-8 h-40 w-40 -translate-x-1/2 rounded-full bg-white/55 ring-1 ring-mint/20" />
      <img
        src="/login-surrogate.png?v=5"
        alt=""
        className="relative z-[1] mx-auto h-full w-auto object-contain"
      />
      <OrbitingChips icons={["records", "heart", "care", "chart"]} />
    </div>
  );
}

export default function SurrogateLoginHero() {
  return (
    <div className="relative w-full max-w-xl text-left">
      <h1 className="text-[2rem] font-bold leading-[1.08] tracking-tight text-charcoal sm:text-4xl">
        Care
        <br />
        <span className="text-mint">Together,</span>
        <br />
        With Confidence
      </h1>
      <p className="mt-3 max-w-lg text-sm leading-relaxed text-charcoal/55">
        Support your loved one’s health journey by accessing their records, insights, and care updates — all in one place.
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
      <p
        className="mt-5 text-[15px] italic leading-tight text-charcoal/80"
        style={{ fontFamily: '"Instrument Serif", Georgia, serif' }}
      >
        A Healthier Tomorrow, Together.
      </p>
    </div>
  );
}
