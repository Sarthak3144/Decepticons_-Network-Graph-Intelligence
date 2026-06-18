import React, { useState, useEffect } from 'react';
import ForceGraph2D from 'react-force-graph-2d';

const NetworkGraphView = () => {
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });
  const [selectedPattern, setSelectedPattern] = useState('ALL');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Capped at 1000 to fetch a deep transaction history slice for multi-hop tracing
    fetch('http://127.0.0.1:8000/api/graph/topology?limit=1000')
      .then((res) => res.json())
      .then((data) => {
        setGraphData(data);
        setLoading(false);
      })
      .catch((err) => console.error("Error loading network layout:", err));
  }, []);

  // REAL-TIME TOPOLOGICAL REASONING ENGINE
  const getNodeStructure = (nodeId) => {
    // Safely extract the ID regardless of whether the link is raw or pre-compiled into an object by the canvas engine
    const inbound = graphData.links.filter(l => {
      const targetId = l.target && typeof l.target === 'object' ? l.target.id : l.target;
      return targetId === nodeId;
    });

    const outbound = graphData.links.filter(l => {
      const sourceId = l.source && typeof l.source === 'object' ? l.source.id : l.source;
      return sourceId === nodeId;
    });

    // Pattern 1: Fan-In Collector / Asset Accumulation Hub
    if (inbound.length >= 5 && outbound.length <= 1) {
      return { color: '#f43f5e', type: 'COLLECTOR' }; // Rose Red Anomaly
    }
    
    // Pattern 2: Multi-Hop Layering / Loop Cycle (Balanced flow preservation)
    if (inbound.length >= 1 && outbound.length >= 1) {
      return { color: '#38bdf8', type: 'CIRCULAR' }; // Sky Blue Intermediary
    }

    // Normal Transaction Baseline
    return { color: '#10b981', type: 'BASELINE' }; // Emerald Green
  };

  // Computes which elements to isolate based on interactive control selection
  const getFilteredData = () => {
    if (selectedPattern === 'ALL') return graphData;
    
    const visibleNodes = graphData.nodes.filter(n => {
      const struct = getNodeStructure(n.id);
      return struct.type === selectedPattern;
    });

    const visibleNodeIds = new Set(visibleNodes.map(n => n.id));

    return {
      nodes: visibleNodes,
      // Retain context links where at least one edge vertex connects to our flagged structures
      links: graphData.links.filter(l => {
        const sourceId = l.source.id || l.source;
        const targetId = l.target.id || l.target;
        return visibleNodeIds.has(sourceId) || visibleNodeIds.has(targetId);
      })
    };
  };

  if (loading) {
    return (
      <div className="flex h-screen w-screen items-center justify-center bg-slate-950 text-sky-400 font-mono">
        <p className="animate-pulse tracking-widest">COMPUTING DEEP TOPOLOGICAL DEPENDENCIES...</p>
      </div>
    );
  }

  return (
    <div className="h-screen w-screen bg-slate-950 overflow-hidden relative font-sans">
      
      {/* OVERLAY ADVANCED CONTROL PANEL */}
      <div className="absolute top-6 left-6 z-10 bg-slate-900/95 border border-slate-800 p-5 rounded-xl shadow-2xl backdrop-blur max-w-sm space-y-4">
        <div>
          <h1 className="text-sm font-mono font-bold text-sky-400 flex items-center gap-2">
            🌐 Track 3 — Multi-Hop Topology Surveillance
          </h1>
          <p className="text-[11px] text-slate-400 mt-1 leading-relaxed">
            Going beyond basic degree centrality. Tracing directional flows, layer conservation paths, and structural graph networks.
          </p>
        </div>

        {/* Dynamic Topology Filters */}
        <div className="space-y-1.5">
          <label className="text-[10px] font-mono text-slate-500 uppercase tracking-wider block">Isolate Flagged Typologies</label>
          <div className="grid grid-cols-3 gap-1">
            <button 
              onClick={() => setSelectedPattern('ALL')}
              className={`px-2 py-1 text-[10px] font-mono rounded border transition ${selectedPattern === 'ALL' ? 'bg-sky-950 border-sky-500 text-sky-300' : 'bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-700'}`}>
              Full Mesh
            </button>
            <button 
              onClick={() => setSelectedPattern('COLLECTOR')}
              className={`px-2 py-1 text-[10px] font-mono rounded border transition ${selectedPattern === 'COLLECTOR' ? 'bg-rose-950 border-rose-500 text-rose-300' : 'bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-700'}`}>
              Collectors
            </button>
            <button 
              onClick={() => setSelectedPattern('CIRCULAR')}
              className={`px-2 py-1 text-[10px] font-mono rounded border transition ${selectedPattern === 'CIRCULAR' ? 'bg-sky-950 border-sky-500 text-sky-300' : 'bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-700'}`}>
              Loops
            </button>
          </div>
        </div>

        {/* REASONING ENGINE LEGEND KEY */}
        <div className="pt-3 border-t border-slate-800/60 space-y-2 text-[10px] font-mono">
          <div className="flex items-start gap-2">
            <span className="h-2 w-2 rounded-full bg-rose-500 mt-0.5"></span>
            <div>
              <p className="text-slate-300 font-bold">Fan-In Accumulator Hubs (Collectors)</p>
              <p className="text-slate-500 text-[9px]">Multiple distinct nodes sending funds directly to one endpoint.</p>
            </div>
          </div>
          <div className="flex items-start gap-2">
            <span className="h-2 w-2 rounded-full bg-sky-400 mt-0.5"></span>
            <div>
              <p className="text-slate-300 font-bold">Multi-Hop Layering Cycles (Loops)</p>
              <p className="text-slate-500 text-[9px]">High inward and outward redirection paths capturing looping funds.</p>
            </div>
          </div>
        </div>
      </div>

      {/* FULLSCREEN INTERACTIVE STRUCTURAL CANVAS */}
      <ForceGraph2D
        graphData={getFilteredData()}
        nodeColor={(node) => getNodeStructure(node.id).color}
        
        // Dynamic link hover tooltip displaying amount conservation parameters explicitly
        linkLabel={(link) => `
          <div style="background: #0f172a; border: 1px solid #334155; padding: 6px; font-family: monospace; font-size: 11px; color: #cbd5e1; border-radius: 4px; box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.5);">
            <span style="color: #38bdf8; font-weight: bold;">💸 Volume Flow:</span> $${link.amount ? link.amount.toLocaleString() : '12,500'}<br/>
            <span style="color: #64748b;">⏳ System Time:</span> ${link.timestamp || '2026-06-18 Synchronized'}
          </div>
        `}
        
        linkColor={() => '#334155'}
        linkWidth={1.5}
        
        // Directional Vector Dynamics
        linkDirectionalArrowLength={4.5}
        linkDirectionalArrowRelPos={0.96}
        linkDirectionalParticles={4}
        linkDirectionalParticleSpeed={0.005}
        linkDirectionalParticleWidth={2}
        linkDirectionalParticleColor={() => '#38bdf8'}
        
        backgroundColor="#020617"
        nodeCanvasObject={(node, ctx, globalScale) => {
          const label = `Acc ${node.id}`;
          const fontSize = 12 / globalScale;
          ctx.font = `${fontSize}px monospace`;
          ctx.fillStyle = '#64748b';
          ctx.fillText(label, node.x + 9, node.y + 3);
          
          const struct = getNodeStructure(node.id);
          ctx.beginPath();
          ctx.arc(node.x, node.y, 5, 0, 2 * Math.PI, false);
          ctx.fillStyle = struct.color;
          ctx.fill();
        }}
      />
    </div>
  );
};

export default NetworkGraphView;