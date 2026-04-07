import csv
import shutil
import uuid
from pathlib import Path

import pandas as pd
import pytest

from alphasift.paper.engine import run_paper_trader
from alphasift.paper.export import export_paper_trading_result_to_csv
from alphasift.strategies.buy_and_hold import BuyAndHoldStrategy


def _make_candles(timestamps, closes):
    return {
        "timestamp": timestamps,
        "open": closes,
        "high": closes,
        "low": closes,
        "close": closes,
        "volume": [1.0] * len(closes),
        "trades": [1] * len(closes),
        "vwap": closes,
    }


def _make_workspace_temp_dir() -> Path:
    base = Path("tests/.tmp_exports")
    temp_dir = base / uuid.uuid4().hex
    temp_dir.mkdir(parents=True, exist_ok=False)
    return temp_dir


def _read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames is not None
        return reader.fieldnames, list(reader)


def test_export_paper_result_writes_expected_files_and_columns():
    temp_dir = _make_workspace_temp_dir()
    try:
        candles = pd.DataFrame(_make_candles([1, 2, 3, 4], [100.0, 110.0, 120.0, 130.0]))
        result = run_paper_trader(candles, BuyAndHoldStrategy(), initial_cash=1_000.0)

        account_path, fills_path = export_paper_trading_result_to_csv(
            result,
            temp_dir / "exports",
            prefix="session_a",
        )

        assert account_path.exists()
        assert fills_path.exists()
        assert account_path.name == "session_a_account_history.csv"
        assert fills_path.name == "session_a_fills.csv"

        account_header, account_rows = _read_csv(account_path)
        fills_header, fills_rows = _read_csv(fills_path)

        assert account_header == ["timestamp", "target_position", "cash", "units", "equity", "close"]
        assert fills_header == [
            "timestamp",
            "side",
            "fill_price",
            "quantity",
            "cash_after_fill",
            "units_after_fill",
            "equity_after_fill",
        ]
        assert len(account_rows) == len(candles)
        assert len(fills_rows) == 1
        assert fills_rows[0]["side"] == "buy"
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_export_paper_result_is_deterministic():
    temp_dir = _make_workspace_temp_dir()
    try:
        candles = pd.DataFrame(_make_candles([1, 2, 3, 4], [100.0, 101.0, 102.0, 103.0]))
        result = run_paper_trader(candles, BuyAndHoldStrategy(), initial_cash=1_000.0)

        a1, f1 = export_paper_trading_result_to_csv(result, temp_dir / "a", prefix="session")
        a2, f2 = export_paper_trading_result_to_csv(result, temp_dir / "b", prefix="session")

        assert a1.read_text(encoding="utf-8") == a2.read_text(encoding="utf-8")
        assert f1.read_text(encoding="utf-8") == f2.read_text(encoding="utf-8")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_export_paper_result_does_not_overwrite_without_flag():
    temp_dir = _make_workspace_temp_dir()
    try:
        candles = pd.DataFrame(_make_candles([1, 2, 3], [100.0, 101.0, 102.0]))
        result = run_paper_trader(candles, BuyAndHoldStrategy(), initial_cash=1_000.0)

        export_paper_trading_result_to_csv(result, temp_dir, prefix="session")
        with pytest.raises(FileExistsError, match="already exists"):
            export_paper_trading_result_to_csv(result, temp_dir, prefix="session")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
