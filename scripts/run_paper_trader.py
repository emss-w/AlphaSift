from __future__ import annotations

import argparse
from pathlib import Path

from alphasift.config import load_config
from alphasift.data.loaders import create_kraken_provider
from alphasift.paper.engine import run_paper_trader
from alphasift.paper.export import export_paper_trading_result_to_csv
from alphasift.strategies.buy_and_hold import BuyAndHoldStrategy
from alphasift.strategies.sma_cross import SimpleMovingAverageCrossStrategy


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run minimal single-symbol paper trading.")
    parser.add_argument("--pair", required=True, help="Trading pair, e.g. BTC/USD")
    parser.add_argument("--interval", type=int, required=True, help="Candle interval in minutes")
    parser.add_argument(
        "--strategy",
        choices=["buy_and_hold", "sma_cross"],
        required=True,
        help="Strategy to run",
    )
    parser.add_argument("--short-window", type=int, default=10, help="SMA short window")
    parser.add_argument("--long-window", type=int, default=30, help="SMA long window")
    parser.add_argument("--initial-cash", type=float, default=10_000.0, help="Starting fake cash")
    parser.add_argument(
        "--export-dir",
        type=Path,
        default=None,
        help="Optional output directory for account/fill CSV exports",
    )
    parser.add_argument(
        "--export-prefix",
        type=str,
        default="paper_session",
        help="CSV filename prefix when exporting paper session outputs",
    )
    parser.add_argument(
        "--overwrite-export",
        action="store_true",
        help="Allow overwriting existing paper-session CSV files",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Refresh candles from provider instead of using only cache",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    config = load_config()
    provider = create_kraken_provider(config)
    candles = provider.fetch_ohlc(args.pair, args.interval, use_cache=not args.refresh)
    if candles.empty:
        print("No completed candles found for the requested pair/interval.")
        return

    if args.strategy == "buy_and_hold":
        strategy = BuyAndHoldStrategy()
    else:
        strategy = SimpleMovingAverageCrossStrategy(
            short_window=args.short_window,
            long_window=args.long_window,
        )

    result = run_paper_trader(candles, strategy, initial_cash=args.initial_cash)
    current_position = 1.0 if result.ending_units > 0.0 else 0.0

    print("Paper trading summary")
    print(f"Starting cash: {result.initial_cash:.2f}")
    print(f"Ending equity: {result.ending_equity:.2f}")
    print(f"Fills: {len(result.fills)}")
    print(
        f"Current position: target={current_position:.1f} "
        f"units={result.ending_units:.8f} cash={result.ending_cash:.2f}"
    )

    if args.export_dir is not None:
        account_history_path, fills_path = export_paper_trading_result_to_csv(
            result,
            args.export_dir,
            prefix=args.export_prefix,
            overwrite=args.overwrite_export,
        )
        print(f"Exported account history CSV: {account_history_path}")
        print(f"Exported fills CSV: {fills_path}")


if __name__ == "__main__":
    main()
