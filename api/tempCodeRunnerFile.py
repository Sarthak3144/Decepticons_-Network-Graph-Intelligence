    
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