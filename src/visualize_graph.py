"""
visualize_graph.py
Generates a structural topological network layout mapping high-risk clusters.
"""
import os
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt

def generate_static_plot():
    # Load dataset
    df = pd.read_csv("../data/ml_features.csv")
    
    # Restrict to a subset of edges for visualization clarity
    df_subset = df.head(150) 
    
    G = nx.from_pandas_edgelist(
        df_subset, 
        source='Sender_account', 
        target='Receiver_account', 
        create_using=nx.DiGraph()
    )
    
    plt.figure(figsize=(12, 8), dpi=300)
    plt.style.use('dark_background')
    
    # Compute force-directed positions
    pos = nx.spring_layout(G, k=0.15, seed=42)
    
    # Highlight high-degree nodes
    node_sizes = [50 + (G.degree(node) * 30) for node in G.nodes()]
    
    print("Rendering network map...")
    nx.draw_networkx_nodes(G, pos, node_size=node_sizes, node_color='#10b981', alpha=0.8)
    nx.draw_networkx_edges(G, pos, arrowstyle='->', arrowsize=8, edge_color='#475569', width=0.5, alpha=0.6)
    
    plt.title("Entity Transaction Flow Network Architecture", fontsize=14, color='#f1f5f9', fontfamily='sans-serif', pad=20)
    plt.axis('off')
    
    output_path = "../outputs/network_topology.png"
    plt.savefig(output_path, bbox_inches='tight', transparent=True)
    print(f"Graph image saved successfully to: {output_path}")

if __name__ == "__main__":
    generate_static_plot()