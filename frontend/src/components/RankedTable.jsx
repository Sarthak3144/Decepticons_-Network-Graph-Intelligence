export default function RankedTable({ accounts, onSelect, selectedId }) {
  if (!accounts || !accounts.length) {
    return <p className="mono dim">No ranked accounts loaded.</p>;
  }

  return (
    <table className="ranked-table">
      <thead>
        <tr>
          <th className="mono">rank</th>
          <th className="mono">account</th>
          <th className="mono">score</th>
          <th className="mono">patterns</th>
          <th className="mono">grade</th>
        </tr>
      </thead>
      <tbody>
        {accounts.map((row) => (
          <tr
            key={row.account_id}
            className={row.account_id === selectedId ? "row--selected" : ""}
            onClick={() => onSelect(row.account_id)}
          >
            <td className="mono dim">{row.rank}</td>
            <td className="mono">{row.account_id}</td>
            <td className="mono score-cell">{row.risk_score}</td>
            <td className="mono small">{row.patterns_triggered}</td>
            <td className="mono small dim">{row.risk_grade}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}