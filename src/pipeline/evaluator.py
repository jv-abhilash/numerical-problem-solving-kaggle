# utils/mcq_eval.py
import pandas as pd
import numpy as np

def _to_opt_idx(x):
    try:
        v = int(float(x))
        return v if 0 <= v <= 4 else -1
    except Exception:
        return -1

def evaluate(key_path: str,
             pred_path: str,
             topic_col: str = "class_type",
             out_dir: str = "/kaggle/working") -> dict:
    key  = pd.read_csv(key_path)
    pred = pd.read_csv(pred_path)

    for fn, df, cols in [
        ("answer_key.csv", key,  ["qid", "option_index"]),
        ("model_preds.csv", pred, ["qid", "option_index"]),
    ]:
        miss = [c for c in cols if c not in df.columns]
        if miss: raise ValueError(f"{fn} missing cols: {miss}")

    key["option_index"]  = key["option_index"].apply(_to_opt_idx)
    pred["option_index"] = pred["option_index"].apply(_to_opt_idx)

    keep_cols = ["qid", "option_index"]
    if topic_col in key.columns: keep_cols.append(topic_col)

    m = key[keep_cols].merge(pred[["qid","option_index"]].rename(columns={"option_index":"pred_option_index"}),
                             on="qid", how="inner")
    if m.empty: raise ValueError("No overlapping qid between files.")

    m["valid_key"]  = m["option_index"].between(0,4)
    m["valid_pred"] = m["pred_option_index"].between(0,4)
    m["correct"]    = (m["option_index"] == m["pred_option_index"])

    # accuracy including all rows
    n_all = len(m); n_corr_all = int(m["correct"].sum())
    acc_all = n_corr_all / n_all if n_all else float("nan")

    # accuracy excluding any out-of-bound rows
    mv = m[m["valid_key"] & m["valid_pred"]]
    n_v = len(mv); n_corr_v = int(mv["correct"].sum())
    acc_v = n_corr_v / n_v if n_v else float("nan")

    cats = pd.CategoricalDtype(categories=[0,1,2,3,4], ordered=True)
    cm_all = pd.crosstab(m["option_index"].astype(cats),  m["pred_option_index"].astype(cats))
    cm_val = pd.crosstab(mv["option_index"].astype(cats), mv["pred_option_index"].astype(cats))

    mm_cols = ["qid","option_index","pred_option_index"] + ([topic_col] if topic_col in m.columns else [])
    out_mm = f"{out_dir.rstrip('/')}/model_preds_mismatches.csv"
    try: mv[~mv["correct"]][mm_cols].to_csv(out_mm, index=False)
    except: pass

    summary = {
        "n_compared_all": n_all, "n_correct_all": n_corr_all,
        "accuracy_all": round(acc_all,6),
        "n_valid_pairs": n_v, "n_correct_valid_only": n_corr_v,
        "accuracy_valid_only": round(acc_v,6) if n_v else None,
        "n_invalid_rows": int(len(m) - len(mv))
    }
    return {"summary": summary, "confusion_all": cm_all, "confusion_valid": cm_val, "merged": m, "merged_valid": mv}