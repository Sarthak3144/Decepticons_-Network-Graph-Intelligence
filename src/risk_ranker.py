import pandas as pd
from pathlib import Path

from graph_builder import load_edges, build_simple_graph, attach_account_attributes, get_graph_summary
from pattern_fanout import detect_fanout, detect_fanin, find_fanout_fanin_chains, explain_fanout, explain_fanin, explain_chain
from pattern_layering import detect_layering, explain_layering
from pattern_cycles import detect_cycles, explain_cycle

OUTPUT_DIR = Path(__file__).parent.parent / "outputs"

# Scoring weights per pattern type — cycles and convergence chains are the
# strongest laundering signals, plain fan-out/fan-in alone is weaker evidence
WEIGHT_CYCLE = 40
WEIGHT_CONVERGENCE_CHAIN = 35
WEIGHT_LAYERING = 25
WEIGHT_FANOUT = 15
WEIGHT_FANIN = 15

# KYC bonus — structural pattern PLUS a flagged KYC attribute is much
# stronger evidence than either alone
KYC_PEP_BONUS = 10
KYC_SANCTIONS_BONUS = 15
KYC_HIGH_RISK_GRADE_BONUS = 5


def score_accounts(fanout_df: pd.DataFrame, fanin_df: pd.DataFrame,
                    chains: list, layering_df: pd.DataFrame,
                    cycles_df: pd.DataFrame, accounts_lookup: dict) -> pd.DataFrame:
    """
    Combine all structural pattern detections into one per-account score.
    An account can be flagged by multiple patterns simultaneously — scores
    accumulate, and each contributing pattern is recorded with its own
    explanation string for the final report.
    """
    scores = {}   # account_id -> running score
    reasons = {}  # account_id -> list of explanation strings
    pattern_flags = {}  # account_id -> set of pattern types triggered

    def add_score(account, points, reason, pattern_type):
        scores[account] = scores.get(account, 0) + points
        reasons.setdefault(account, []).append(reason)
        pattern_flags.setdefault(account, set()).add(pattern_type)

    # --- Fan-out ---
    for _, row in fanout_df.iterrows():
        add_score(row["sender"], WEIGHT_FANOUT, explain_fanout(row), "fanout")

    # --- Fan-in ---
    for _, row in fanin_df.iterrows():
        add_score(row["receiver"], WEIGHT_FANIN, explain_fanin(row), "fanin")

    # --- Fan-out -> fan-in convergence chains (strongest smurfing signal) ---
    for chain in chains:
        add_score(chain["origin_sender"], WEIGHT_CONVERGENCE_CHAIN, explain_chain(chain), "convergence_chain")
        add_score(chain["collector_receiver"], WEIGHT_CONVERGENCE_CHAIN, explain_chain(chain), "convergence_chain")
        for mid_account in chain["intermediate_accounts"]:
            add_score(mid_account, WEIGHT_CONVERGENCE_CHAIN * 0.6, explain_chain(chain), "convergence_chain")

    # --- Layering chains ---
    for _, row in layering_df.iterrows():
        for account in row["chain_accounts"]:
            add_score(account, WEIGHT_LAYERING, explain_layering(row), "layering")

    # --- Cycles ---
    for _, row in cycles_df.iterrows():
        for account in row["cycle_accounts"]:
            add_score(account, WEIGHT_CYCLE, explain_cycle(row), "cycle")

    # --- Apply KYC bonuses ---
    for account in list(scores.keys()):
        attrs = accounts_lookup.get(account, {})
        if attrs.get("pep_flag") == 1:
            scores[account] += KYC_PEP_BONUS
            reasons[account].append(f"Account {account} is flagged as a Politically Exposed Person (PEP).")
        if attrs.get("sanctions_hit") == 1:
            scores[account] += KYC_SANCTIONS_BONUS
            reasons[account].append(f"Account {account} has a sanctions list hit.")
        if attrs.get("risk_grade") == "RISK-HIGH":
            scores[account] += KYC_HIGH_RISK_GRADE_BONUS
            reasons[account].append(f"Account {account} carries a pre-existing RISK-HIGH grade.")

    # --- Build final dataframe ---
    rows = []
    for account, score in scores.items():
        attrs = accounts_lookup.get(account, {})
        rows.append({
            "account_id": account,
            "risk_score": round(min(score, 100), 2),
            "patterns_triggered": ", ".join(sorted(pattern_flags.get(account, []))),
            "num_reasons": len(reasons.get(account, [])),
            "risk_grade": attrs.get("risk_grade", "UNKNOWN"),
            "pep_flag": attrs.get("pep_flag", 0),
            "sanctions_hit": attrs.get("sanctions_hit", 0),
            "institution": attrs.get("institution", "UNKNOWN"),
            "explanation": " | ".join(reasons.get(account, [])[:3]),  # cap to top 3 reasons for readability
        })

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    df = df.sort_values("risk_score", ascending=False).reset_index(drop=True)
    df.insert(0, "rank", range(1, len(df) + 1))

    return df


def get_account_explanation(account_id, ranked_df: pd.DataFrame) -> dict:
    """
    Lookup full explanation for a single account — used by the API's
    /account/{id}/explanation endpoint for the practical demo requirement.
    """
    row = ranked_df[ranked_df["account_id"] == account_id]
    if row.empty:
        return {"account_id": account_id, "found": False, "message": "No structural risk patterns detected for this account."}

    row = row.iloc[0]
    return {
        "account_id": account_id,
        "found": True,
        "rank": int(row["rank"]),
        "risk_score": row["risk_score"],
        "patterns_triggered": row["patterns_triggered"].split(", "),
        "risk_grade": row["risk_grade"],
        "pep_flag": bool(row["pep_flag"]),
        "sanctions_hit": bool(row["sanctions_hit"]),
        "explanation": row["explanation"],
    }


def run_full_pipeline(fanout_window_candidates=None, layering_candidate_limit=500,
                       cycle_max_candidates=2000) -> pd.DataFrame:
    """
    Orchestrates the full Track 3 pipeline: load data, run all three
    pattern detectors, combine into a ranked account risk list, and save.
    """
    print("=" * 60)
    print("RUNNING FULL NETWORK INTELLIGENCE PIPELINE")
    print("=" * 60)

    edges_df = load_edges()
    print(f"\nLoaded {len(edges_df)} transactions")

    accounts_df = pd.read_csv(Path(__file__).parent.parent / "data" / "accounts.csv")
    accounts_lookup = accounts_df.set_index("account_id").to_dict(orient="index")

    print("\n[1/4] Detecting fan-out / fan-in patterns...")
    fanout_df = detect_fanout(edges_df)
    fanin_df = detect_fanin(edges_df)
    chains = find_fanout_fanin_chains(fanout_df, fanin_df)
    print(f"  Fan-out: {len(fanout_df)} | Fan-in: {len(fanin_df)} | Convergence chains: {len(chains)}")

    print("\n[2/4] Detecting layering chains...")
    layering_df = detect_layering(edges_df, candidate_limit=layering_candidate_limit)
    print(f"  Layering chains: {len(layering_df)}")

    print("\n[3/4] Detecting circular flows...")
    cycles_df = detect_cycles(edges_df, max_length=4, max_candidates=cycle_max_candidates)
    print(f"  Validated cycles: {len(cycles_df)}")

    print("\n[4/4] Scoring and ranking accounts...")
    ranked_df = score_accounts(fanout_df, fanin_df, chains, layering_df, cycles_df, accounts_lookup)
    print(f"  Total flagged accounts: {len(ranked_df)}")

    OUTPUT_DIR.mkdir(exist_ok=True)
    output_path = OUTPUT_DIR / "network_intelligence_scores.csv"
    ranked_df.to_csv(output_path, index=False)
    print(f"\nSaved ranked results to {output_path}")

    return ranked_df


if __name__ == "__main__":
    ranked_df = run_full_pipeline()

    print("\n" + "=" * 60)
    print("TOP 10 RANKED ACCOUNTS")
    print("=" * 60)
    for _, row in ranked_df.head(10).iterrows():
        print(f"\nRank {row['rank']} | Account {row['account_id']} | Score: {row['risk_score']}")
        print(f"  Patterns: {row['patterns_triggered']}")
        print(f"  {row['explanation']}")