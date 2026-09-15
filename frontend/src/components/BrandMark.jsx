const letters = ["E", "T", "U"];

export default function BrandMark({ size = "md", className = "" }) {
  const large = size === "lg";
  const stroke = large ? "3px #111111" : "1.6px #111111";

  return (
    <span
      className={`inline-flex items-end ${large ? "gap-[0.18em] text-7xl" : "gap-[0.18em] text-2xl"} ${className}`}
      aria-label="Hetu"
    >
      <img
        src="/hetu-icon.png?v=3"
        alt=""
        className="h-[0.92em] w-auto shrink-0 object-contain"
      />
      {letters.map((letter) => (
        <span
          key={letter}
          className="font-semibold uppercase leading-none text-mint"
          style={{
            fontFamily: '"Orbitron", ui-sans-serif, system-ui, sans-serif',
            WebkitTextStroke: stroke,
            paintOrder: "stroke fill",
          }}
        >
          {letter}
        </span>
      ))}
    </span>
  );
}
