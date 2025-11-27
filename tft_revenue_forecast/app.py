from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

import math
from typing import Dict, Any

import torch
import pandas as pd
import numpy as np

from pytorch_forecasting import TemporalFusionTransformer, TimeSeriesDataSet
from pytorch_forecasting.data import GroupNormalizer
from sklearn.metrics import mean_absolute_error, mean_squared_error


# ============================================================
# 1. LOAD DATA + RECREATE TimeSeriesDataSet (same as training)
# ============================================================

CSV_PATH = "financial_dataset.csv"
CHECKPOINT_PATH = "tft-best.ckpt"

df = pd.read_csv(CSV_PATH)

if "Date" in df.columns:
    df["Date"] = pd.to_datetime(df["Date"])

df = df.sort_values(["Company_ID", "Year", "Quarter"]).reset_index(drop=True)

if "time_idx" not in df.columns:
    df["time_idx"] = df.groupby("Company_ID").cumcount()

max_encoder_length = 8
max_prediction_length = 1

target_col = "Target_Revenue_Next_Qtr"
ignore_cols = ["Date", "Target_Anomaly_Class"]

cont_cols = [
    c
    for c in df.columns
    if (
        c not in ["Company_ID", target_col, "time_idx"] + ignore_cols
        and np.issubdtype(df[c].dtype, np.number)
    )
]

training_cutoff = df["time_idx"].max() - 4

training = TimeSeriesDataSet(
    df[df.time_idx <= training_cutoff],
    time_idx="time_idx",
    target=target_col,
    group_ids=["Company_ID"],
    max_encoder_length=max_encoder_length,
    max_prediction_length=max_prediction_length,
    static_categoricals=["Company_ID"],
    static_reals=[],
    time_varying_known_categoricals=[],
    time_varying_known_reals=["Quarter"],
    time_varying_unknown_categoricals=[],
    time_varying_unknown_reals=cont_cols,
    target_normalizer=GroupNormalizer(groups=["Company_ID"], transformation="softplus"),
    add_relative_time_idx=True,
    add_target_scales=True,
    add_encoder_length=True,
)

device = "cuda" if torch.cuda.is_available() else "cpu"

tft: TemporalFusionTransformer = TemporalFusionTransformer.load_from_checkpoint(
    CHECKPOINT_PATH
)
tft.to(device)
tft.eval()


# ============================================================
# 2. REQUEST MODEL
# ============================================================

class TFTRequest(BaseModel):
    company_id: str


app = FastAPI(
    title="TFT Revenue Forecast API",
    version="0.1.0",
    description=(
        "Predict next-quarter revenues for the latest year using Temporal Fusion Transformer. "
        "Returns actual vs forecast plus MAE / RMSE."
    ),
)


@app.get("/")
def root() -> Dict[str, Any]:
    return {
        "message": "TFT Revenue Forecast API is running. Go to /docs for interactive docs.",
        "endpoints": ["/predict_tft"],
    }


# ============================================================
# 3. HELPER: BUILD PREDICTION DATASET
# ============================================================

def build_prediction_dataset_latest_year(company_id: str):
    company_df = df[df["Company_ID"] == company_id].copy()

    if company_df.empty:
        raise HTTPException(
            status_code=404,
            detail=f"No data found for company_id={company_id}",
        )

    latest_year = int(company_df["Year"].max())

    mask_year = company_df["Year"] == latest_year
    if not mask_year.any():
        raise HTTPException(
            status_code=400,
            detail=f"No rows for latest year={latest_year} for company_id={company_id}",
        )

    min_pred_idx = int(company_df.loc[mask_year, "time_idx"].min())

    pred_dataset = TimeSeriesDataSet.from_dataset(
        training,
        company_df,
        min_prediction_idx=min_pred_idx,
        stop_randomization=True,
    )

    future_rows = company_df[company_df["time_idx"] >= min_pred_idx].copy()

    return latest_year, pred_dataset, future_rows


# ============================================================
# 4. ENDPOINT
# ============================================================

@app.post("/predict_tft", summary="Predict future revenues for the latest year with TFT")
def predict_tft(req: TFTRequest):
    latest_year, pred_dataset, future_rows = build_prediction_dataset_latest_year(
        company_id=req.company_id
    )

    pred_loader = pred_dataset.to_dataloader(
        train=False,
        batch_size=64,
        num_workers=0,
    )

    with torch.no_grad():
        preds = tft.predict(pred_loader).cpu().numpy().ravel()

    n = min(len(preds), len(future_rows))
    preds = preds[:n]
    future_rows = future_rows.iloc[:n]

    dates = []
    for _, row in future_rows.iterrows():
        year = int(row["Year"])
        quarter = int(row["Quarter"])
        period = pd.Period(f"{year}Q{quarter}", freq="Q")
        dates.append(str(period.end_time))

    actual_values = future_rows[target_col].to_numpy(dtype=float)

    mask_valid = ~np.isnan(actual_values)
    actual_clean = actual_values[mask_valid]
    preds_clean = preds[mask_valid]

    if len(actual_clean) > 0:
        mae = float(mean_absolute_error(actual_clean, preds_clean))
        rmse = float(math.sqrt(mean_squared_error(actual_clean, preds_clean)))
    else:
        mae = None
        rmse = None

    results = {
        "Revenue": {
            "dates": dates,
            "actual": actual_values.tolist(),
            "forecast": preds.tolist(),
            "mae": mae,
            "rmse": rmse,
        }
    }

    return {
        "company_id": req.company_id,
        "latest_year": latest_year,
        "results": results,
    }
