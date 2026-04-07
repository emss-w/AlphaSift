# alphasift

Foundational data-access component for Kraken OHLC data, plus minimal strategy, backtest, experiment, and paper trading layers that operate on normalized candles.

**What this is**
- A minimal, modular data-access layer
- A normalized OHLCV schema with local caching
- A clean separation between HTTP client, provider logic, and IO
- A small long/flat backtest engine driven by target positions
- A minimal strategy layer for generating target positions
- A minimal single-symbol long/flat paper trading simulation layer
- A minimal local FastAPI service layer with SQLite metadata for frontend-facing orchestration

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
APP_DB_PATH=./data/app/metadata.sqlite3
ARTIFACTS_DIR=./data/artifacts
API_HOST=127.0.0.1
API_PORT=8000
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
|   |-- run_strategy_backtest.py
|   |-- run_sma_experiments.py
|   |-- run_paper_trader.py
|   `-- run_api.py
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
        |-- strategies/
        |   |-- base.py
        |   |-- buy_and_hold.py
        |   `-- sma_cross.py
        |-- experiments/
        |   |-- models.py
        |   |-- export.py
        |   `-- runner.py
        |-- paper/
        |   |-- models.py
        |   |-- export.py
        |   `-- engine.py
        `-- app/
            |-- api.py
            |-- schemas.py
            |-- services.py
            |-- jobs.py
            `-- db.py
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

## Run SMA Experiments
```
python scripts/run_sma_experiments.py --pair BTC/USD --interval 60 --short-min 5 --short-max 20 --long-min 30 --long-max 80 --step 5
python scripts/run_sma_experiments.py --pair BTC/USD --interval 60 --export-csv data/experiments/sma_results.csv
```
This runs a simple SMA cross parameter sweep and prints ranked results.
Optionally, `--export-csv` writes ranked results to CSV. Use `--overwrite-export` to replace an existing file.

## Run Minimal Paper Trading
```
python scripts/run_paper_trader.py --pair BTC/USD --interval 60 --strategy buy_and_hold --initial-cash 10000
python scripts/run_paper_trader.py --pair BTC/USD --interval 60 --strategy sma_cross --short-window 10 --long-window 30
python scripts/run_paper_trader.py --pair BTC/USD --interval 60 --strategy sma_cross --export-dir data/paper_sessions --export-prefix btcusd_60m
```
This runs a fake-cash long/flat simulation on completed candles. Target changes are executed on the next completed bar open.
Optionally, `--export-dir` writes account history and fills as deterministic CSV files. Use `--overwrite-export` to replace existing files.

## Run Local API
```
python scripts/run_api.py
```
This starts a local FastAPI service that exposes:
- health/system info,
- strategy listing,
- SMA experiment run creation and lookup,
- paper session creation and lookup,
- artifact metadata listing and lookup.

## Why This Base Layer Exists
This project is intentionally scoped as a clean, modular research foundation so future prompts can add:
- Broader result persistence
- Live execution components
- More data providers

without refactoring the foundations.
