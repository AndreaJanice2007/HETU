import { FeatureIcon, OrbitingChips } from "./PatientLoginHero";

const FEATURES = [
  {
    name: "records",
    title: "Complete Patient View",
    copy: "Access history, reports and prescriptions",
  },
  {
    name: "care",
    title: "Collaborative Care",
    copy: "Work with your care team seamlessly",
  },
  {
    name: "chart",
    title: "Better Outcomes",
    copy: "Data-driven insights for proactive care",
  },
];

export function DoctorLoginFigure() {
  return (
    <div className="relative mx-auto hidden h-[min(42vh,19rem)] w-full max-w-[15rem] lg:block">
      <div className="absolute left-1/2 top-8 h-40 w-40 -translate-x-1/2 rounded-full bg-white/55 ring-1 ring-mint/20" />
      <img
        src="/login-doctor.png?v=5"
        alt=""
        className="relative z-[1] mx-auto h-full w-auto object-contain"
      />
      <OrbitingChips icons={["records", "heart", "care", "chart"]} />
    </div>
  );
}

export default function DoctorLoginHero() {
  return (
    <div className="relative w-full max-w-xl text-left">
      <h1 className="text-[2rem] font-bold leading-[1.08] tracking-tight text-charcoal sm:text-4xl">
        Empower
        <br />
        <span className="text-mint">Better Care</span>
        <br />
        Every Day
      </h1>
      <p className="mt-3 max-w-lg text-sm leading-relaxed text-charcoal/55">
        Access patient records, log diagnoses, collaborate with care teams, and make more informed decisions.
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
        className="mt-5 text-[15px] italic leading-tight text-mint"
        style={{ fontFamily: '"Instrument Serif", Georgia, serif' }}
      >
        A Healthier Tomorrow, Together.
      </p>
    </div>
  );
}
