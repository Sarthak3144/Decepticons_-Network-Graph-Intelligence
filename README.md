# Decepticons_-Network-Graph-Intelligence


# Network and Graph Intelligence System for Anti-Money Laundering (AML)

This repository contains a graph-based transaction monitoring and forensic analysis pipeline developed for Track 3 (Network & Graph Intelligence). The system ingests banking transactional records, models structural behavior using directed graph networks, isolates established financial crime typologies, and exports a prioritize-ranked risk matrix with clear natural language justifications for investigators.

## System Overview

Traditional transaction monitoring engines analyze isolated transactions using hardcoded rule thresholds. This pipeline shifts focus to relational network topology, identifying anomalies across multiple hops that standard relational databases miss.

The system specifically targets three primary money laundering structures:
* **Smurfing (Fan-In / Fan-Out):** Layered asset structuring where high-volume accounts dispatch or aggregate split capital to or from peripheral nodes.
* **Layering (Pass-Through Bottlenecks):** Middleman nodes that maintain high centrality by rapidly routing funds across intermediate paths.
* **Circular Flows (Directed Loops):** Multi-hop execution paths where assets loop back to origin or related accounts to disrupt the audit trail.

---

## Architectural Pipeline and Notebook Design

The project is structured sequentially within a single Google Colab framework to ensure reproducibility:

### 1. Data Engineering and Temporal Network Parsing
The system reads the transactional data and initializes a Directed Graph (`nx.DiGraph`) via NetworkX. Rather than parsing raw transaction volume naively, transactions are grouped by unique directed channels (`Sender_account` to `Receiver_account`). Weights are assigned based on aggregated transacted amounts and localized temporal variables like average hour of daily placement.

### 2. High-Speed Structural Feature Extraction
To ensure fast execution during tight delivery timelines, the pipeline implements localized optimizations for computationally heavy network properties:
* **Targeted Centrality Mapping:** Bypasses exact global shortest-path calculations across innocent retail clusters. Instead, it measures `betweenness_centrality_subset` exclusively on active pass-through nodes with concurrent inbound and outbound footprints.
* **Bounded Cycle Tracking:** Runs depth-bounded iterations to quickly map short circular loops (max length 3) before they cause memory allocation timeouts.

### 3. Core Engine Fusion (EDA Integration)
The framework integrates empirical discoveries made during the Exploratory Data Analysis (EDA) phase. Accounts displaying perfect 1.0 amount-conservation metrics (where incoming balances are instantly moved downstream) are integrated via a localized reference validation database (`eda_flagged_suspicious_accounts.csv`). These entities receive a definitive risk priority adjustment inside the central mathematical formula.

### 4. Mathematical Composite Scoring Model
Every account is evaluated using a normalized weight distribution matrix that translates pure structural layout values into an explicit score between 0 and 100:

$$Structural\ Risk\ Score = (Betweenness \times 35) + (Cycle\ Participant \times 25) + (EDA\ Flag \times 20) + (Layering\ Hub \times 10) + (Smurfing\ Multiplier \times 10)$$

High-risk entities from internal KYC databases inflate this baseline score to finalize the absolute risk positioning.

---

## Deliverables and Explanations

The primary output file, `final_ranked_suspicious_accounts.csv`, contains the ultimate ranked registry of high-risk nodes. To satisfy modern compliance requirements, the script matches numeric scoring parameters with explicit, rule-generated plain text audit narratives:

* *Circular Loop Flag:* "Participates in a closed directed cycle path where funds loop back to origins."
* *Layering Hub Flag:* "Acts as a critical transaction bridge node with an elevated betweenness centrality footprint."
* *Fan-Out Indicator:* "Exhibits a structural fan-out pattern splitting asset flows into multiple directions with zero inbound history."

---

## How to Run the Implementation

### Prerequisites
Ensure your Python environment contains the standard data science and network analysis stack:
```bash
pip install pandas numpy networkx matplotlib seaborn
