import pandas as pd
from datetime import timedelta
from graph_builder import load_edges

MAX_HOP_DEPTH = 5                  # how many hops deep to search
MAX_HOP_GAP_HOURS = 72             # max time between consecutive hops
AMOUNT_TOLERANCE = 0.15            # 15% tolerance for amount conservation across a hop
MIN_CHAIN_AMOUNT = 50000           # ignore tiny chains, not worth investigating


def build_outgoing_index(edges_df: pd.DataFrame) -> dict:
    """
    Pre-index transactions by sender for fast lookup during chain traversal.
    Each sender maps to their outgoing transactions sorted by timestamp.
    """
    index = {}
    for sender, group in edges_df.groupby("Sender_account"):
        index[sender] = group.sort_values("timestamp").to_dict("records")
    return index


def amount_conserved(incoming_amount: float, outgoing_amount: float,
                      tolerance: float = AMOUNT_TOLERANCE) -> bool:
    """
    Layering typically forwards most of the received amount onward,
    sometimes minus a small cut. Checks outgoing is within tolerance
    band of incoming (allows it to be slightly less, not more).
    """
    if incoming_amount <= 0:
        return False
    ratio = outgoing_amount / incoming_amount
    return (1 - tolerance) <= ratio <= 1.05  # allow tiny markup for rounding


def find_chains_from_account(start_account, outgoing_index: dict,
                              max_depth: int = MAX_HOP_DEPTH,
                              max_gap_hours: int = MAX_HOP_GAP_HOURS,
                              min_amount: float = MIN_CHAIN_AMOUNT) -> list:
    """
    DFS from a starting account, following only hops where the outgoing
    transaction happens after the incoming one, within a time gap limit,
    and conserves roughly the same amount. This distinguishes deliberate
    layering from coincidental unrelated transfers.
    """
    chains = []

    def dfs(current_account, current_amount, current_time, path, depth):
        if depth >= max_depth:
            return

        outgoing_txs = outgoing_index.get(current_account, [])

        for tx in outgoing_txs:
            tx_time = tx["timestamp"]

            # must happen after we received funds, within the gap window
            if tx_time <= current_time:
                continue
            if (tx_time - current_time) > timedelta(hours=max_gap_hours):
                continue

            tx_amount = tx["amount_local_npr"]

            if not amount_conserved(current_amount, tx_amount):
                continue

            next_account = tx["Receiver_account"]

            if next_account in [p["account"] for p in path]:
                continue  # avoid revisiting (cycles are handled separately)

            new_path = path + [{
                "account": next_account,
                "amount": tx_amount,
                "timestamp": tx_time,
            }]

            if len(new_path) >= 3 and tx_amount >= min_amount:
                chains.append(list(new_path))

            dfs(next_account, tx_amount, tx_time, new_path, depth + 1)

    # seed the path with the start account
    start_outgoing = outgoing_index.get(start_account, [])
    for tx in start_outgoing:
        if tx["amount_local_npr"] < min_amount:
            continue
        seed_path = [
            {"account": start_account, "amount": tx["amount_local_npr"], "timestamp": tx["timestamp"]},
            {"account": tx["Receiver_account"], "amount": tx["amount_local_npr"], "timestamp": tx["timestamp"]},
        ]
        dfs(tx["Receiver_account"], tx["amount_local_npr"], tx["timestamp"], seed_path, 1)

    return chains


def detect_layering(edges_df: pd.DataFrame = None,
                     max_depth: int = MAX_HOP_DEPTH,
                     min_amount: float = MIN_CHAIN_AMOUNT,
                     candidate_limit: int = None) -> pd.DataFrame:
    """
    Run layering chain detection across candidate starting accounts.
    candidate_limit caps how many starting senders to scan — full run
    can be slow given the dataset size, so start with a limit while testing.
    """
    if edges_df is None:
        edges_df = load_edges()

    outgoing_index = build_outgoing_index(edges_df)

    # candidates: accounts with at least one outgoing transaction above min_amount
    candidates = edges_df[edges_df["amount_local_npr"] >= min_amount]["Sender_account"].unique()

    if candidate_limit:
        candidates = candidates[:candidate_limit]

    results = []
    for start_account in candidates:
        chains = find_chains_from_account(
            start_account, outgoing_index,
            max_depth=max_depth, min_amount=min_amount
        )
        for chain in chains:
                    results.append({
                        "origin": int(start_account),
                        "chain_accounts": [int(p["account"]) for p in chain],
                        "hop_count": int(len(chain)),
                        "start_amount": float(chain[0]["amount"]),
                        "end_amount": float(chain[-1]["amount"]),
                        "amount_retained_pct": float(round((chain[-1]["amount"] / chain[0]["amount"]) * 100, 1)),
                        "start_time": chain[0]["timestamp"],
                        "end_time": chain[-1]["timestamp"],
                        "duration_hours": float(round((chain[-1]["timestamp"] - chain[0]["timestamp"]).total_seconds() / 3600, 1)),
                    })

    if not results:
        return pd.DataFrame(columns=[
            "origin", "chain_accounts", "hop_count", "start_amount",
            "end_amount", "amount_retained_pct", "start_time", "end_time", "duration_hours"
        ])

    df = pd.DataFrame(results)

    # keep the longest chain per origin to avoid flooding with sub-chains
    df = df.sort_values("hop_count", ascending=False)
    df = df.drop_duplicates(subset="origin", keep="first").reset_index(drop=True)

    return df.sort_values(["hop_count", "amount_retained_pct"], ascending=[False, False]).reset_index(drop=True)


def explain_layering(row: pd.Series) -> str:
    path_str = " -> ".join(str(a) for a in row["chain_accounts"])
    return (
        f"Funds originating from {row['origin']} pass through {row['hop_count']} hops "
        f"({path_str}) over {row['duration_hours']:.1f}h, retaining "
        f"{row['amount_retained_pct']:.0f}% of the original NPR {row['start_amount']:,.0f} "
        f"— consistent with layering."
    )


if __name__ == "__main__":
    edges_df = load_edges()
    print(f"Loaded {len(edges_df)} transactions\n")

    print("Detecting layering chains (testing on first 500 candidate senders)...")
    layering_df = detect_layering(edges_df, candidate_limit=500)
    print(f"Flagged {len(layering_df)} layering chains\n")

    for _, row in layering_df.head(5).iterrows():
        print("  " + explain_layering(row))