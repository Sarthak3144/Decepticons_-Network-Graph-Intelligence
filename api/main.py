from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import pandas as pd
import sys

sys.path.append(str(Path(__file__).parent.parent / "src"))

from graph_builder import load_edges, build_simple_graph, attach_account_attributes, get_graph_summary
from pattern_fanout import detect_fanout, detect_fanin, find_fanout_fanin_chains
from pattern_layering import detect_layering
from pattern_cycles import detect_cycles
from risk_ranker import run_full_pipeline, get_account_explanation

app = FastAPI(title="Network Intelligence API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

OUTPUT_DIR = Path(__file__).parent.parent / "outputs"
RANKED_CSV = OUTPUT_DIR / "network_intelligence_scores.csv"

# Cache the ranked results and graph in memory at startup so each API call
# doesn't re-run the full detection pipeline
_state = {
    "ranked_df": None,
    "graph": None,
}


@app.on_event("startup")
def load_or_compute_results():
    if RANKED_CSV.exists():
        print(f"Loading cached results from {RANKED_CSV}")
        df = pd.read_csv(RANKED_CSV)
        _state["ranked_df"] = df
    else:
        print("No cached results found, running full pipeline (this may take a few minutes)...")
        _state["ranked_df"] = run_full_pipeline()

    # Cache pattern detections too, so tabs load instantly instead of
    # recomputing on every click
    edges_df = load_edges()

    fanout_path = OUTPUT_DIR / "fanout_cache.csv"
    fanin_path = OUTPUT_DIR / "fanin_cache.csv"
    layering_path = OUTPUT_DIR / "layering_cache.csv"
    cycles_path = OUTPUT_DIR / "cycles_cache.csv"

    if fanout_path.exists():
        _state["fanout_df"] = pd.read_csv(fanout_path)
    else:
        print("Computing fan-out patterns...")
        df = detect_fanout(edges_df)
        df.to_csv(fanout_path, index=False)
        _state["fanout_df"] = df

    if layering_path.exists():
        _state["layering_df"] = pd.read_csv(layering_path)
    else:
        print("Computing layering patterns (this is the slow one)...")
        df = detect_layering(edges_df, candidate_limit=500)
        df.to_csv(layering_path, index=False)
        _state["layering_df"] = df

    if cycles_path.exists():
        _state["cycles_df"] = pd.read_csv(cycles_path)
    else:
        print("Computing cycle patterns...")
        df = detect_cycles(edges_df, max_length=4, max_candidates=2000)
        df.to_csv(cycles_path, index=False)
        _state["cycles_df"] = df

    print("Building graph for visualization endpoints...")
    G = build_simple_graph(edges_df)
    G = attach_account_attributes(G)
    _state["graph"] = G

    print("API ready.")


@app.on_event("startup")
def load_or_compute_results():
    if RANKED_CSV.exists():
        print(f"Loading cached results from {RANKED_CSV}")
        df = pd.read_csv(RANKED_CSV)
        # patterns_triggered was saved as a comma-joined string, keep as-is
        _state["ranked_df"] = df
    else:
        print("No cached results found, running full pipeline (this may take a few minutes)...")
        _state["ranked_df"] = run_full_pipeline()

    print("Building graph for visualization endpoints...")
    edges_df = load_edges()
    G = build_simple_graph(edges_df)
    G = attach_account_attributes(G)
    _state["graph"] = G

    print("API ready.")

@app.get("/")
def root():
    return {
        "service": "Network Intelligence API",
        "track": "Track 3 — Network & Graph Intelligence",
        "endpoints": [
            "/graph/summary",
            "/graph/subgraph/{account_id}",
            "/patterns/fanout",
            "/patterns/fanin",
            "/patterns/layering",
            "/patterns/cycles",
            "/accounts/ranked",
            "/accounts/{account_id}/explanation",
        ],
    }    

    
    
# @app.get("/patterns/layering")
# def get_layering_patterns(limit: int = 20, candidate_limit: int = 500):
#     edges_df = load_edges()
#     df = detect_layering(edges_df, candidate_limit=candidate_limit)
#     df = df.head(limit).copy()

#     df["start_time"] = df["start_time"].astype(str)
#     df["end_time"] = df["end_time"].astype(str)

#     # Cast numpy types to native Python types so FastAPI's jsonable_encoder
#     # can serialize them — numpy.int64 inside lists/scalars fails silently
#     # with a cryptic "not iterable" error otherwise
#     df["origin"] = df["origin"].apply(lambda x: int(x))
#     df["chain_accounts"] = df["chain_accounts"].apply(lambda lst: [int(a) for a in lst])
#     df["hop_count"] = df["hop_count"].apply(lambda x: int(x))
#     df["start_amount"] = df["start_amount"].apply(lambda x: float(x))
#     df["end_amount"] = df["end_amount"].apply(lambda x: float(x))
#     df["amount_retained_pct"] = df["amount_retained_pct"].apply(lambda x: float(x))
#     df["duration_hours"] = df["duration_hours"].apply(lambda x: float(x))

#     return df.to_dict(orient="records")


    


@app.get("/graph/summary")
def graph_summary():
    G = _state["graph"]
    if G is None:
        raise HTTPException(status_code=503, detail="Graph not yet loaded")
    return get_graph_summary(G)


@app.get("/graph/subgraph/{account_id}")
def get_subgraph(account_id: int, hops: int = 2):
    """
    Returns a local subgraph around an account — its neighbors up to N hops
    in both directions. Used by the frontend to render a focused visualization
    instead of the entire 65k-node graph.
    """
    G = _state["graph"]
    if account_id not in G:
        raise HTTPException(status_code=404, detail=f"Account {account_id} not found in graph")

    nodes_in_scope = {account_id}
    frontier = {account_id}

    for _ in range(hops):
        next_frontier = set()
        for node in frontier:
            next_frontier.update(G.predecessors(node))
            next_frontier.update(G.successors(node))
        nodes_in_scope.update(next_frontier)
        frontier = next_frontier

    subgraph = G.subgraph(nodes_in_scope)

    nodes_payload = [
        {
            "id": n,
            "risk_grade": subgraph.nodes[n].get("risk_grade"),
            "pep_flag": subgraph.nodes[n].get("pep_flag"),
            "sanctions_hit": subgraph.nodes[n].get("sanctions_hit"),
            "is_center": n == account_id,
        }
        for n in subgraph.nodes
    ]

    edges_payload = [
        {
            "source": u,
            "target": v,
            "total_amount": data.get("total_amount"),
            "tx_count": data.get("tx_count"),
        }
        for u, v, data in subgraph.edges(data=True)
    ]

    return {"center": account_id, "nodes": nodes_payload, "edges": edges_payload}


@app.get("/patterns/fanout")
def get_fanout_patterns(limit: int = 20):
    df = _state.get("fanout_df")
    if df is None or df.empty:
        return []
    return df.head(limit).to_dict(orient="records")


@app.get("/patterns/layering")
def get_layering_patterns(limit: int = 20, candidate_limit: int = 500):
    edges_df = load_edges()
    df = detect_layering(edges_df, candidate_limit=candidate_limit)
    df = df.head(limit).copy()
    df["start_time"] = df["start_time"].astype(str)
    df["end_time"] = df["end_time"].astype(str)
    return df.to_dict(orient="records")


@app.get("/patterns/cycles")
def get_cycle_patterns(limit: int = 20):
    edges_df = load_edges()
    df = detect_cycles(edges_df, max_length=4, max_candidates=2000)
    df = df.head(limit).copy()
    df["start_time"] = df["start_time"].astype(str)
    df["end_time"] = df["end_time"].astype(str)
    return df.to_dict(orient="records")


@app.get("/patterns/fanin")
def get_fanin_patterns(limit: int = 20):
    edges_df = load_edges()
    df = detect_fanin(edges_df)
    df = df.head(limit).copy()
    df["window_start"] = df["window_start"].astype(str)
    df["window_end"] = df["window_end"].astype(str)
    return df.to_dict(orient="records")


# @app.get("/patterns/cycles")
# def get_cycle_patterns(limit: int = 20):
#     edges_df = load_edges()
#     df = detect_cycles(edges_df, max_length=4, max_candidates=2000)
#     df = df.head(limit).copy()

#     df["start_time"] = df["start_time"].astype(str)
#     df["end_time"] = df["end_time"].astype(str)
#     df["cycle_accounts"] = df["cycle_accounts"].apply(lambda lst: [int(a) for a in lst])
#     df["cycle_length"] = df["cycle_length"].apply(lambda x: int(x))
#     df["start_amount"] = df["start_amount"].apply(lambda x: float(x))
#     df["end_amount"] = df["end_amount"].apply(lambda x: float(x))
#     df["amount_retained_pct"] = df["amount_retained_pct"].apply(lambda x: float(x))
#     df["duration_hours"] = df["duration_hours"].apply(lambda x: float(x))

#     return df.to_dict(orient="records")


@app.get("/accounts/ranked")
def get_ranked_accounts(limit: int = 50, offset: int = 0):
    df = _state["ranked_df"]
    if df is None or df.empty:
        return {"total": 0, "results": []}

    page = df.iloc[offset: offset + limit]
    return {
        "total": len(df),
        "limit": limit,
        "offset": offset,
        "results": page.to_dict(orient="records"),
    }


@app.get("/accounts/{account_id}/explanation")
def get_explanation(account_id: int):
    df = _state["ranked_df"]
    if df is None:
        raise HTTPException(status_code=503, detail="Results not yet loaded")

    result = get_account_explanation(account_id, df)
    if not result["found"]:
        return result

    return result


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)