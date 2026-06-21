import { useEffect, useState } from "react";
import { api } from "./api/client";
import GraphCanvas from "./components/GraphCanvas";
import SearchBar from "./components/SearchBar";
import ExplanationPanel from "./components/ExplanationPanel";
import RankedTable from "./components/RankedTable";
import PatternTabs from "./components/PatternTabs";

export default function App() {
  const [summary, setSummary] = useState(null);
  const [accountId, setAccountId] = useState(null);
  const [subgraph, setSubgraph] = useState(null);
  const [explanation, setExplanation] = useState(null);
  const [graphLoading, setGraphLoading] = useState(false);
  const [explLoading, setExplLoading] = useState(false);
  const [ranked, setRanked] = useState([]);

  useEffect(() => {
    api.graphSummary().then(setSummary).catch(() => {});
    api.rankedAccounts(50, 0).then((r) => setRanked(r.results)).catch(() => {});
  }, []);

  function handleSearch(id) {
    const numId = Number(id);
    setAccountId(numId);
    setGraphLoading(true);
    setExplLoading(true);

    api.subgraph(numId, 1)
      .then(setSubgraph)
      .catch(() => setSubgraph(null))
      .finally(() => setGraphLoading(false));

    api.explanation(numId)
      .then(setExplanation)
      .catch(() => setExplanation(null))
      .finally(() => setExplLoading(false));
  }

  return (
    <div className="app">
      <header className="app-header">
        <div>
          <h1 className="mono">NETWORK INTELLIGENCE</h1>
          <p className="dim small">Track 3 — structural laundering pattern detection</p>
        </div>
        {summary && (
          <div className="header-stats mono small dim">
            <span>{summary.num_nodes.toLocaleString()} accounts</span>
            <span>{summary.num_edges.toLocaleString()} edges</span>
          </div>
        )}
      </header>

      <div className="hero-row">
        <div className="hero-main">
          <SearchBar onSearch={handleSearch} defaultValue={accountId || ""} />
          <GraphCanvas subgraph={subgraph} centerAccount={accountId} loading={graphLoading} />
        </div>
        <div className="hero-side">
          <ExplanationPanel explanation={explanation} loading={explLoading} />
        </div>
      </div>

      <div className="lower-row">
        <div className="lower-main">
          <h2 className="mono section-title">ranked accounts</h2>
          <RankedTable accounts={ranked} onSelect={(id) => handleSearch(id)} selectedId={accountId} />
        </div>
        <div className="lower-side">
          <h2 className="mono section-title">pattern deep-dive</h2>
          <PatternTabs onSelectAccount={(id) => handleSearch(id)} />
        </div>
      </div>
    </div>
  );
}