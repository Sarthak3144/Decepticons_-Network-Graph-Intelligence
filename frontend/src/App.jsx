import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import RiskDashboard from './components/RiskDashboard';
import NetworkGraphView from './components/NetworkGraphView';

function App() {
  return (
    <Router>
      {/* Global Navigation Toggle bar */}
      <div className="absolute bottom-6 right-6 z-50 flex gap-2 bg-slate-900/80 border border-slate-800 p-1.5 rounded-lg backdrop-blur">
        <Link to="/" className="px-3 py-1.5 rounded font-mono text-xs text-slate-300 hover:bg-slate-800 transition">
          📋 Dashboard
        </Link>
        <Link to="/topology" className="px-3 py-1.5 rounded font-mono text-xs text-sky-400 bg-slate-800 border border-slate-700 transition">
          🌐 Global Topology Map
        </Link>
      </div>

      <Routes>
        <Route path="/" element={<RiskDashboard />} />
        <Route path="/topology" element={<NetworkGraphView />} />
      </Routes>
    </Router>
  );
}

export default App;