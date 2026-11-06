# Stock Volatility Regime Prediction

A machine-learning project that uses historical OHLCV market data to classify a stock's volatility regime. The repository includes the training notebook and a script for fetching recent market data for inference.

## Files
- `Stock_Volatility_Prediction.ipynb` — data preparation, feature engineering, model training, and evaluation.
- `stock_prices_combined.csv` — dataset bundled with the original project.
- `live_predict.py` — live-data prediction script.

## Setup
```bash
python -m venv .venv
# Activate the environment, then:
pip install -r requirements.txt
jupyter notebook
```

Run the notebook from top to bottom. It should generate the model/scaler/feature artifacts required by `live_predict.py`.

Then run:
```bash
python live_predict.py AAPL
```

## Important
The serialized model files (`.pkl`) are intentionally not included in this public starter repository. Regenerate them by running the notebook. Only load model artifacts you created or trust; Python pickle/joblib files can execute code during loading.

Market predictions are uncertain and are not financial advice. Include the notebook's evaluation metrics and limitations when describing this project.
