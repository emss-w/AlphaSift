# alphasift

Foundational data-access component for Kraken OHLC data, plus a minimal strategy layer and backtest engine that operate on cached normalized candles.

**What this is**
- A minimal, modular data-access layer
- A normalized OHLCV schema with local caching
- A clean separation between HTTP client, provider logic, and IO
- A small long/flat backtest engine driven by target positions
- A minimal strategy layer for generating target positions

**What this is not**
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
|-- data/
|   |-- raw/
|   `-- cache/
|-- scripts/
|   |-- fetch_kraken_ohlc.py
|   |-- run_backtest.py
|   `-- run_strategy_backtest.py
`-- src/
    `-- alphasift/
        |-- config.py
        |-- logging_config.py
        |-- utils/
        |-- data/
        |   |-- base.py
        |   |-- models.py
        |   |-- cache.py
        |   |-- kraken_client.py
        |   |-- kraken_provider.py
        |   `-- loaders.py
        |-- backtest/
        |   |-- engine.py
        |   |-- metrics.py
        |   `-- models.py
        `-- strategies/
            |-- base.py
            |-- buy_and_hold.py
            `-- sma_cross.py
```

## Fetch Data
After installing, run:
```
python scripts/fetch_kraken_ohlc.py --pair BTC/USD --interval 60
```
This fetches Kraken OHLC data, normalizes to the schema:
`timestamp, open, high, low, close, volume, trades, vwap`
and caches it under `data/cache`.

## Run Minimal Backtest
```
python scripts/run_backtest.py --pair BTC/USD --interval 60
```
This uses cached data and runs a basic long/flat backtest with a buy-and-hold target position.

## Run Strategy Backtest
```
python scripts/run_strategy_backtest.py --pair BTC/USD --interval 60 --strategy buy_and_hold
python scripts/run_strategy_backtest.py --pair BTC/USD --interval 60 --strategy sma_cross --short-window 10 --long-window 30
```
This loads cached data, generates target positions from the chosen strategy, and runs the backtest engine.

## Why This Base Layer Exists
This project is intentionally scoped to a clean data-access layer so future prompts can add:
- Strategy modules
- Parameter sweeps
- Paper trading

without refactoring the foundations.
