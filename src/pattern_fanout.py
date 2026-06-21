import pandas as pd
from datetime import timedelta
from graph_builder import load_edges, attach_account_attributes, build_simple_graph

FANOUT_WINDOW_HOURS = 24
FANOUT_MIN_RECEIVERS = 5          # minimum unique receivers in window to flag
FANIN_MIN_SENDERS = 5             # minimum unique senders converging to flag
CONVERGENCE_MIN_OVERLAP = 0.5     # fraction of fan-out receivers that must forward to same collector


def detect_fanout(edges_df: pd.DataFrame = None,
                   window_hours: int = FANOUT_WINDOW_HOURS,
                   min_receivers: int = FANOUT_MIN_RECEIVERS) -> pd.DataFrame:
    """
    Smurfing fan-out: one sender splits funds to many distinct receivers
    within a short time window. Classic structuring pattern used to keep
    individual transfers below reporting thresholds.
    """
    if edges_df is None:
        edges_df = load_edges()

    edges_df = edges_df.sort_values(["Sender_account", "timestamp"])
    results = []

    for sender, group in edges_df.groupby("Sender_account"):
        group = group.reset_index(drop=True)
        n = len(group)

        for i in range(n):
            window_start = group.loc[i, "timestamp"]
            window_end = window_start + timedelta(hours=window_hours)

            window_rows = group[
                (group["timestamp"] >= window_start) &
                (group["timestamp"] <= window_end)
            ]

            unique_receivers = window_rows["Receiver_account"].nunique()

            if unique_receivers >= min_receivers:
                results.append({
                    "sender": sender,
                    "window_start": window_start,
                    "window_end": window_end,
                    "unique_receivers": unique_receivers,
                    "tx_count": len(window_rows),
                    "total_amount": window_rows["amount_local_npr"].sum(),
                    "avg_amount": window_rows["amount_local_npr"].mean(),
                    "receivers": window_rows["Receiver_account"].unique().tolist(),
                })

    if not results:
        return pd.DataFrame(columns=[
            "sender", "window_start", "window_end", "unique_receivers",
            "tx_count", "total_amount", "avg_amount", "receivers"
        ])

    df = pd.DataFrame(results)

    # Keep only the strongest (widest) window per sender to avoid duplicate
    # overlapping windows flagging the same burst repeatedly
    df = df.sort_values("unique_receivers", ascending=False)
    df = df.drop_duplicates(subset="sender", keep="first").reset_index(drop=True)

    return df.sort_values("unique_receivers", ascending=False).reset_index(drop=True)


def detect_fanin(edges_df: pd.DataFrame = None,
                  window_hours: int = FANOUT_WINDOW_HOURS,
                  min_senders: int = FANIN_MIN_SENDERS) -> pd.DataFrame:
    """
    Fan-in / collector pattern: one receiver collects funds from many
    distinct senders within a short time window. Often the destination
    after a fan-out — money gets split then re-converged.
    """
    if edges_df is None:
        edges_df = load_edges()

    edges_df = edges_df.sort_values(["Receiver_account", "timestamp"])
    results = []

    for receiver, group in edges_df.groupby("Receiver_account"):
        group = group.reset_index(drop=True)
        n = len(group)

        for i in range(n):
            window_start = group.loc[i, "timestamp"]
            window_end = window_start + timedelta(hours=window_hours)

            window_rows = group[
                (group["timestamp"] >= window_start) &
                (group["timestamp"] <= window_end)
            ]

            unique_senders = window_rows["Sender_account"].nunique()

            if unique_senders >= min_senders:
                results.append({
                    "receiver": receiver,
                    "window_start": window_start,
                    "window_end": window_end,
                    "unique_senders": unique_senders,
                    "tx_count": len(window_rows),
                    "total_amount": window_rows["amount_local_npr"].sum(),
                    "avg_amount": window_rows["amount_local_npr"].mean(),
                    "senders": window_rows["Sender_account"].unique().tolist(),
                })

    if not results:
        return pd.DataFrame(columns=[
            "receiver", "window_start", "window_end", "unique_senders",
            "tx_count", "total_amount", "avg_amount", "senders"
        ])

    df = pd.DataFrame(results)
    df = df.sort_values("unique_senders", ascending=False)
    df = df.drop_duplicates(subset="receiver", keep="first").reset_index(drop=True)

    return df.sort_values("unique_senders", ascending=False).reset_index(drop=True)


def find_fanout_fanin_chains(fanout_df: pd.DataFrame, fanin_df: pd.DataFrame,
                              min_overlap: float = CONVERGENCE_MIN_OVERLAP) -> list:
    """
    The strongest smurfing signal: a fan-out sender whose receivers
    significantly overlap with a fan-in collector's senders. This means
    money was deliberately split then re-converged — classic layering
    structure, not just coincidental high activity.
    """
    chains = []

    for _, fo_row in fanout_df.iterrows():
        fo_receivers = set(fo_row["receivers"])

        for _, fi_row in fanin_df.iterrows():
            if fi_row["receiver"] == fo_row["sender"]:
                continue  # skip trivial self loops

            fi_senders = set(fi_row["senders"])
            overlap = fo_receivers & fi_senders

            if not fo_receivers:
                continue

            overlap_ratio = len(overlap) / len(fo_receivers)

            if overlap_ratio >= min_overlap:
                chains.append({
                    "origin_sender": fo_row["sender"],
                    "collector_receiver": fi_row["receiver"],
                    "intermediate_accounts": list(overlap),
                    "overlap_count": len(overlap),
                    "overlap_ratio": round(overlap_ratio, 2),
                    "fanout_window_start": fo_row["window_start"],
                    "fanin_window_end": fi_row["window_end"],
                    "total_amount_out": fo_row["total_amount"],
                    "total_amount_in": fi_row["total_amount"],
                })

    chains.sort(key=lambda x: x["overlap_ratio"], reverse=True)
    return chains


def explain_fanout(row: pd.Series) -> str:
    return (
        f"Account {row['sender']} sent funds to {row['unique_receivers']} "
        f"distinct accounts within {FANOUT_WINDOW_HOURS}h "
        f"({row['tx_count']} transactions, total NPR {row['total_amount']:,.0f}, "
        f"avg NPR {row['avg_amount']:,.0f} per transfer)."
    )


def explain_fanin(row: pd.Series) -> str:
    return (
        f"Account {row['receiver']} received funds from {row['unique_senders']} "
        f"distinct accounts within {FANOUT_WINDOW_HOURS}h "
        f"({row['tx_count']} transactions, total NPR {row['total_amount']:,.0f})."
    )


def explain_chain(chain: dict) -> str:
    return (
        f"Account {chain['origin_sender']} fans out to {chain['overlap_count']} accounts, "
        f"{chain['overlap_ratio']*100:.0f}% of which forward funds to a common collector "
        f"account {chain['collector_receiver']} — consistent with smurfing/layering."
    )


if __name__ == "__main__":
    edges_df = load_edges()
    print(f"Loaded {len(edges_df)} transactions\n")

    print("Detecting fan-out patterns...")
    fanout_df = detect_fanout(edges_df)
    print(f"Flagged {len(fanout_df)} fan-out senders\n")
    for _, row in fanout_df.head(5).iterrows():
        print("  " + explain_fanout(row))

    print("\nDetecting fan-in patterns...")
    fanin_df = detect_fanin(edges_df)
    print(f"Flagged {len(fanin_df)} fan-in receivers\n")
    for _, row in fanin_df.head(5).iterrows():
        print("  " + explain_fanin(row))

    print("\nDetecting fan-out -> fan-in convergence chains...")
    chains = find_fanout_fanin_chains(fanout_df, fanin_df)
    print(f"Found {len(chains)} suspicious convergence chains\n")
    for chain in chains[:5]:
        print("  " + explain_chain(chain))