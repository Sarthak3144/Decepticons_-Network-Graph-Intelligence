import pandas as pd
import networkx as nx
from datetime import timedelta
from itertools import combinations
from graph_builder import load_edges, build_multigraph

MAX_CYCLE_LENGTH = 5            # max hops in a cycle to search for
MAX_CYCLE_DURATION_HOURS = 168  # 7 days — cycle must complete within this window
AMOUNT_TOLERANCE = 0.15         # 15% tolerance for amount conservation around the cycle
MIN_CYCLE_AMOUNT = 50000        # ignore tiny circular flows


def build_simple_cycle_graph(edges_df: pd.DataFrame) -> nx.DiGraph:
    """
    Collapsed graph (one edge per unique sender->receiver pair) used only
    to enumerate candidate cycle structures cheaply with networkx. Time and
    amount validation happens afterward on the raw transactions.
    """
    G = nx.DiGraph()
    pairs = edges_df.groupby(["Sender_account", "Receiver_account"]).size().reset_index()
    for _, row in pairs.iterrows():
        G.add_edge(row["Sender_account"], row["Receiver_account"])
    return G


def find_candidate_cycles(G: nx.DiGraph, max_length: int = MAX_CYCLE_LENGTH) -> list:
    """
    Use networkx's cycle enumeration restricted to a max length, since
    simple_cycles on the full graph can blow up combinatorially.
    """
    cycles = []
    for cycle in nx.simple_cycles(G, length_bound=max_length):
        if 2 <= len(cycle) <= max_length:
            cycles.append(cycle)
    return cycles


def validate_cycle_timing_and_amount(cycle: list, edges_df: pd.DataFrame,
                                      max_duration_hours: int = MAX_CYCLE_DURATION_HOURS,
                                      amount_tolerance: float = AMOUNT_TOLERANCE,
                                      min_amount: float = MIN_CYCLE_AMOUNT) -> dict:
    """
    A structural cycle (A->B->C->A) is only suspicious if the hops happen
    in increasing time order within a bounded window AND the amount is
    roughly conserved hop to hop. Random unrelated transfers that happen
    to form a structural cycle should not be flagged.

    Returns a dict with validation result and supporting transaction path,
    or None if no valid time-respecting instance of this cycle exists.
    """
    n = len(cycle)
    extended_cycle = cycle + [cycle[0]]  # close the loop

    # Get all transactions for each hop in the cycle
    hop_transactions = []
    for i in range(n):
        sender = extended_cycle[i]
        receiver = extended_cycle[i + 1]
        hop_txs = edges_df[
            (edges_df["Sender_account"] == sender) &
            (edges_df["Receiver_account"] == receiver) &
            (edges_df["amount_local_npr"] >= min_amount)
        ].sort_values("timestamp")
        if hop_txs.empty:
            return None
        hop_transactions.append(hop_txs)

    # Try to find a time-respecting, amount-conserving chain starting from
    # each candidate transaction on the first hop
    for _, start_tx in hop_transactions[0].iterrows():
        path = [start_tx]
        current_time = start_tx["timestamp"]
        current_amount = start_tx["amount_local_npr"]
        valid = True

        for hop_idx in range(1, n):
            next_candidates = hop_transactions[hop_idx][
                hop_transactions[hop_idx]["timestamp"] > current_time
            ]
            if next_candidates.empty:
                valid = False
                break

            # find a candidate within amount tolerance, closest in time
            next_candidates = next_candidates.copy()
            next_candidates["amount_ratio"] = next_candidates["amount_local_npr"] / current_amount
            matched = next_candidates[
                next_candidates["amount_ratio"].between(1 - amount_tolerance, 1.05)
            ]

            if matched.empty:
                valid = False
                break

            next_tx = matched.iloc[0]
            path.append(next_tx)
            current_time = next_tx["timestamp"]
            current_amount = next_tx["amount_local_npr"]

        if not valid:
            continue

        total_duration = (path[-1]["timestamp"] - path[0]["timestamp"]).total_seconds() / 3600
        if total_duration > max_duration_hours:
            continue

        return {
            "cycle_accounts": cycle,
            "cycle_length": n,
            "path": path,
            "start_amount": path[0]["amount_local_npr"],
            "end_amount": path[-1]["amount_local_npr"],
            "amount_retained_pct": round((path[-1]["amount_local_npr"] / path[0]["amount_local_npr"]) * 100, 1),
            "start_time": path[0]["timestamp"],
            "end_time": path[-1]["timestamp"],
            "duration_hours": round(total_duration, 1),
        }

    return None


def detect_cycles(edges_df: pd.DataFrame = None,
                   max_length: int = MAX_CYCLE_LENGTH,
                   max_candidates: int = None) -> pd.DataFrame:
    """
    Full pipeline: enumerate structural cycles, then validate each one
    against timing and amount conservation to confirm it's a real
    circular money flow rather than a structural coincidence.
    """
    if edges_df is None:
        edges_df = load_edges()

    print("Building collapsed graph for cycle search...")
    G = build_simple_cycle_graph(edges_df)

    print(f"Searching for structural cycles (max length {max_length})...")
    candidate_cycles = find_candidate_cycles(G, max_length=max_length)
    print(f"Found {len(candidate_cycles)} structural cycle candidates")

    if max_candidates:
        candidate_cycles = candidate_cycles[:max_candidates]

    results = []
    for cycle in candidate_cycles:
        validated = validate_cycle_timing_and_amount(cycle, edges_df)
        if validated:
            results.append(validated)

    if not results:
        return pd.DataFrame(columns=[
            "cycle_accounts", "cycle_length", "start_amount", "end_amount",
            "amount_retained_pct", "start_time", "end_time", "duration_hours"
        ])

    df = pd.DataFrame([{
            "cycle_accounts": [int(a) for a in r["cycle_accounts"]],
            "cycle_length": int(r["cycle_length"]),
            "start_amount": float(r["start_amount"]),
            "end_amount": float(r["end_amount"]),
            "amount_retained_pct": float(r["amount_retained_pct"]),
            "start_time": r["start_time"],
            "end_time": r["end_time"],
            "duration_hours": float(r["duration_hours"]),
        } for r in results])

    return df.sort_values("amount_retained_pct", ascending=False).reset_index(drop=True)


def explain_cycle(row: pd.Series) -> str:
    path_str = " -> ".join(str(a) for a in row["cycle_accounts"]) + f" -> {row['cycle_accounts'][0]}"
    return (
        f"Circular flow detected: {path_str} over {row['duration_hours']:.1f}h, "
        f"retaining {row['amount_retained_pct']:.0f}% of the original NPR {row['start_amount']:,.0f} "
        f"— funds return to the originating account, consistent with a laundering loop."
    )


if __name__ == "__main__":
    edges_df = load_edges()
    print(f"Loaded {len(edges_df)} transactions\n")

    # max_candidates caps validation work while testing — cycle enumeration
    # itself can already be expensive on dense graphs
    cycles_df = detect_cycles(edges_df, max_length=4, max_candidates=2000)
    print(f"\nValidated {len(cycles_df)} time-respecting, amount-conserving cycles\n")

    for _, row in cycles_df.head(5).iterrows():
        print("  " + explain_cycle(row))