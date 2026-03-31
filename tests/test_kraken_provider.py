from alphasift.data.kraken_provider import KrakenOHLCProvider
from pathlib import Path


class DummyClient:
    def __init__(self, payload):
        self.payload = payload

    def get_ohlc(self, pair, interval):
        return self.payload


def test_normalization_dedup_sort_drop_incomplete():
    payload = {
        "error": [],
        "result": {
            "XXBTZUSD": [
                [1700000600, "2", "3", "1", "2.5", "2.2", "12", 10],
                [1700000000, "1", "2", "0.5", "1.5", "1.2", "10", 8],
                [1700000000, "1", "2", "0.5", "1.5", "1.2", "10", 8],
                [1700001200, "3", "4", "2", "3.5", "3.2", "14", 11],
            ],
            "last": 1700001800,
        },
    }
    cache_dir = Path("data/cache/test-cache")
    provider = KrakenOHLCProvider(DummyClient(payload), cache_dir=cache_dir)
    df = provider.fetch_ohlc("BTC/USD", 60, use_cache=False)

    assert list(df.columns) == [
        "timestamp",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "trades",
        "vwap",
    ]
    # duplicates removed and sorted ascending
    assert df["timestamp"].tolist() == [1700000000, 1700000600]
    # last row excluded as incomplete
    assert 1700001200 not in df["timestamp"].tolist()
    assert df.dtypes["timestamp"] == "int64"
    assert df.dtypes["open"] == "float64"
    assert df.dtypes["trades"] == "int64"
    cache_file = cache_dir / "kraken_BTC-USD_60.csv"
    if cache_file.exists():
        cache_file.unlink()
    if cache_dir.exists():
        cache_dir.rmdir()
