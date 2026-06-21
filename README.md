# Network Intelligence — AML Structural Pattern Detection

**Track 3 — Network & Graph Intelligence**
AI/ML Intelligence Hackathon 

Money laundering rarely shows up in a single transaction. It hides in the *shape* of money movement — one account quietly splitting funds across a dozen others, a chain of transfers passing value hand to hand, or a loop that brings money right back to where it started. This project models a banking transaction dataset as a directed graph and hunts for exactly those shapes: **fan-out/fan-in (smurfing)**, **layering chains**, and **circular flows** — then ranks the accounts involved and explains, in plain language, what structural evidence put them there.

---

## Why graphs, not just transactions

A single suspicious transaction is easy to flag and easy to miss. A *pattern* — the same account sending to 14 others within a day, all converging on one collector — is invisible at the row level but obvious once you draw it as a graph. That's the core bet of this system: structural reasoning over flow direction, timing, and amount conservation finds things a flat table never will.

---

## What it does

| Pattern | Detection logic |
|---|---|
| **Fan-out / Fan-in** | Rolling time-window scan (24h) per account — flags senders splitting funds across many receivers, and receivers converging funds from many senders |
| **Convergence chains** | Cross-references fan-out receivers against fan-in senders to catch deliberate split-then-reconverge structures, not coincidental activity |
| **Layering** | Depth-limited DFS following multi-hop transfer chains where each hop happens after the last and conserves ~85–105% of the incoming amount |
| **Circular flows** | Graph cycle enumeration (`networkx.simple_cycles`) validated against real timestamps and amount conservation — only time-respecting, value-conserving loops count |

Every flagged account gets a composite risk score, the structural patterns that triggered it, and a KYC-aware bonus (PEP flag, sanctions hit, existing risk grade) layered on top of the structural evidence — never replacing it.

---

## Architecture

```
risk-scoring/
├── api/
│   └── main.py                 FastAPI service — graph, pattern, and explanation endpoints
├── data/
│   ├── accounts.csv             KYC records (65k accounts)
│   ├── transactions.csv         Enriched transaction table
│   ├── ml_features.csv          Model-ready transaction features
│   └── graph_edges.csv          Sender → receiver edge list (100k+ transactions)
├── src/
│   ├── graph_builder.py         Builds the transaction graph + attaches KYC node attributes
│   ├── pattern_fanout.py        Fan-out / fan-in / convergence chain detection
│   ├── pattern_layering.py      Multi-hop layering chain detection
│   ├── pattern_cycles.py        Time-respecting circular flow detection
│   ├── graph_features.py        Centrality metrics as supporting structural signal
│   └── risk_ranker.py           Combines all detectors into one ranked, explained output
├── frontend/
│   └── src/                     React investigation console — graph view + ranked list + pattern tabs
├── notebook/
│   └── EDA.ipynb                Exploratory analysis of the transaction network
├── outputs/
│   └── network_intelligence_scores.csv   Final ranked account output
├── docs/
└── slides/
```

---

## Quickstart

**Backend**
```bash
cd api
pip install -r ../src/requirements.txt
python main.py
```
First boot computes and caches all pattern detections — give it a few minutes. Every restart after that loads instantly from `outputs/`.

**Frontend**
```bash
cd frontend
npm install
npm run dev
```

Visit `localhost:5173`, search any account ID, and the graph traces its neighborhood while the side panel explains exactly why — or why not — it's flagged.

---

## API

| Endpoint | Returns |
|---|---|
| `GET /graph/summary` | Node/edge counts, density |
| `GET /graph/subgraph/{account_id}?hops=N` | Local neighborhood graph for visualization |
| `GET /patterns/fanout` | Ranked fan-out senders |
| `GET /patterns/layering` | Detected multi-hop layering chains |
| `GET /patterns/cycles` | Validated circular flows |
| `GET /accounts/ranked` | Full ranked, scored account list |
| `GET /accounts/{account_id}/explanation` | Score + human-readable structural reasoning for one account |

---

## What makes a result trustworthy here

Degree centrality alone is cheap and misleading — a high-volume legitimate merchant looks identical to a smurfing hub on degree count alone. Every pattern in this system instead requires **temporal ordering** (a hop only counts if it happens *after* the one before it, within a bounded window) and **amount conservation** (a chain only counts if the money roughly survives the hop, not just any two transactions that happen to connect two accounts). That's the difference between *"this account has lots of edges"* and *"this account is structurally consistent with a known laundering typology."*

---

## Tech stack

Python · FastAPI · NetworkX · Pandas · React · JetBrains Mono / Inter
