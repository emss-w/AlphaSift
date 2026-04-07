from __future__ import annotations

import argparse
from pathlib import Path

from alphasift.config import Config
from alphasift.data.loaders import create_kraken_provider
from alphasift.experiments.export import export_experiment_results_to_csv
from alphasift.experiments.runner import run_sma_cross_experiments


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run SMA cross parameter sweep backtests.")
    parser.add_argument("--pair", required=True, help="Trading pair, e.g. BTC/USD")
    parser.add_argument("--interval", type=int, required=True, help="Candle interval in minutes")
    parser.add_argument("--short-min", type=int, default=5, help="Minimum short window")
    parser.add_argument("--short-max", type=int, default=20, help="Maximum short window (inclusive)")
    parser.add_argument("--long-min", type=int, default=30, help="Minimum long window")
    parser.add_argument("--long-max", type=int, default=80, help="Maximum long window (inclusive)")
    parser.add_argument("--step", type=int, default=5, help="Step size for window ranges")
    parser.add_argument("--top", type=int, default=5, help="Number of top results to display")
    parser.add_argument(
        "--sort-by",
        choices=["total_return", "annualized_return", "max_drawdown", "trades"],
        default="total_return",
        help="Metric to rank results by",
    )
    parser.add_argument("--fee-rate", type=float, default=0.0, help="Optional fee rate (e.g. 0.001)")
    parser.add_argument(
        "--export-csv",
        type=Path,
        default=None,
        help="Optional path to export ranked experiment results as CSV",
    )
    parser.add_argument(
        "--overwrite-export",
        action="store_true",
        help="Allow overwriting an existing CSV export file",
    )
    return parser.parse_args()


def _make_range(min_value: int, max_value: int, step: int) -> list[int]:
    if step <= 0:
        raise ValueError("step must be > 0")
    if max_value < min_value:
        raise ValueError("max must be >= min")
    return list(range(min_value, max_value + 1, step))


def main() -> None:
    args = _parse_args()
    config = Config.load()
    provider = create_kraken_provider(config)
    candles = provider.fetch_ohlc(args.pair, args.interval, use_cache=True)
    if candles.empty:
        print("No cached candles found for the requested pair/interval.")
        return

    short_windows = _make_range(args.short_min, args.short_max, args.step)
    long_windows = _make_range(args.long_min, args.long_max, args.step)

    experiment = run_sma_cross_experiments(
        candles,
        short_windows,
        long_windows,
        sort_by=args.sort_by,
        fee_rate=args.fee_rate,
    )

    print("SMA cross experiment results")
    print(f"Skipped invalid combos: {len(experiment.skipped_parameters)}")
    print("Top results:")
    for result in experiment.results[: args.top]:
        params = result.parameters
        print(
            f"short={params['short_window']} long={params['long_window']} "
            f"total_return={result.total_return:.4f} "
            f"max_drawdown={result.max_drawdown:.4f} "
            f"trades={result.trades}"
        )

    best = experiment.results[0]
    best_params = best.parameters
    print("Best parameters")
    print(
        f"short={best_params['short_window']} long={best_params['long_window']} "
        f"total_return={best.total_return:.4f}"
    )

    if args.export_csv is not None:
        output = export_experiment_results_to_csv(
            experiment.results,
            args.export_csv,
            overwrite=args.overwrite_export,
        )
        print(f"Exported experiment results to {output}")


if __name__ == "__main__":
    main()
