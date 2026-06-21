import pandas as pd
import networkx as nx
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"


def load_edges() -> pd.DataFrame:
    """
    Load and clean the transaction edge list.
    Each row: Sender_account -> Receiver_account, with amount and timestamp.
    """
    df = pd.read_csv(DATA_DIR / "graph_edges.csv")

    # Combine Date + Time into a single sortable datetime
    df["timestamp"] = pd.to_datetime(
        df["Date"].astype(str) + " " + df["Time"].astype(str),
        errors="coerce"
    )

    df = df.dropna(subset=["timestamp", "Sender_account", "Receiver_account", "amount_local_npr"])
    df = df.sort_values("timestamp").reset_index(drop=True)

    return df


def build_multigraph(edges_df: pd.DataFrame = None) -> nx.MultiDiGraph:
    """
    Build a directed multigraph — multiple edges allowed between the same
    pair of accounts because the same sender->receiver pair can transact
    multiple times at different timestamps/amounts. This preserves every
    individual transaction as a distinct edge, which is required for
    time-windowed pattern detection (fan-out, layering, cycles).
    """
    if edges_df is None:
        edges_df = load_edges()

    G = nx.MultiDiGraph()

    for _, row in edges_df.iterrows():
        G.add_edge(
            row["Sender_account"],
            row["Receiver_account"],
            amount=row["amount_local_npr"],
            timestamp=row["timestamp"],
            row_index=row.get("row_index", None),
        )

    return G


def build_simple_graph(edges_df: pd.DataFrame = None) -> nx.DiGraph:
    """
    Collapsed view: one edge per sender->receiver pair, aggregating
    all individual transactions between them. Useful for centrality
    metrics and quick structural overviews where per-transaction
    granularity isn't needed.
    """
    if edges_df is None:
        edges_df = load_edges()

    G = nx.DiGraph()

    grouped = edges_df.groupby(["Sender_account", "Receiver_account"]).agg(
        total_amount=("amount_local_npr", "sum"),
        tx_count=("amount_local_npr", "count"),
        avg_amount=("amount_local_npr", "mean"),
        first_tx=("timestamp", "min"),
        last_tx=("timestamp", "max"),
    ).reset_index()

    for _, row in grouped.iterrows():
        G.add_edge(
            row["Sender_account"],
            row["Receiver_account"],
            total_amount=row["total_amount"],
            tx_count=row["tx_count"],
            avg_amount=row["avg_amount"],
            first_tx=row["first_tx"],
            last_tx=row["last_tx"],
        )

    return G


def attach_account_attributes(G: nx.Graph) -> nx.Graph:
    """
    Enrich graph nodes with KYC attributes from accounts.csv
    (risk_grade, pep_flag, sanctions_hit, acct_type, is_person).
    Required for explanations like "account is flagged PEP" alongside
    structural findings.
    """
    accounts = pd.read_csv(DATA_DIR / "accounts.csv")
    accounts_map = accounts.set_index("account_id").to_dict(orient="index")

    for node in G.nodes:
        attrs = accounts_map.get(node, {})
        G.nodes[node].update({
            "risk_grade":    attrs.get("risk_grade", "UNKNOWN"),
            "acct_type":     attrs.get("acct_type", "UNKNOWN"),
            "pep_flag":      attrs.get("pep_flag", 0),
            "sanctions_hit": attrs.get("sanctions_hit", 0),
            "is_person":     attrs.get("is_person", None),
            "institution":   attrs.get("institution", "UNKNOWN"),
        })

    return G


def get_graph_summary(G: nx.Graph) -> dict:
    return {
        "num_nodes": G.number_of_nodes(),
        "num_edges": G.number_of_edges(),
        "is_multigraph": G.is_multigraph(),
        "density": nx.density(G),
    }


if __name__ == "__main__":
    edges_df = load_edges()
    print(f"Loaded {len(edges_df)} transactions")
    print(f"Date range: {edges_df['timestamp'].min()} to {edges_df['timestamp'].max()}")

    print("\nBuilding multigraph (per-transaction edges)...")
    MG = build_multigraph(edges_df)
    MG = attach_account_attributes(MG)
    print(get_graph_summary(MG))

    print("\nBuilding simple graph (aggregated pairs)...")
    SG = build_simple_graph(edges_df)
    SG = attach_account_attributes(SG)
    print(get_graph_summary(SG))

    # Quick sanity check — highest out-degree account in simple graph
    out_degrees = dict(SG.out_degree())
    top_sender = max(out_degrees, key=out_degrees.get)
    print(f"\nTop out-degree account: {top_sender} -> {out_degrees[top_sender]} unique receivers")
    print(f"  risk_grade: {SG.nodes[top_sender].get('risk_grade')}")
    print(f"  pep_flag: {SG.nodes[top_sender].get('pep_flag')}")