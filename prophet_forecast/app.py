from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import pandas as pd
from prophet import Prophet
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error

app = FastAPI(title="Financial Forecasting API")

df = pd.read_csv("financial_dataset.csv")
df["date"] = pd.PeriodIndex(year=df["Year"], quarter=df["Quarter"], freq="Q").to_timestamp(how="end")
df = df.sort_values("date")

class ForecastRequest(BaseModel):
    company_id: str

@app.post("/forecast")
def forecast_all(req: ForecastRequest):
    company_id = req.company_id
    df_company = df[df["Company_ID"] == company_id].copy()

    if df_company.empty:
        raise HTTPException(status_code=404, detail="Company not found")

    targets_config = {
        "Revenue": {
            "y_col": "Revenue",
            "regressors": ["Operating_Income", "Cash_Flow", "Net_Income"]
        },
        "Expenses": {
            "y_col": "Expenses",
            "regressors": ["Revenue", "Operating_Income"]
        },
        "Cash_Flow": {
            "y_col": "Cash_Flow",
            "regressors": ["Revenue", "Expenses", "Net_Income"]
        }
    }

    results = {}

    for target, cfg in targets_config.items():
        df_p = df_company[["date", cfg["y_col"]] + cfg["regressors"]].copy()
        df_p = df_p.rename(columns={"date": "ds", cfg["y_col"]: "y"})
        df_p[cfg["regressors"]] = df_p[cfg["regressors"]].ffill().bfill()

        train = df_p.iloc[:-4]
        test = df_p.iloc[-4:]

        model = Prophet(
            yearly_seasonality=True,
            seasonality_mode="multiplicative",
            changepoint_prior_scale=0.1
        )
        model.add_seasonality(name="quarterly", period=4, fourier_order=3)

        for r in cfg["regressors"]:
            model.add_regressor(r)

        model.fit(train)
        future = df_p[["ds"] + cfg["regressors"]].iloc[-4:]
        forecast = model.predict(future)

        pred = forecast["yhat"].values
        actual = test["y"].values
        dates = test["ds"].astype(str).values

        mae = mean_absolute_error(actual, pred)
        rmse = np.sqrt(mean_squared_error(actual, pred))

        results[target] = {
            "dates": dates.tolist(),
            "actual": actual.tolist(),
            "forecast": pred.tolist(),
            "mae": round(mae, 2),
            "rmse": round(rmse, 2)
        }

    return {
        "company_id": company_id,
        "results": results
    }
