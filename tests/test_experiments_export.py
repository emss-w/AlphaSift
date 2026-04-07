import csv
import shutil
import uuid
from pathlib import Path

import pytest

from alphasift.experiments.export import export_experiment_results_to_csv
from alphasift.experiments.models import ExperimentResult


def _make_results() -> list[ExperimentResult]:
    return [
        ExperimentResult(
            strategy="SimpleMovingAverageCrossStrategy",
            parameters={"short_window": 5, "long_window": 30},
            total_return=0.2,
            annualized_return=0.15,
            max_drawdown=-0.1,
            trades=4,
            final_equity=1.2,
        ),
        ExperimentResult(
            strategy="SimpleMovingAverageCrossStrategy",
            parameters={"short_window": 10, "long_window": 50},
            total_return=0.1,
            annualized_return=None,
            max_drawdown=-0.08,
            trades=2,
            final_equity=1.1,
        ),
    ]


def _read_csv_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames is not None
        return reader.fieldnames, list(reader)


def _make_workspace_temp_dir() -> Path:
    base = Path("tests/.tmp_exports")
    temp_dir = base / uuid.uuid4().hex
    temp_dir.mkdir(parents=True, exist_ok=False)
    return temp_dir


def test_export_writes_expected_columns_and_rows():
    temp_dir = _make_workspace_temp_dir()
    try:
        results = _make_results()
        output = temp_dir / "exports" / "sma_results.csv"

        written_path = export_experiment_results_to_csv(results, output)
        assert written_path == output
        assert output.exists()

        fieldnames, rows = _read_csv_rows(output)
        assert fieldnames == [
            "rank",
            "strategy",
            "long_window",
            "short_window",
            "parameters_json",
            "total_return",
            "annualized_return",
            "max_drawdown",
            "trades",
            "final_equity",
        ]
        assert len(rows) == 2
        assert rows[0]["rank"] == "1"
        assert rows[0]["short_window"] == "5"
        assert rows[0]["long_window"] == "30"
        assert rows[0]["parameters_json"] == '{"long_window": 30, "short_window": 5}'
        assert rows[1]["rank"] == "2"
        assert rows[1]["annualized_return"] == ""
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_export_column_order_is_deterministic():
    temp_dir = _make_workspace_temp_dir()
    try:
        base = temp_dir
        output_a = base / "a.csv"
        output_b = base / "b.csv"
        results = _make_results()

        export_experiment_results_to_csv(results, output_a)
        export_experiment_results_to_csv(results, output_b)

        content_a = output_a.read_text(encoding="utf-8")
        content_b = output_b.read_text(encoding="utf-8")
        assert content_a == content_b
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_export_rejects_empty_results():
    temp_dir = _make_workspace_temp_dir()
    try:
        with pytest.raises(ValueError, match="results must be non-empty"):
            export_experiment_results_to_csv([], temp_dir / "out.csv")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_export_does_not_silently_overwrite():
    temp_dir = _make_workspace_temp_dir()
    try:
        output = temp_dir / "results.csv"
        export_experiment_results_to_csv(_make_results(), output)

        with pytest.raises(FileExistsError, match="already exists"):
            export_experiment_results_to_csv(_make_results(), output)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
