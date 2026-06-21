import { useEffect, useState } from "react";
import { api } from "../api/client";

const TABS = [
  { key: "fanout", label: "Fan-out" },
  { key: "layering", label: "Layering" },
  { key: "cycles", label: "Cycles" },
];

export default function PatternTabs({ onSelectAccount }) {
  const [active, setActive] = useState("fanout");
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    setData([]); // clear stale data from previous tab immediately

    const fetcher =
      active === "fanout" ? api.fanout :
      active === "layering" ? api.layering :
      api.cycles;

    fetcher(15)
      .then(setData)
      .catch(() => setData([]))
      .finally(() => setLoading(false));
  }, [active]);

  return (
    <div className="pattern-tabs">
      <div className="tab-row">
        {TABS.map((t) => (
          <button
            key={t.key}
            className={`tab mono ${active === t.key ? "tab--active" : ""}`}
            onClick={() => setActive(t.key)}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="tab-body">
        {loading && <span className="mono dim">loading…</span>}

        {!loading && active === "fanout" &&
          data
            .filter((row) => row && typeof row.sender !== "undefined")
            .map((row, i) => (
              <div key={i} className="pattern-row" onClick={() => onSelectAccount(row.sender)}>
                <span className="mono">{row.sender}</span>
                <span className="dim small">→ {row.unique_receivers} accounts in 24h</span>
                <span className="mono small dim">NPR {Math.round(row.total_amount).toLocaleString()}</span>
              </div>
            ))}

        {!loading && active === "layering" &&
          data
            .filter((row) => row && Array.isArray(row.chain_accounts))
            .map((row, i) => (
              <div key={i} className="pattern-row" onClick={() => onSelectAccount(row.origin)}>
                <span className="mono">{row.chain_accounts.join(" → ")}</span>
                <span className="dim small">{row.hop_count} hops, {row.amount_retained_pct}% retained, {row.duration_hours}h</span>
              </div>
            ))}

        {!loading && active === "cycles" &&
          data
            .filter((row) => row && Array.isArray(row.cycle_accounts))
            .map((row, i) => (
              <div key={i} className="pattern-row" onClick={() => onSelectAccount(row.cycle_accounts[0])}>
                <span className="mono">{row.cycle_accounts.join(" → ")}</span>
                <span className="dim small">{row.amount_retained_pct}% retained, {row.duration_hours}h</span>
              </div>
            ))}

        {!loading && data.length === 0 && (
          <span className="mono dim small">No patterns found for this category.</span>
        )}
      </div>
    </div>
  );
}