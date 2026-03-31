from __future__ import annotations

import argparse

from alphasift.config import load_config
from alphasift.data.loaders import create_kraken_provider
from alphasift.logging_config import configure_logging
from alphasift.utils.time import to_utc_datetime


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch Kraken OHLC data.")
    parser.add_argument("--pair", required=True, help="Trading pair like BTC/USD")
    parser.add_argument("--interval", type=int, required=True, help="Interval in minutes")
    return parser.parse_args()


def main() -> None:
    configure_logging()
    args = parse_args()
    config = load_config()
    provider = create_kraken_provider(config)
    df = provider.fetch_ohlc(args.pair, args.interval, use_cache=True)
    if df.empty:
        print("No data returned.")
        return
    start = to_utc_datetime(int(df["timestamp"].iloc[0]))
    end = to_utc_datetime(int(df["timestamp"].iloc[-1]))
    print(
        f"Fetched {len(df)} rows for {args.pair} interval {args.interval}m. "
        f"Range: {start.isoformat()} -> {end.isoformat()}"
    )


if __name__ == "__main__":
    main()
