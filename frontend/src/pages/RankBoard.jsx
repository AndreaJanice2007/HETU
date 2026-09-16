import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import BrandMark from "../components/BrandMark";

export default function RankBoard() {
  const [rows, setRows] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .doctorRank()
      .then(setRows)
      .catch((err) => setError(err.message));
  }, []);

  return (
    <div className="relative z-10 mx-auto min-h-screen max-w-4xl px-8 pb-24 pt-16 text-charcoal sm:px-12">
      <div className="mb-8 flex flex-wrap items-center justify-between gap-4">
        <BrandMark size="md" />
        <Link to="/" className="text-sm font-medium text-mint">
          Back
        </Link>
      </div>
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-mint">Live board</p>
      <h1 className="mt-2 text-3xl font-semibold">Best doctor rank</h1>
      <p className="mt-2 max-w-2xl text-sm text-charcoal/55">
        Rank is based on credibility. A senior doctor moves up when they record a sound coordinated treatment after a two-doctor conversation. Hetu does not diagnose.
      </p>
      {error ? <p className="mt-4 text-sm text-severity-high">{error}</p> : null}
      <div className="mt-8 overflow-hidden rounded-2xl bg-white shadow-[0_12px_32px_rgba(43,45,47,0.08)] ring-1 ring-charcoal/8">
        {rows.length === 0 ? (
          <p className="px-5 py-8 text-sm text-charcoal/50">No doctors yet. Create doctor accounts to start the board.</p>
        ) : (
          rows.map((row) => (
            <article key={row.id} className="flex flex-wrap items-center gap-4 border-b border-charcoal/8 px-5 py-4 last:border-0">
              <span className="grid h-10 w-10 place-items-center rounded-full bg-mint/15 text-sm font-semibold text-mint">
                {row.rank}
              </span>
              <div className="min-w-[12rem] flex-1">
                <p className="font-semibold">{row.name}</p>
                <p className="text-sm text-charcoal/50">
                  {row.specialty} · {row.hospital}
                </p>
              </div>
              <div className="text-right text-sm">
                <p className="font-medium">{Number(row.credibility_score || 0).toFixed(2)}</p>
                <p className="text-xs text-charcoal/45">
                  {row.resolved_cases_count || 0} reviews · {row.years_experience || 0} yrs
                </p>
              </div>
            </article>
          ))
        )}
      </div>
    </div>
  );
}
