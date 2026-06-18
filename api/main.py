"""
main.py
Track 4 — Risk Scoring & Prioritization (API Service Layer)
AI/ML Intelligence Hackathon, June 2026

FastAPI backend application serving risk scores, complex topological graph intelligence,
and real-time SHAP explanation factors to power the compliance dashboard interface.

Run from api/: uvicorn main:app --reload --port 8000
"""

import os
import sys
import json
import pandas as pd
import xgboost as xgb
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# Ensure api directory can access src directory sibling modules
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.abspath(os.path.join(CURRENT_DIR, '..'))
SRC_DIR = os.path.join(PARENT_DIR, 'src')

if PARENT_DIR not in sys.path:
    sys.path.append(PARENT_DIR)
if SRC_DIR not in sys.path:
    sys.path.append(SRC_DIR)

from src.explainer import build_explainer, explain_account

app = FastAPI(
    title="Risk Prioritization Engine Engine API",
    description="Compliance Triage Back-End Orchestrator for Track 3 & Track 4",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permits localhost:5173 to connect seamlessly
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables to act as memory cache storage for fast response metrics
DB = {}

@app.on_event("startup")
def startup_event():
    """Initializes and caches heavy structural data tables and models into RAM at boot time."""
    print("Booting Core Engine API - Preloading Models and Scoring Ledgers...")
    try:
        # 1. Load ML priority metrics
        scores_path = "../outputs/account_risk_scores.csv"
        if os.path.exists(scores_path):
            DB["scores"] = pd.read_csv(scores_path)
        else:
            raise FileNotFoundError(f"Missing core scoring ledger artifact at {scores_path}")
            
        # 2. Load Network Graph metrics
        net_path = "../outputs/network_intelligence_scores.csv"
        if os.path.exists(net_path):
            DB["network"] = pd.read_csv(net_path)
        else:
            DB["network"] = pd.DataFrame()
            
        # 3. Initialize prediction explanation objects
        model = xgb.XGBClassifier()
        model.load_model("../models/xgb_risk_model.json")
        
        with open("../models/feature_columns.json") as f:
            feature_cols = json.load(f)
            
        from src.model import load_data, build_account_features
        ml, accounts = load_data("../data")
        feat = build_account_features(ml, accounts)
        
        DB["model"] = model
        DB["feature_cols"] = feature_cols
        DB["feat"] = feat
        DB["explainer"] = build_explainer(model)
        
        print("Preloading sequence completed successfully. Systems operational.")
    except Exception as e:
        print(f"CRITICAL BOOT ERROR: {str(e)}")

@app.get("/api/triage/queue")
def get_triage_queue(limit: int = 50):
    """Returns the primary compliance queue ranked by risk score to power the master dashboard."""
    if "scores" not in DB:
        raise HTTPException(status_code=503, detail="Scoring engine ledger uninitialized.")
    
    merged = DB["scores"].copy()
    if not DB["network"].empty:
        merged = merged.merge(DB["network"][["account_id", "network_risk_score", "structural_explanation"]], on="account_id", how="left")
        
    df_sorted = merged.sort_values(by="risk_score", ascending=False).head(limit)
    return df_sorted.fillna(0).to_dict(orient="records")

@app.get("/api/risk/{account_id}")
def get_account_risk_profile(account_id: int):
    """Returns granular details, network topology, and SHAP factors for a specific target account."""
    if "feat" not in DB:
        raise HTTPException(status_code=503, detail="Agnostic inference engine uninitialized.")
        
    try:
        explanation = explain_account(
            account_id=account_id,
            model=DB["model"],
            explainer=DB["explainer"],
            feat=DB["feat"],
            feature_cols=DB["feature_cols"]
        )
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Account configuration {account_id} not indexed.")

    net_profile = {}
    if not DB["network"].empty:
        net_match = DB["network"][DB["network"]["account_id"] == account_id]
        if not net_match.empty:
            net_profile = net_match.iloc[0].to_dict()

    return {
        "account_id": account_id,
        "risk_score": explanation["risk_score"],
        "is_suspicious_ground_truth": explanation["is_suspicious_account_label"],
        "structural_risk_factors": explanation["top_factors"],
        "network_intelligence": net_profile
    }

@app.get("/api/graph/topology")
def get_graph_topology(limit: int = 100):
    """Returns the nodes and edges required to render an interactive network visual canvas."""
    # Reference the local global DB context safely
    if "feat" not in DB:
        raise HTTPException(status_code=503, detail="Data layers uninitialized.")
        
    csv_path = "../data/ml_features.csv"
    if not os.path.exists(csv_path):
        raise HTTPException(status_code=404, detail="Transaction ledger file not found.")

    ml_data = pd.read_csv(csv_path).head(limit)
    
    nodes = set(ml_data["Sender_account"].unique()).union(set(ml_data["Receiver_account"].unique()))
    
    nodes_list = [{"id": int(n), "label": f"Acc {n}"} for n in nodes]
    links_list = [
        {
            "source": int(row["Sender_account"]), 
            "target": int(row["Receiver_account"]), 
            "val": float(row["amount_local_npr"])
        } for _, row in ml_data.iterrows()
    ]
    
    return {"nodes": nodes_list, "links": links_list}

@app.get("/api/health")
def health_check():
    """System heartbeat verification ping."""
    return {"status": "healthy", "cached_keys": list(DB.keys())}