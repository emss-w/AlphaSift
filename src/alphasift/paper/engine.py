from __future__ import annotations

from typing import Iterable
import pandas as pd

from alphasift.data.models import OHLCV_COLUMNS
from alphasift.paper.models import PaperAccountState, PaperFill, PaperTradingResult
from alphasift.strategies.base import Strategy


def run_paper_trader(
    candles: pd.DataFrame,
    strategy: Strategy,
    *,
    initial_cash: float = 10_000.0,
) -> PaperTradingResult:
    """
    Run minimal single-symbol long/flat paper trading.

    Timing model:
    - Strategy target for bar N is computed from completed candles through N.
    - A target change observed at bar N is executed at bar N+1 open.
    - Equity is marked at each completed bar close using post-fill holdings.
    """
    _validate_candles(candles)
    if initial_cash < 0.0:
        raise ValueError("initial_cash must be >= 0.")

    if candles.empty:
        empty_history = pd.DataFrame(
            columns=[
                "timestamp",
                "target_position",
                "cash",
                "units",
                "equity",
                "close",
            ]
        )
        return PaperTradingResult(
            account_states=[],
            account_history=empty_history,
            fills=[],
            initial_cash=float(initial_cash),
            ending_cash=float(initial_cash),
            ending_units=0.0,
            ending_equity=float(initial_cash),
        )

    targets = _coerce_target_positions(candles, strategy.generate_positions(candles))
    _validate_targets(targets)

    timestamps = candles["timestamp"].astype(int).reset_index(drop=True)
    opens = candles["open"].astype(float).reset_index(drop=True)
    closes = candles["close"].astype(float).reset_index(drop=True)

    cash = float(initial_cash)
    units = 0.0
    current_target = 0.0

    fills: list[PaperFill] = []
    account_states: list[PaperAccountState] = []

    for idx in range(len(candles)):
        timestamp = int(timestamps.iloc[idx])
        open_price = float(opens.iloc[idx])
        close_price = float(closes.iloc[idx])

        if idx > 0:
            desired_target = float(targets.iloc[idx - 1])
            if desired_target != current_target:
                if desired_target == 1.0:
                    if cash > 0.0:
                        quantity = cash / open_price
                        cash -= quantity * open_price
                        units += quantity
                        current_target = 1.0
                        fills.append(
                            PaperFill(
                                timestamp=timestamp,
                                side="buy",
                                fill_price=open_price,
                                quantity=quantity,
                                cash_after_fill=float(cash),
                                units_after_fill=float(units),
                                equity_after_fill=float(cash + units * close_price),
                            )
                        )
                else:
                    if units > 0.0:
                        quantity = units
                        cash += quantity * open_price
                        units = 0.0
                        current_target = 0.0
                        fills.append(
                            PaperFill(
                                timestamp=timestamp,
                                side="sell",
                                fill_price=open_price,
                                quantity=quantity,
                                cash_after_fill=float(cash),
                                units_after_fill=float(units),
                                equity_after_fill=float(cash + units * close_price),
                            )
                        )

        equity = float(cash + units * close_price)
        account_states.append(
            PaperAccountState(
                timestamp=timestamp,
                cash=float(cash),
                units=float(units),
                target_position=float(current_target),
                equity=equity,
            )
        )

    history = pd.DataFrame(
        {
            "timestamp": [state.timestamp for state in account_states],
            "target_position": [state.target_position for state in account_states],
            "cash": [state.cash for state in account_states],
            "units": [state.units for state in account_states],
            "equity": [state.equity for state in account_states],
            "close": closes.tolist(),
        }
    )
    ending_cash = float(history["cash"].iloc[-1])
    ending_units = float(history["units"].iloc[-1])
    ending_equity = float(history["equity"].iloc[-1])

    return PaperTradingResult(
        account_states=account_states,
        account_history=history,
        fills=fills,
        initial_cash=float(initial_cash),
        ending_cash=ending_cash,
        ending_units=ending_units,
        ending_equity=ending_equity,
    )


def _validate_candles(candles: pd.DataFrame) -> None:
    missing = set(OHLCV_COLUMNS) - set(candles.columns)
    if missing:
        raise ValueError(f"Missing required candle columns: {sorted(missing)}")
    timestamps = candles["timestamp"]
    if timestamps.empty:
        return
    if not timestamps.is_monotonic_increasing:
        raise ValueError("Candles must be sorted ascending by unique timestamp.")
    if not timestamps.is_unique:
        raise ValueError("Candles must have unique timestamp values.")


def _coerce_target_positions(
    candles: pd.DataFrame,
    target_positions: pd.Series | pd.DataFrame | Iterable[float],
) -> pd.Series:
    timestamps = candles["timestamp"].reset_index(drop=True)

    if isinstance(target_positions, pd.DataFrame):
        required = {"timestamp", "target_position"}
        if not required.issubset(target_positions.columns):
            raise ValueError(
                "Target position DataFrame must have timestamp and target_position columns."
            )
        series = (
            target_positions[["timestamp", "target_position"]]
            .set_index("timestamp")["target_position"]
            .reindex(timestamps)
        )
        if series.isna().any():
            raise ValueError("Target position timestamps do not align with candles.")
        return series.reset_index(drop=True)

    if isinstance(target_positions, pd.Series):
        series = target_positions.copy()
        if series.index.equals(timestamps):
            series = series.reindex(timestamps)
        elif len(series) == len(candles):
            series = series.reset_index(drop=True)
        else:
            raise ValueError("Target positions length does not match candles.")
        return series

    series = pd.Series(list(target_positions))
    if len(series) != len(candles):
        raise ValueError("Target positions length does not match candles.")
    return series.reset_index(drop=True)


def _validate_targets(targets: pd.Series) -> None:
    if targets.empty:
        return
    allowed = {0.0, 1.0, 0, 1}
    unique_values = set(targets.dropna().unique())
    if not unique_values.issubset(allowed):
        raise ValueError("Target positions must be 0.0 or 1.0 for long/flat mode.")
