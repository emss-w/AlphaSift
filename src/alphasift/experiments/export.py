from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Sequence

from alphasift.experiments.models import ExperimentResult


def export_experiment_results_to_csv(
    results: Sequence[ExperimentResult],
    output_path: str | Path,
    *,
    overwrite: bool = False,
) -> Path:
    """Export experiment results to a deterministic CSV file."""
    if not results:
        raise ValueError("results must be non-empty")

    destination = Path(output_path)
    if destination.exists() and not overwrite:
        raise FileExistsError(
            f"CSV output already exists at {destination}. Set overwrite=True to replace it."
        )

    parameter_columns = sorted(
        {
            key
            for result in results
            for key in result.parameters.keys()
            if key and key.isidentifier()
        }
    )

    fieldnames = [
        "rank",
        "strategy",
        *parameter_columns,
        "parameters_json",
        "total_return",
        "annualized_return",
        "max_drawdown",
        "trades",
        "final_equity",
    ]

    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()

        for index, result in enumerate(results, start=1):
            row: dict[str, object] = {
                "rank": index,
                "strategy": result.strategy,
                "parameters_json": json.dumps(result.parameters, sort_keys=True),
                "total_return": result.total_return,
                "annualized_return": result.annualized_return,
                "max_drawdown": result.max_drawdown,
                "trades": result.trades,
                "final_equity": result.final_equity,
            }
            for key in parameter_columns:
                row[key] = result.parameters.get(key)
            writer.writerow(row)

    return destination
