"""
graph_features.py
Track 3 — Network & Graph Intelligence
AI/ML Intelligence Hackathon, June 2026

Constructs a directed transaction network from transaction edges, uncovers
structural topologies consistent with laundering typologies (smurfing fan-outs,
layering chains, and circular loops), and produces a ranked network risk list.
"""

import os
import json
import pandas as pd
import numpy as np
import networkx as nx

DATA_DIR = "../data"
OUTPUT_DIR = "../outputs"
MODEL_DIR = "../models"

def load_graph_data(data_dir: str = DATA_DIR):
    """Loads transaction records to construct network edges."""
    # Using ml_features as it contains the source sender-receiver ledger
    ml = pd.read_csv(os.path.join(data_dir, "ml_features.csv"))
    return ml

def build_transaction_graph(df: pd.DataFrame) -> nx.DiGraph:
    """Builds a directed multi-edge weighted network representation."""
    print("Building network graph representation...")
    G = nx.DiGraph()
    
    # Aggregate parallel edges between identical nodes to streamline multi-hop execution
    edge_agg = df.groupby(['Sender_account', 'Receiver_account']).agg(
        total_amount=('amount_local_npr', 'sum'),
        tx_count=('amount_local_npr', 'count')
    ).reset_index()
    
    for _, row in edge_agg.iterrows():
        G.add_edge(
            int(row['Sender_account']), 
            int(row['Receiver_account']), 
            weight=float(row['total_amount']),
            tx_count=int(row['tx_count'])
        )
    return G

def extract_graph_intelligence(G: nx.DiGraph, output_dir: str = OUTPUT_DIR):
    """Computes advanced topological flow metrics beyond simple degree centrality."""
    print("Analyzing structural flow configurations...")
    
    # 1. Degree ratios to find dispersion/consolidation points (Smurfing indicators)
    in_degrees = dict(G.in_degree())
    out_degrees = dict(G.out_degree())
    
    # 2. PageRank to find highly systemic risk hubs
    pagerank = nx.pagerank(G, weight='weight')
    
    # 3. Finding Strongly Connected Components (Circular Flows)
    cycles = list(nx.strongly_connected_components(G))
    cycle_map = {}
    for idx, component in enumerate(cycles):
        if len(component) > 1: # True circular flow loop involving multiple nodes
            for node in component:
                cycle_map[node] = len(component)

    # 4. Compile node network profiles
    network_nodes = []
    for node in G.nodes():
        ind = in_degrees.get(node, 0)
        outd = out_degrees.get(node, 0)
        total_deg = ind + outd
        
        # Heuristic ratio flags
        fan_out_ratio = outd / (ind + 1) if ind == 0 or outd > ind else 0
        fan_in_ratio = ind / (outd + 1) if outd == 0 or ind > outd else 0
        
        network_nodes.append({
            "account_id": node,
            "net_in_degree": ind,
            "net_out_degree": outd,
            "pagerank_score": round(pagerank.get(node, 0.0), 6),
            "in_cycle_loop_size": cycle_map.get(node, 0),
            "smurfing_fan_out_score": round(fan_out_ratio, 2),
            "smurfing_fan_in_score": round(fan_in_ratio, 2)
        })
        
    net_df = pd.DataFrame(network_nodes)
    
    # Define composite network risk ranking score
    net_df["network_risk_score"] = (
        (net_df["pagerank_score"] * 1000) + 
        (net_df["smurfing_fan_out_score"] * 2) + 
        (net_df["in_cycle_loop_size"] * 5)
    ).round(2)
    
    net_df = net_df.sort_values("network_risk_score", ascending=False).reset_index(drop=True)
    
    # Add structural explanations
    explanations = []
    for _, r in net_df.iterrows():
        exp = "Standard network transactional activity."
        if r["in_cycle_loop_size"] > 0:
            exp = f"Circular flow vulnerability detected: Node participates in a closed {int(r['in_cycle_loop_size'])}-hop loop structure."
        elif r["smurfing_fan_out_score"] > 5:
            exp = f"Smurfing fan-out behavior: Account fans out funds across {int(r['net_out_degree'])} downstream counter-parties with low consolidation."
        elif r["net_in_degree"] > 10 and r["net_out_degree"] > 10:
            exp = "High-velocity layering hub: High multi-hop input routing forwarding directly to external entities."
        explanations.append(exp)
        
    net_df["structural_explanation"] = explanations
    
    # Save network feature metrics manifest
    os.makedirs(output_dir, exist_ok=True)
    net_df.to_csv(os.path.join(output_dir, "network_intelligence_scores.csv"), index=False)
    print(f"Network intelligence scores saved to {output_dir}/network_intelligence_scores.csv")
    
    return net_df

def main():
    ml = load_graph_data()
    G = build_transaction_graph(ml)
    net_df = extract_graph_intelligence(G)
    
    print("\n=== Top 5 Suspicious Graph Structures Surfaced ===")
    print(net_df[["account_id", "network_risk_score", "structural_explanation"]].head(5).to_string(index=False))

if __name__ == "__main__":
    main()