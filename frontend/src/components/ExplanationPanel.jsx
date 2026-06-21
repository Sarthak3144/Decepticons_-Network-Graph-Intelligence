const PATTERN_LABELS = {
  fanout: "Fan-out",
  fanin: "Fan-in",
  convergence_chain: "Convergence chain",
  layering: "Layering",
  cycle: "Circular flow",
};

export default function ExplanationPanel({ explanation, loading }) {
  if (loading) {
    return (
      <div className="panel">
        <span className="mono dim">loading…</span>
      </div>
    );
  }

  if (!explanation) {
    return (
      <div className="panel panel--empty">
        <p className="mono dim">No account selected.</p>
        <p className="dim small">Search an account ID above to see its structural risk profile.</p>
      </div>
    );
  }

  if (!explanation.found) {
    return (
      <div className="panel panel--empty">
        <p className="mono">account {explanation.account_id}</p>
        <p className="dim small">{explanation.message}</p>
        <span className="badge badge--clear mono">no patterns triggered</span>
      </div>
    );
  }

  return (
    <div className="panel">
      <div className="panel__header">
        <span className="mono panel__acct">acct {explanation.account_id}</span>
        <span className="panel__rank mono dim">rank #{explanation.rank}</span>
      </div>

      <div className="score-row">
        <div className="score-circle mono" style={{ "--score": explanation.risk_score }}>
          {explanation.risk_score}
        </div>
        <div className="score-meta">
          <div className="tags">
            {explanation.patterns_triggered.map((p) => (
              <span key={p} className="tag mono">{PATTERN_LABELS[p] || p}</span>
            ))}
          </div>
          <div className="flags mono dim">
            {explanation.pep_flag && <span className="flag flag--warn">PEP</span>}
            {explanation.sanctions_hit && <span className="flag flag--alert">SANCTIONS</span>}
            <span className="flag">{explanation.risk_grade}</span>
          </div>
        </div>
      </div>

      <div className="explanation-text">
        {explanation.explanation.split(" | ").map((line, i) => (
          <p key={i} className="explanation-line">
            <span className="mono dim">{String(i + 1).padStart(2, "0")}</span> {line}
          </p>
        ))}
      </div>
    </div>
  );
}