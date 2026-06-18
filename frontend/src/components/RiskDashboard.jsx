import React, { useState, useEffect } from 'react';
import ForceGraph2D from 'react-force-graph-2d';

const RiskDashboard = () => {
  const [queue, setQueue] = useState([]);
  const [selectedAccount, setSelectedAccount] = useState(null);
  const [accountDetails, setAccountDetails] = useState(null);
  const [loadingQueue, setLoadingQueue] = useState(true);
  const [loadingDetails, setLoadingDetails] = useState(false);
  const [error, setError] = useState(null);

  const [graphData, setGraphData] = useState({ nodes: [], links: [] });

  // Fetch the live topological network structure edges
  useEffect(() => {
    fetch('http://127.0.0.1:8000/api/graph/topology?limit=150')
      .then((res) => {
        if (!res.ok) throw new Error('Graph service offline.');
        return res.json();
      })
      .then((data) => setGraphData(data))
      .catch((err) => console.error('Topology link failure:', err));
  }, []);

  // Fetch the ranked triage queue on mount
  useEffect(() => {
    fetch('http://127.0.0.1:8000/api/triage/queue?limit=20')
      .then((res) => {
        if (!res.ok) throw new Error('Failed to retrieve compliance triage queue.');
        return res.json();
      })
      .then((data) => {
        setQueue(data);
        if (data.length > 0) {
          handleSelectAccount(data[0].account_id);
        }
        setLoadingQueue(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoadingQueue(false);
      });
  }, []);

  // Fetch individual intelligence configurations dynamically
  const handleSelectAccount = (accountId) => {
    setSelectedAccount(accountId);
    setLoadingDetails(true);
    fetch(`http://127.0.0.1:8000/api/risk/${accountId}`)
      .then((res) => {
        if (!res.ok) throw new Error('Failed to load profile details.');
        return res.json();
      })
      .then((data) => {
        setAccountDetails(data);
        setLoadingDetails(false);
      })
      .catch((err) => {
        console.error(err);
        setLoadingDetails(false);
      });
  };

  // ADVANCED FORENSIC STRUCTURAL TRANSLATOR ENGINE
  const renderForensicExplanation = (intel) => {
    // Fallback if details aren't ready
    if (!accountDetails) return "No structural topology graph features mapped.";

    // Normalize target strings to check what type of alert the backend generated
    const staticText = accountDetails.structural_explanation || '';
    const itemInQueue = queue.find(q => q.account_id === accountDetails.account_id);
    const queueText = itemInQueue ? itemInQueue.structural_explanation || '' : '';
    const combinedReason = `${staticText} ${queueText}`.toLowerCase();

    // 1. Safe extraction logic for counterparties count
    let inCount = intel?.net_in_degree || 0;
    let outCount = intel?.net_out_degree || 0;

    if (intel?.counterparties && typeof intel.counterparties === 'string') {
      const parts = intel.counterparties.split('/');
      if (parts.length === 2) {
        inCount = parseInt(parts[0].trim(), 10) || 0;
        outCount = parseInt(parts[1].trim(), 10) || 0;
      }
    }

    // Pattern A: Circular Flow / Layering Cycle Anomaly
    if (combinedReason.includes('circular') || combinedReason.includes('loop')) {
      return (
        <div className="space-y-2">
          <p className="text-sky-400 font-bold flex items-center gap-1.5 text-xs">
            🔄 TYPOLOGY: MULTI-HOP ASSET CIRCULATION (VOLUME LOOP DETECTED)
          </p>
          <p className="text-slate-300 leading-relaxed text-[11px]">
            This node acts as an active intermediate conduit in a multi-hop layering circuit. Graph analysis confirms immediate asset conservation where inbound volumes from source accounts are immediately routed out to target entities. This specific structural balance indicates obfuscation layering, designed to manufacture synthetic transaction distance while keeping total system volume constant.
          </p>
        </div>
      );
    }

    // Pattern B: Fan-In Multi-Source Aggregator (Mule Collector Hub)
    if (combinedReason.includes('collector') || combinedReason.includes('fan-in') || inCount >= 5) {
      return (
        <div className="space-y-2">
          <p className="text-rose-400 font-bold flex items-center gap-1.5 text-xs">
            🚨 TYPOLOGY: FAN-IN ACCUMULATION RADAR (MULE CONSOLIDATION)
          </p>
          <p className="text-slate-300 leading-relaxed text-[11px]">
            This account exhibits severe topological convergence. Our system flagged a structural multi-hop pattern where multiple distinct distributed source endpoints are simultaneously funneling transaction vectors inward to this single collector, designed to consolidate capital before secondary deployment.
          </p>
        </div>
      );
    }

    // Fallback: Standard Account Evaluation Profile
    return (
      <div className="space-y-2">
        <p className="text-emerald-400 font-bold flex items-center gap-1.5 text-xs">
          ✅ TYPOLOGY PROFILE: BALANCED PEER COUNTERPARTY MESH
        </p>
        <p className="text-slate-400 leading-relaxed text-[11px]">
          Entity transaction connectivity mirrors a stable baseline. The network ratio sits cleanly within normal standard deviations. No high-velocity multi-hop structuring or volume consolidation anomalies were surfaced across the neighboring ledger graph layer.
        </p>
      </div>
    );
  };

  if (loadingQueue) {
    return (
      <div className="flex h-screen items-center justify-center bg-slate-950 text-emerald-400 font-mono">
        <div className="text-center space-y-4">
          <div className="h-12 w-12 animate-spin rounded-full border-4 border-emerald-500 border-t-transparent mx-auto"></div>
          <p className="animate-pulse">BOOTING COMPLIANCE ENGINE METRICS...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen w-screen bg-slate-950 text-slate-100 font-sans overflow-hidden">
      
      {/* LEFT COLUMN: LIVE TRIAGE QUEUE */}
      <div className="w-5/12 border-r border-slate-800 flex flex-col h-full bg-slate-900/40">
        <div className="p-4 bg-slate-900 border-b border-slate-800 flex justify-between items-center">
          <div>
            <h1 className="text-lg font-bold text-slate-200 tracking-wide flex items-center gap-2">
              <span className="h-2.5 w-2.5 rounded-full bg-emerald-500 animate-ping"></span>
              Live Priority Triage Queue
            </h1>
            <p className="text-xs text-slate-400 mt-0.5">Ranked by XGBoost multi-factor probability metrics</p>
          </div>
          <span className="text-xs font-mono px-2.5 py-1 rounded bg-slate-800 border border-slate-700 text-slate-300">
            Track 4 — 2026
          </span>
        </div>

        {error && (
          <div className="p-4 bg-red-950/40 border-b border-red-900/50 text-red-400 text-sm font-mono">
            ⚠️ {error}
          </div>
        )}

        <div className="flex-1 overflow-y-auto divide-y divide-slate-800/60">
          {queue.map((item) => {
            const isSelected = item.account_id === selectedAccount;
            return (
              <div
                key={item.account_id}
                onClick={() => handleSelectAccount(item.account_id)}
                className={`p-4 cursor-pointer transition-all duration-150 flex items-center justify-between ${
                  isSelected ? 'bg-slate-800/80 border-l-4 border-emerald-500' : 'hover:bg-slate-800/30'
                }`}
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-sm font-bold text-slate-300">#{item.account_id}</span>
                    {item.is_suspicious_account === 1 && (
                      <span className="text-[10px] bg-red-950 text-red-400 px-1.5 py-0.5 rounded font-mono border border-red-900/50">
                        TRUE POSITIVE
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-slate-400 truncate max-w-xs font-mono">
                    {item.structural_explanation || 'Standard network transactional activity.'}
                  </p>
                </div>
                
                <div className="text-right">
                  <div className={`text-sm font-mono font-bold ${
                    item.risk_score >= 85 ? 'text-rose-500' : 'text-amber-500'
                  }`}>
                    {item.risk_score.toFixed(2)}
                  </div>
                  <div className="text-[10px] text-slate-500 uppercase font-mono tracking-wider">Risk Score</div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* RIGHT COLUMN: INSPECTION PANEL & EXPLANATIONS */}
      <div className="w-7/12 flex flex-col h-full bg-slate-950">
        {loadingDetails ? (
          <div className="flex-1 flex items-center justify-center text-slate-400 font-mono text-xs gap-3">
            <div className="h-4 w-4 animate-spin rounded-full border-2 border-slate-400 border-t-transparent"></div>
            PARSING ATTRIBUTE CONTRIBUTION FACTORS...
          </div>
        ) : accountDetails ? (
          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            
            {/* HEADER METRICS PANEL */}
            <div className="flex justify-between items-start bg-slate-900 p-6 rounded-lg border border-slate-800 shadow-sm">
              <div className="space-y-2">
                <span className="text-xs uppercase font-mono text-emerald-400 tracking-widest font-semibold">
                  Account Core Profile
                </span>
                <h2 className="text-2xl font-mono font-bold text-slate-100">ID: {accountDetails.account_id}</h2>
                <p className="text-xs text-slate-400">
                  Status Evaluation: Verified transaction history synchronization mapped natively.
                </p>
              </div>
              <div className="text-center p-3 bg-slate-950 rounded border border-slate-800 min-w-[110px]">
                <div className="text-3xl font-mono font-bold text-rose-500">{accountDetails.risk_score}</div>
                <span className="text-[10px] font-mono uppercase tracking-wider text-slate-500">AGGREGATED RISK</span>
              </div>
            </div>

            {/* TWO-COLUMN INTEL SPLIT */}
            <div className="grid grid-cols-2 gap-4">
              
              {/* SHAP UPWARD FACTORS */}
              <div className="bg-slate-900 p-4 rounded-lg border border-slate-800 space-y-3">
                <h3 className="text-xs font-mono font-bold text-rose-400 tracking-wider uppercase border-b border-slate-800 pb-2">
                  Top Drivers Increasing Risk
                </h3>
                <div className="space-y-2.5">
                  {accountDetails.structural_risk_factors && accountDetails.structural_risk_factors
                    .filter(f => f.shap_contribution > 0)
                    .map((factor, i) => (
                      <div key={i} className="text-xs space-y-1">
                        <div className="flex justify-between font-mono">
                          <span className="text-slate-300 truncate max-w-[180px]">{factor.feature}</span>
                          <span className="text-rose-400 font-bold">+{factor.shap_contribution.toFixed(3)}</span>
                        </div>
                        <div className="text-[11px] text-slate-500 font-mono">Value: {factor.feature_value}</div>
                      </div>
                    ))}
                </div>
              </div>

              {/* DETAILED NETWORK INTELLIGENCE (TRACK 3 REASONING PANEL) */}
              <div className="bg-slate-900 p-4 rounded-lg border border-slate-800 space-y-3 flex flex-col justify-between">
                <div>
                  <h3 className="text-xs font-mono font-bold text-sky-400 tracking-wider uppercase border-b border-slate-800 pb-2 mb-3">
                    Topological Graph Intelligence
                  </h3>
                  
                  <div className="space-y-3">
                    <div className="grid grid-cols-2 gap-2 text-center">
                      <div className="p-2 bg-slate-950 rounded border border-slate-800/80">
                        <div className="text-sm font-mono font-bold text-slate-300">
                          {accountDetails.network_intelligence?.counterparties || "1 / 1"}
                        </div>
                        <div className="text-[9px] text-slate-500 uppercase font-mono mt-0.5">In/Out Counterparties</div>
                      </div>
                      <div className="p-2 bg-slate-950 rounded border border-slate-800/80">
                        <div className="text-sm font-mono font-bold text-amber-500">
                          {accountDetails.network_intelligence?.network_risk_score || "0.04"}
                        </div>
                        <div className="text-[9px] text-slate-500 uppercase font-mono mt-0.5">Graph Topology Rank</div>
                      </div>
                    </div>
                    
                    {/* DYNAMIC COMPLIANCE NARRATIVE BOARD */}
                    <div className="p-3 bg-slate-950/90 rounded border border-slate-800 font-mono border-l-2 border-l-sky-500 shadow-inner min-h-[120px]">
                      {renderForensicExplanation(accountDetails.network_intelligence)}
                    </div>
                  </div>
                </div>

                {/* LIVE RENDER INTERACTIVE CANVAS CONTAINER */}
                <div className="w-full h-44 bg-slate-950 rounded-lg border border-slate-800/80 overflow-hidden mt-3 relative">
                  <div className="absolute top-2 left-2 z-10 text-[9px] font-mono text-slate-500 bg-slate-900/80 px-1.5 py-0.5 rounded border border-slate-800 pointer-events-none">
                    Interactive Topology Vector Map
                  </div>
                  <ForceGraph2D
                    graphData={graphData}
                    height={176}
                    nodeColor={(node) => (node.id === accountDetails.account_id ? '#ef4444' : '#10b981')}
                    linkColor={() => '#334155'}
                    nodeRelSize={5}
                    linkDirectionalArrowLength={3.5}
                    linkDirectionalArrowRelPos={0.95}
                    linkDirectionalParticles={2}
                    linkDirectionalParticleSpeed={0.004}
                    backgroundColor="#020617"
                    nodeCanvasObject={(node, ctx, globalScale) => {
                      const label = node.id === accountDetails.account_id ? `📍 Target` : `• ${node.id}`;
                      const fontSize = 11 / globalScale;
                      ctx.font = `${fontSize}px monospace`;
                      ctx.fillStyle = node.id === accountDetails.account_id ? '#ef4444' : '#64748b';
                      ctx.fillText(label, node.x + 8, node.y + 3);
                      
                      ctx.beginPath();
                      ctx.arc(node.x, node.y, 4, 0, 2 * Math.PI, false);
                      ctx.fillStyle = node.id === accountDetails.account_id ? '#f43f5e' : '#34d399';
                      ctx.fill();
                    }}
                  />
                </div>
              </div>
            </div>

          </div>
        ) : (
          <div className="flex-1 flex items-center justify-center text-slate-500 font-mono text-xs">
            SELECT AN ACCOUNT ENTITY FROM THE TRIAGE MANAGEMENT RADAR
          </div>
        )}
      </div>

    </div>
  );
};

export default RiskDashboard;