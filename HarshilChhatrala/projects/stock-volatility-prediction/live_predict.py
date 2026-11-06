"""
Live Stock Volatility Regime Predictor
========================================
Run this script on YOUR OWN machine (not in the training notebook's environment).
It fetches today's live/recent price data for a chosen ticker via yfinance,
computes the same features used during training, and applies the trained
model to predict whether the stock is heading into a HIGH or LOW volatility
regime over the next 10 trading days.

SETUP (one-time):
    pip install yfinance scikit-learn pandas joblib numpy

USAGE:
    python live_predict.py AAPL
    python live_predict.py TSLA
    python live_predict.py            # defaults to NVDA if no ticker given

REQUIRED FILES (must be in the same folder as this script):
    - volatility_model.pkl
    - volatility_scaler.pkl
    - feature_columns.pkl
(These were produced by the training notebook, Stock_Volatility_Prediction.ipynb)
"""

import sys
import numpy as np
import pandas as pd
import joblib

def get_ticker():
    if len(sys.argv) > 1:
        return sys.argv[1].upper()
    return "NVDA"

def fetch_live_data(ticker, period="6mo"):
    """Pull recent daily price data live from Yahoo Finance."""
    try:
        import yfinance as yf
    except ImportError:
        print("ERROR: yfinance is not installed. Run: pip install yfinance")
        sys.exit(1)

    print(f"Fetching live data for {ticker} from Yahoo Finance...")
    data = yf.download(ticker, period=period, progress=False)

    if data.empty:
        print(f"ERROR: No data returned for ticker '{ticker}'. Check the symbol and try again.")
        sys.exit(1)

    # yfinance sometimes returns MultiIndex columns (newer versions) — flatten if so
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    data = data.reset_index()
    data.columns = [c.lower() for c in data.columns]
    data = data.rename(columns={"adj close": "adj_close"})
    print(f"Fetched {len(data)} rows. Most recent date: {data['date'].max().date()}")
    return data

def engineer_features(data):
    """Recreate the exact same features used during training."""
    g = data.sort_values("date").copy()

    g["return"] = g["close"].pct_change()
    g["vol_10d"] = g["return"].rolling(10).std()
    g["vol_30d"] = g["return"].rolling(30).std()
    g["vol_ratio"] = g["vol_10d"] / g["vol_30d"]
    g["volume_chg"] = g["volume"].pct_change()
    g["volume_ma_ratio"] = g["volume"] / g["volume"].rolling(20).mean()
    g["price_range"] = (g["high"] - g["low"]) / g["close"]
    g["momentum_10d"] = g["close"].pct_change(10)
    g["momentum_20d"] = g["close"].pct_change(20)
    g["ma5_ma20_ratio"] = g["close"].rolling(5).mean() / g["close"].rolling(20).mean()
    g["vol_10d_lag1"] = g["vol_10d"].shift(1)
    g["vol_10d_lag2"] = g["vol_10d"].shift(2)

    g = g.replace([np.inf, -np.inf], np.nan)
    return g

def main():
    ticker = get_ticker()
    data = fetch_live_data(ticker)
    features_df = engineer_features(data)

    # Load the trained model, scaler, and expected feature order
    try:
        model = joblib.load("volatility_model.pkl")
        scaler = joblib.load("volatility_scaler.pkl")
        feature_cols = joblib.load("feature_columns.pkl")
    except FileNotFoundError:
        print("ERROR: Could not find volatility_model.pkl / volatility_scaler.pkl / feature_columns.pkl")
        print("Make sure these files (produced by the training notebook) are in the same folder as this script.")
        sys.exit(1)

    latest_row = features_df.iloc[-1:]

    if latest_row[feature_cols].isnull().any(axis=1).values[0]:
        print("\nWARNING: Not enough historical data yet to compute all features reliably")
        print("(this can happen for newly listed tickers). Try a longer period or a different ticker.\n")

    X_live = latest_row[feature_cols].fillna(0)
    X_live_scaled = scaler.transform(X_live)

    prediction = model.predict(X_live_scaled)[0]
    proba = model.predict_proba(X_live_scaled)[0]

    regime = "HIGH VOLATILITY" if prediction == 1 else "LOW VOLATILITY"
    confidence = proba[prediction] * 100

    print("\n" + "=" * 50)
    print(f"  LIVE PREDICTION FOR {ticker}")
    print("=" * 50)
    print(f"  As of:          {latest_row['date'].values[0]}")
    print(f"  Last close:     ${latest_row['close'].values[0]:.2f}")
    print(f"  Current 10d volatility: {latest_row['vol_10d'].values[0]:.4f}")
    print(f"  Predicted regime (next 10 trading days): {regime}")
    print(f"  Model confidence: {confidence:.1f}%")
    print("=" * 50)
    print("\nReminder: this model's honest test accuracy is ~63-65% (see the")
    print("training notebook's Section 9 for why raw price/volatility prediction")
    print("is inherently hard, and what this accuracy level does and doesn't mean).")

if __name__ == "__main__":
    main()
