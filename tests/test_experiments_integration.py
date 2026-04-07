import pandas as pd
import shutil
import uuid
from pathlib import Path

from alphasift.experiments.export import export_experiment_results_to_csv
from alphasift.experiments.runner import run_sma_cross_experiments


def _make_candles(timestamps, closes):
    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "open": closes,
            "high": closes,
            "low": closes,
            "close": closes,
            "volume": [1.0] * len(closes),
            "trades": [1] * len(closes),
            "vwap": closes,
        }
    )


def _make_workspace_temp_dir() -> Path:
    base = Path("tests/.tmp_exports")
    temp_dir = base / uuid.uuid4().hex
    temp_dir.mkdir(parents=True, exist_ok=False)
    return temp_dir


def test_experiment_integration_trend():
    candles = _make_candles([1, 2, 3, 4, 5, 6], [1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
    experiment = run_sma_cross_experiments(candles, [2, 3], [4, 5])
    best = experiment.results[0]
    assert best.total_return == max(r.total_return for r in experiment.results)


def test_results_deterministic():
    candles = _make_candles([1, 2, 3, 4, 5], [2.0, 2.5, 3.0, 3.5, 4.0])
    run_a = run_sma_cross_experiments(candles, [2], [4])
    run_b = run_sma_cross_experiments(candles, [2], [4])
    assert run_a.results[0].total_return == run_b.results[0].total_return


def test_runner_results_can_be_exported():
    temp_dir = _make_workspace_temp_dir()
    try:
        candles = _make_candles([1, 2, 3, 4, 5, 6], [1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
        experiment = run_sma_cross_experiments(candles, [2, 3], [4, 5])
        output = temp_dir / "experiment_results.csv"

        export_experiment_results_to_csv(experiment.results, output)

        csv_text = output.read_text(encoding="utf-8")
        assert "rank,strategy,long_window,short_window,parameters_json,total_return" in csv_text
        assert "SimpleMovingAverageCrossStrategy" in csv_text
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
