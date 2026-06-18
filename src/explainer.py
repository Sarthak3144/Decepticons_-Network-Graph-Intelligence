"""
explainer.py
Track 4 — Risk Scoring & Prioritization
AI/ML Intelligence Hackathon, June 2026

Loads the trained XGBoost model from model.py and produces a per-account
SHAP explanation: which features pushed an account's risk score up or
down, and by how much. This is what main.py's /risk/{account_id} endpoint
will call to populate the "why is this account flagged" panel.

Run from src/:  python explainer.py            -> demo on top-5 riskiest accounts
                python explainer.py <account_id> -> explain one account
"""

import json
import os
import sys

import pandas as pd
import shap
import xgboost as xgb

from model import LABEL_COL, build_account_features, load_data

MODEL_DIR = "../models"
OUTPUT_DIR = "../outputs"

MODEL_PATH = os.path.join(MODEL_DIR, "xgb_risk_model.json")
FEATURE_COLS_PATH = os.path.join(MODEL_DIR, "feature_columns.json")


# ---------------------------------------------------------------------------
# Load trained model + feature table
# ---------------------------------------------------------------------------
def load_model_and_features():
    model = xgb.XGBClassifier()
    model.load_model(MODEL_PATH)

    with open(FEATURE_COLS_PATH) as f:
        feature_cols = json.load(f)

    ml, accounts = load_data()
    feat = build_account_features(ml, accounts)

    return model, feature_cols, feat


# ---------------------------------------------------------------------------
# Build a SHAP explainer (Version-agnostic black-box bypass)
# ---------------------------------------------------------------------------
def build_explainer(model):
    # Returns the prediction probability method to pass forward to the sampler path
    return model.predict_proba


# ---------------------------------------------------------------------------
# Per-account explanation
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Per-account explanation
# ---------------------------------------------------------------------------
def explain_account(account_id, model, explainer, feat: pd.DataFrame, feature_cols, top_n: int = 5):
    """Return a dict with the account's risk score and its top SHAP-driven
    risk factors (both upward and downward), sorted by |contribution|.
    """
    row = feat[feat["account_id"] == account_id]
    if row.empty:
        raise ValueError(f"account_id {account_id} not found in feature table")

    # Force cast everything to float to prevent numpy ufunc invariants errors
    X_row = row[feature_cols].astype(float)
    risk_score = round(float(model.predict_proba(X_row)[:, 1][0]) * 100, 2)

    # Grab a background sample and forcefully cast it to float as well
    bg_sample = feat[feature_cols].sample(min(100, len(feat)), random_state=42).astype(float)
    
    # Isolate the target positive class probability mapping (Index 1)
    prediction_wrapper = lambda x: model.predict_proba(x)[:, 1]
    
    # Create an exact permutation/kernel interface instance dynamically
    agnostic_explainer = shap.Explainer(prediction_wrapper, bg_sample)
    shap_output = agnostic_explainer(X_row)
    
    # Handle structural metadata matrix layouts safely
    if hasattr(shap_output, "values"):
        contributions = pd.Series(shap_output.values[0], index=feature_cols)
    else:
        contributions = pd.Series(shap_output[0], index=feature_cols)
        
    feature_values = X_row.iloc[0]

    top = contributions.abs().sort_values(ascending=False).head(top_n).index
    factors = []
    for f in top:
        factors.append({
            "feature": f,
            "feature_value": feature_values[f],
            "shap_contribution": round(float(contributions[f]), 4),
            "direction": "increases risk" if contributions[f] > 0 else "decreases risk",
        })

    return {
        "account_id": int(account_id),
        "risk_score": risk_score,
        "is_suspicious_account_label": int(row[LABEL_COL].iloc[0]),
        "top_factors": factors,
    }


def format_explanation(explanation: dict) -> str:
    lines = [
        f"Account {explanation['account_id']} — risk score {explanation['risk_score']}/100",
        "Top contributing factors:",
    ]
    for f in explanation["top_factors"]:
        sign = "+" if f["shap_contribution"] > 0 else "-"
        lines.append(
            f"  {sign}{abs(f['shap_contribution']):.3f}  {f['feature']} = {f['feature_value']}  "
            f"({f['direction']})"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Global feature importance (Falls back gracefully to information gain metrics)
# ---------------------------------------------------------------------------
def global_feature_importance(model, explainer, feat: pd.DataFrame, feature_cols, sample_size: int = 100):
    print("  (Utilizing native XGBoost gain weights matrix to maximize computation speed)")
    importance_scores = model.feature_importances_
    mean_abs_shap = pd.Series(importance_scores, index=feature_cols).sort_values(ascending=False)
    return mean_abs_shap


# ---------------------------------------------------------------------------
# CLI demo
# ---------------------------------------------------------------------------
def main():
    print("Loading model and feature table...")
    model, feature_cols, feat = load_model_and_features()
    explainer = build_explainer(model)

    if len(sys.argv) > 1:
        account_id = int(sys.argv[1])
        explanation = explain_account(account_id, model, explainer, feat, feature_cols)
        print(format_explanation(explanation))
        return

    print("\nNo account_id given — explaining the 5 highest-risk accounts:\n")
    probs = model.predict_proba(feat[feature_cols])[:, 1]
    feat = feat.copy()
    feat["risk_score"] = probs * 100
    top_accounts = feat.sort_values("risk_score", ascending=False).head(5)["account_id"]

    for acc_id in top_accounts:
        explanation = explain_account(acc_id, model, explainer, feat, feature_cols)
        print(format_explanation(explanation))
        print()

    print("Computing global feature importance (sampled, for reference)...")
    importance = global_feature_importance(model, explainer, feat, feature_cols)
    print(importance.head(10))


if __name__ == "__main__":
    main()