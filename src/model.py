"""
model.py
Track 4 — Risk Scoring & Prioritization
AI/ML Intelligence Hackathon, June 2026

Builds account-level risk features from transaction + KYC data, trains an
XGBoost classifier with SMOTE oversampling to handle the severe class
imbalance (~0.49% suspicious accounts), evaluates using precision@K (the
right metric for a "rank then investigate top N" workflow), and produces
a 0-100 risk score + ranked priority list for every account.

NOTE: account-level feature engineering normally belongs in
feature_engineering.py (iteration 2). It's included here inline so this
file is immediately runnable end-to-end; extract build_account_features()
into its own module later if graph_features.py / explainer.py should reuse it.

Run from src/:  python model.py
"""

import json
import os

import numpy as np
import pandas as pd
import xgboost as xgb
from imblearn.over_sampling import SMOTE
from sklearn.metrics import (
    average_precision_score,
    classification_report,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split

RANDOM_STATE = 42

DATA_DIR = "../data"
MODEL_DIR = "../models"
OUTPUT_DIR = "../outputs"

CATEGORICAL_COLS = ["institution", "acct_type", "risk_grade", "city"]
ID_COLS = ["account_id"]
LABEL_COL = "is_suspicious_account"

# Precision@K thresholds — relevant scale for an analyst triage queue
K_VALUES = [10, 25, 50, 100, 200, 300]


# ---------------------------------------------------------------------------
# 1. Load data
# ---------------------------------------------------------------------------
def load_data(data_dir: str = DATA_DIR):
    ml = pd.read_csv(os.path.join(data_dir, "ml_features.csv"))
    accounts = pd.read_csv(os.path.join(data_dir, "accounts.csv"))
    return ml, accounts


# ---------------------------------------------------------------------------
# 2. Account-level feature engineering
# ---------------------------------------------------------------------------
def build_account_features(ml: pd.DataFrame, accounts: pd.DataFrame) -> pd.DataFrame:
    """Aggregate transaction-level rows to one row per account, merge KYC,
    and compute the account-level suspicious label.

    Label definition: an account is labelled suspicious (1) if it appears
    as sender OR receiver in at least one transaction flagged
    is_suspicious_tx == 1. This captures risk exposure on both sides of the
    money flow, not just origination. (336 suspicious tx -> 319 unique
    accounts touched -> ~0.49% positive rate at account level.)

    IMPORTANT: is_suspicious_tx itself is NEVER aggregated into the feature
    set below — only used (separately, further down) to build the label.
    Aggregating it into a feature like "suspicious_tx_count" would leak the
    label directly into X and produce a trivially perfect, useless model.
    """
    sender_agg = ml.groupby("Sender_account").agg(
        sent_tx_count=("amount_local_npr", "count"),
        sent_total_amount=("amount_local_npr", "sum"),
        sent_avg_amount=("amount_local_npr", "mean"),
        sent_max_amount=("amount_local_npr", "max"),
        sent_std_amount=("amount_local_npr", "std"),
        sent_avg_zscore=("amount_zscore", "mean"),
        sent_cross_border_ratio=("cross_border_flag", "mean"),
        sent_currency_mismatch_ratio=("currency_mismatch", "mean"),
        sent_avg_country_risk=("sender_country_risk", "mean"),
        sent_avg_velocity=("velocity_sum_10tx", "mean"),
        sent_max_velocity=("velocity_sum_10tx", "max"),
        sent_unique_receivers=("Receiver_account", "nunique"),
        sent_weekend_ratio=("is_weekend", "mean"),
        sent_above_1M_count=("above_1M_NPR", "sum"),
        sent_above_10M_count=("above_10M_NPR", "sum"),
    ).reset_index().rename(columns={"Sender_account": "account_id"})

    receiver_agg = ml.groupby("Receiver_account").agg(
        recv_tx_count=("amount_local_npr", "count"),
        recv_total_amount=("amount_local_npr", "sum"),
        recv_avg_amount=("amount_local_npr", "mean"),
        recv_max_amount=("amount_local_npr", "max"),
        recv_avg_zscore=("amount_zscore", "mean"),
        recv_cross_border_ratio=("cross_border_flag", "mean"),
        recv_currency_mismatch_ratio=("currency_mismatch", "mean"),
        recv_avg_country_risk=("receiver_country_risk", "mean"),
        recv_unique_senders=("Sender_account", "nunique"),
        recv_above_1M_count=("above_1M_NPR", "sum"),
        recv_above_10M_count=("above_10M_NPR", "sum"),
    ).reset_index().rename(columns={"Receiver_account": "account_id"})

    # Label source — computed independently from the features above, never
    # merged into X. Built from the raw transaction rows directly.
    sender_label = (
        ml.groupby("Sender_account")["is_suspicious_tx"].sum()
        .rename("sent_suspicious_count").reset_index()
        .rename(columns={"Sender_account": "account_id"})
    )
    receiver_label = (
        ml.groupby("Receiver_account")["is_suspicious_tx"].sum()
        .rename("recv_suspicious_count").reset_index()
        .rename(columns={"Receiver_account": "account_id"})
    )

    # Start from the full KYC roster so every known account gets scored,
    # even one with zero observed transactions in this snapshot.
    feat = accounts[["account_id"]].copy()
    feat = feat.merge(sender_agg, on="account_id", how="left")
    feat = feat.merge(receiver_agg, on="account_id", how="left")

    num_cols = [c for c in feat.columns if c != "account_id"]
    feat[num_cols] = feat[num_cols].fillna(0)

    feat["total_tx_count"] = feat["sent_tx_count"] + feat["recv_tx_count"]
    feat["total_volume"] = feat["sent_total_amount"] + feat["recv_total_amount"]
    feat["net_flow"] = feat["recv_total_amount"] - feat["sent_total_amount"]
    feat["total_unique_counterparties"] = feat["sent_unique_receivers"] + feat["recv_unique_senders"]

    kyc = accounts.copy()
    kyc["is_person"] = kyc["is_person"].astype(int)
    kyc["pep_flag"] = kyc["pep_flag"].astype(int)
    kyc["sanctions_hit"] = kyc["sanctions_hit"].astype(int)
    kyc["opened"] = pd.to_datetime(kyc["opened"])
    reference_date = pd.to_datetime(ml["Date"]).max()
    kyc["account_age_days"] = (reference_date - kyc["opened"]).dt.days

    kyc_cols = ID_COLS + CATEGORICAL_COLS + ["is_person", "pep_flag", "sanctions_hit", "account_age_days"]
    feat = feat.merge(kyc[kyc_cols], on="account_id", how="left")

    feat = pd.get_dummies(feat, columns=CATEGORICAL_COLS, dummy_na=False)

    # Merge label sources into a lookup that never touches feat's columns —
    # they only exist to build the label and must not leak into X.
    label_lookup = pd.DataFrame({"account_id": feat["account_id"]})
    label_lookup = label_lookup.merge(sender_label, on="account_id", how="left")
    label_lookup = label_lookup.merge(receiver_label, on="account_id", how="left")
    label_lookup[["sent_suspicious_count", "recv_suspicious_count"]] = \
        label_lookup[["sent_suspicious_count", "recv_suspicious_count"]].fillna(0)
    total_suspicious_count = (
        label_lookup["sent_suspicious_count"] + label_lookup["recv_suspicious_count"]
    )

    feat[LABEL_COL] = (total_suspicious_count > 0).astype(int)

    return feat


# ---------------------------------------------------------------------------
# 3. Train / test split
# ---------------------------------------------------------------------------
def split_features(feat: pd.DataFrame):
    feature_cols = [c for c in feat.columns if c not in ID_COLS + [LABEL_COL]]
    X = feat[feature_cols]
    y = feat[LABEL_COL]
    account_ids = feat["account_id"]

    X_train, X_test, y_train, y_test, ids_train, ids_test = train_test_split(
        X, y, account_ids,
        test_size=0.25, stratify=y, random_state=RANDOM_STATE,
    )
    return X_train, X_test, y_train, y_test, ids_test, feature_cols


# ---------------------------------------------------------------------------
# 4. SMOTE + XGBoost training
# ---------------------------------------------------------------------------
def train_xgb(X_train, y_train):
    smote = SMOTE(random_state=RANDOM_STATE, k_neighbors=5)
    X_res, y_res = smote.fit_resample(X_train, y_train)

    model = xgb.XGBClassifier(
        n_estimators=300,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        eval_metric="aucpr",
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )
    model.fit(X_res, y_res)
    return model


# ---------------------------------------------------------------------------
# 5. Evaluation — precision@K is the primary metric for a ranked triage list
# ---------------------------------------------------------------------------
def precision_at_k(y_true: pd.Series, y_scores: np.ndarray, k: int) -> float:
    order = np.argsort(y_scores)[::-1][:k]
    return y_true.values[order].sum() / k


def evaluate(model, X_test, y_test):
    probs = model.predict_proba(X_test)[:, 1]
    preds = (probs >= 0.5).astype(int)

    print("=== Held-out test evaluation ===")
    print(f"ROC-AUC      : {roc_auc_score(y_test, probs):.4f}")
    print(f"PR-AUC (AP)  : {average_precision_score(y_test, probs):.4f}")
    print()
    print("Precision@K (K = top-ranked accounts by predicted risk score):")
    for k in K_VALUES:
        if k <= len(y_test):
            p = precision_at_k(y_test, probs, k)
            print(f"  precision@{k:<4}: {p:.3f}  ({int(round(p * k))}/{k} true positives)")
    print()
    print("Classification report @ 0.5 threshold (informational only —")
    print("precision@K matters more than a fixed threshold for this use case):")
    print(classification_report(y_test, preds, digits=3))
    return probs


# ---------------------------------------------------------------------------
# 6. Score every account + save ranked output
# ---------------------------------------------------------------------------
def score_all_accounts(model, feat: pd.DataFrame, feature_cols):
    X_full = feat[feature_cols]
    probs = model.predict_proba(X_full)[:, 1]

    result = feat[["account_id", LABEL_COL]].copy()
    result["risk_score"] = (probs * 100).round(2)
    result = result.sort_values("risk_score", ascending=False).reset_index(drop=True)
    result["rank"] = result.index + 1
    return result


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main():
    os.makedirs(MODEL_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("Loading data...")
    ml, accounts = load_data()

    print("Building account-level features...")
    feat = build_account_features(ml, accounts)
    print(f"Account feature table: {feat.shape[0]} accounts, {feat.shape[1]} columns")
    print(f"Suspicious accounts: {feat[LABEL_COL].sum()} ({feat[LABEL_COL].mean() * 100:.3f}%)")

    print("\nSplitting train/test and training evaluation model...")
    X_train, X_test, y_train, y_test, ids_test, feature_cols = split_features(feat)
    eval_model = train_xgb(X_train, y_train)
    evaluate(eval_model, X_test, y_test)

    print("\nTraining final production model on full dataset...")
    X_full = feat[feature_cols]
    y_full = feat[LABEL_COL]
    smote = SMOTE(random_state=RANDOM_STATE, k_neighbors=5)
    X_full_res, y_full_res = smote.fit_resample(X_full, y_full)
    production_model = xgb.XGBClassifier(
        n_estimators=300, max_depth=5, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.8, eval_metric="aucpr",
        random_state=RANDOM_STATE, n_jobs=-1,
    )
    production_model.fit(X_full_res, y_full_res)

    print("Scoring all accounts and saving ranked output...")
    ranked = score_all_accounts(production_model, feat, feature_cols)
    ranked.to_csv(os.path.join(OUTPUT_DIR, "account_risk_scores.csv"), index=False)
    print(ranked.head(10).to_string(index=False))

    production_model.save_model(os.path.join(MODEL_DIR, "xgb_risk_model.json"))
    with open(os.path.join(MODEL_DIR, "feature_columns.json"), "w") as f:
        json.dump(feature_cols, f)

    print(f"\nSaved model to {MODEL_DIR}/xgb_risk_model.json")
    print(f"Saved feature columns to {MODEL_DIR}/feature_columns.json")
    print(f"Saved ranked risk scores to {OUTPUT_DIR}/account_risk_scores.csv")


if __name__ == "__main__":
    main()