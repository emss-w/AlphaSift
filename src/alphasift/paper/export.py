from __future__ import annotations

import csv
from pathlib import Path

from alphasift.paper.models import PaperTradingResult


def export_paper_trading_result_to_csv(
    result: PaperTradingResult,
    output_dir: str | Path,
    *,
    prefix: str = "paper_session",
    overwrite: bool = False,
) -> tuple[Path, Path]:
    """Export paper account history and fills to deterministic CSV files."""
    destination_dir = Path(output_dir)
    destination_dir.mkdir(parents=True, exist_ok=True)

    account_history_path = destination_dir / f"{prefix}_account_history.csv"
    fills_path = destination_dir / f"{prefix}_fills.csv"

    _assert_writable(account_history_path, overwrite=overwrite)
    _assert_writable(fills_path, overwrite=overwrite)

    _write_account_history_csv(result, account_history_path)
    _write_fills_csv(result, fills_path)
    return account_history_path, fills_path


def _assert_writable(path: Path, *, overwrite: bool) -> None:
    if path.exists() and not overwrite:
        raise FileExistsError(
            f"CSV output already exists at {path}. Set overwrite=True to replace it."
        )


def _write_account_history_csv(result: PaperTradingResult, output_path: Path) -> None:
    fieldnames = ["timestamp", "target_position", "cash", "units", "equity", "close"]

    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for _, row in result.account_history.iterrows():
            writer.writerow(
                {
                    "timestamp": int(row["timestamp"]),
                    "target_position": float(row["target_position"]),
                    "cash": float(row["cash"]),
                    "units": float(row["units"]),
                    "equity": float(row["equity"]),
                    "close": float(row["close"]),
                }
            )


def _write_fills_csv(result: PaperTradingResult, output_path: Path) -> None:
    fieldnames = [
        "timestamp",
        "side",
        "fill_price",
        "quantity",
        "cash_after_fill",
        "units_after_fill",
        "equity_after_fill",
    ]

    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for fill in result.fills:
            writer.writerow(
                {
                    "timestamp": fill.timestamp,
                    "side": fill.side,
                    "fill_price": fill.fill_price,
                    "quantity": fill.quantity,
                    "cash_after_fill": fill.cash_after_fill,
                    "units_after_fill": fill.units_after_fill,
                    "equity_after_fill": fill.equity_after_fill,
                }
            )
