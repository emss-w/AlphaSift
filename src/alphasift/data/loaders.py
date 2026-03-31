from __future__ import annotations

from alphasift.config import Config
from alphasift.data.kraken_client import KrakenClient, KrakenClientConfig
from alphasift.data.kraken_provider import KrakenOHLCProvider


def create_kraken_provider(config: Config) -> KrakenOHLCProvider:
    client = KrakenClient(
        KrakenClientConfig(
            base_url=config.kraken_base_url,
            api_key=config.kraken_api_key,
            api_secret=config.kraken_api_secret,
        )
    )
    cache_dir = config.default_data_dir / "cache"
    return KrakenOHLCProvider(client=client, cache_dir=cache_dir)
