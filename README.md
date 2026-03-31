# alphasift

Foundational data-access component for Kraken OHLC data. This repo intentionally contains only the base layer needed to fetch, normalize, and locally cache historical candles so future prompts can build backtesting and strategy layers cleanly.

**What this is**
- A minimal, modular data-access layer
- A normalized OHLCV schema with local caching
- A clean separation between HTTP client, provider logic, and IO

**What this is not**
- Backtesting engine
- Strategy code
- Live trading or websockets
- Databases or Docker

## Setup
1. Create and activate a virtual environment
2. Install dependencies
3. Copy `.env.example` to `.env` and set values if desired

## Environment Variables
```
KRAKEN_API_KEY=
KRAKEN_API_SECRET=
KRAKEN_BASE_URL=https://api.kraken.com
DEFAULT_DATA_DIR=./data
```
Public OHLC endpoints do not require auth, but the config supports future private endpoints.

## Project Structure
```
.
├── data/
│   ├── raw/
│   └── cache/
├── scripts/
│   └── fetch_kraken_ohlc.py
└── src/
    └── alphasift/
        ├── config.py
        ├── logging_config.py
        ├── utils/
        └── data/
            ├── base.py
            ├── models.py
            ├── cache.py
            ├── kraken_client.py
            ├── kraken_provider.py
            └── loaders.py
```

## Fetch Data
After installing, run:
```
python scripts/fetch_kraken_ohlc.py --pair BTC/USD --interval 60
```
This fetches Kraken OHLC data, normalizes to the schema:
`timestamp, open, high, low, close, volume, trades, vwap`
and caches it under `data/cache`.

## Why This Base Layer Exists
This project is intentionally scoped to a clean data-access layer so future prompts can add:
- A backtesting engine
- Strategy modules
- Parameter sweeps
- Paper trading

without refactoring the foundations.
