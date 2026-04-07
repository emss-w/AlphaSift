from __future__ import annotations

import argparse

from alphasift.backtest.engine import run_backtest
from alphasift.config import Config
from alphasift.data.loaders import create_kraken_provider
from alphasift.strategies.buy_and_hold import BuyAndHoldStrategy
from alphasift.strategies.sma_cross import SimpleMovingAverageCrossStrategy


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a strategy backtest from cached OHLC data.")
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
    parser.add_argument("--fee-rate", type=float, default=0.0, help="Optional fee rate (e.g. 0.001)")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    config = Config.load()
    provider = create_kraken_provider(config)
    candles = provider.fetch_ohlc(args.pair, args.interval, use_cache=True)
    if candles.empty:
        print("No cached candles found for the requested pair/interval.")
        return

    if args.strategy == "buy_and_hold":
        strategy = BuyAndHoldStrategy()
    else:
        strategy = SimpleMovingAverageCrossStrategy(
            short_window=args.short_window,
            long_window=args.long_window,
        )

    positions = strategy.generate_positions(candles)
    result = run_backtest(candles, positions, fee_rate=args.fee_rate)

    summary = result.summary
    print("Backtest summary")
    print(f"Total return: {summary.total_return:.4f}")
    if summary.annualized_return is not None:
        print(f"Annualized return: {summary.annualized_return:.4f}")
    print(f"Max drawdown: {summary.max_drawdown:.4f}")
    print(f"Trades: {summary.trades}")


if __name__ == "__main__":
    main()
