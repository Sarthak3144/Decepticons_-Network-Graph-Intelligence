const API_BASE = "http://localhost:8000";

async function get(path) {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) {
    throw new Error(`API error ${res.status}: ${path}`);
  }
  return res.json();
}

export const api = {
  graphSummary: () => get("/graph/summary"),
  subgraph: (accountId, hops = 1) => get(`/graph/subgraph/${accountId}?hops=${hops}`),
  fanout: (limit = 20) => get(`/patterns/fanout?limit=${limit}`),
  fanin: (limit = 20) => get(`/patterns/fanin?limit=${limit}`),
  cycles: (limit = 20) => get(`/patterns/cycles?limit=${limit}`),
  rankedAccounts: (limit = 50, offset = 0) => get(`/accounts/ranked?limit=${limit}&offset=${offset}`),
  explanation: (accountId) => get(`/accounts/${accountId}/explanation`),
  layering: (limit = 20) => get(`/patterns/layering?limit=${limit}`),
};