from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

try:
    from scipy.stats import gaussian_kde
except ImportError:  # pragma: no cover - optional dependency
    gaussian_kde = None


def load_replica_scaling_series(file_path: str | Path) -> np.ndarray:
    path = Path(file_path)
    values: list[float] = []

    with path.open() as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            parts = stripped.split()
            if len(parts) < 3:
                continue

            try:
                values.append(float(parts[2]))
            except ValueError as exc:
                raise ValueError(
                    f"Failed to parse third column from {path} at line {line_number}: {stripped}"
                ) from exc

    if len(values) == 0:
        raise ValueError(f"No third-column values found in {path}")

    return np.asarray(values, dtype=float)


def extract_active_tail(values) -> dict[str, np.ndarray | int]:
    series = np.asarray(values, dtype=float).ravel()
    series = series[np.isfinite(series)]
    if series.size == 0:
        raise ValueError("No finite values available for replica scaling analysis.")

    positive_indices = np.flatnonzero(series > 0.0)
    if positive_indices.size == 0:
        raise ValueError("No values > 0 found in the third column.")

    active_start_idx = int(positive_indices[0])
    active_values = series[active_start_idx:]
    tail_start = len(active_values) // 2
    tail_values = active_values[tail_start:]

    if tail_values.size == 0:
        raise ValueError("No data left after selecting the last 50% of the active region.")

    return {
        "series": series,
        "active_start_idx": active_start_idx,
        "active_values": active_values,
        "tail_values": tail_values,
    }


def parse_intended_center_from_filename(file_path: str | Path, prefix: str = "com_pull_") -> float:
    stem = Path(file_path).stem
    if not stem.startswith(prefix):
        raise ValueError(f"Filename does not start with prefix '{prefix}': {stem}")

    suffix = stem[len(prefix):]
    match = re.search(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", suffix)
    if match is None:
        raise ValueError(f"Could not parse intended center from filename: {stem}")

    return float(match.group(0))


def smooth_histogram_counts(counts, window: int = 5) -> np.ndarray:
    values = np.asarray(counts, dtype=float)
    if window <= 1 or values.size == 0:
        return values

    window = int(window)
    if window % 2 == 0:
        window += 1

    kernel = np.ones(window, dtype=float) / float(window)
    return np.convolve(values, kernel, mode="same")


def compute_kde_curve(values, bin_edges, fallback_window: int = 5) -> tuple[np.ndarray, np.ndarray]:
    sample_values = np.asarray(values, dtype=float)
    sample_values = sample_values[np.isfinite(sample_values)]
    if sample_values.size == 0:
        return np.asarray([], dtype=float), np.asarray([], dtype=float)

    x_min = float(np.min(sample_values))
    x_max = float(np.max(sample_values))
    if x_min == x_max:
        x_values = np.array([x_min], dtype=float)
        y_values = np.array([float(sample_values.size)], dtype=float)
        return x_values, y_values

    x_values = np.linspace(x_min, x_max, 400)

    if gaussian_kde is not None and sample_values.size > 1:
        kde = gaussian_kde(sample_values)
        bin_widths = np.diff(np.asarray(bin_edges, dtype=float))
        scale = float(sample_values.size) * float(np.mean(bin_widths))
        y_values = kde(x_values) * scale
        return x_values, np.asarray(y_values, dtype=float)

    counts, edges = np.histogram(sample_values, bins=bin_edges)
    centers = 0.5 * (edges[:-1] + edges[1:])
    smoothed_counts = smooth_histogram_counts(counts, window=fallback_window)
    y_values = np.interp(x_values, centers, smoothed_counts, left=0.0, right=0.0)
    return x_values, y_values


def compute_histogram_center(counts, bin_centers) -> float:
    counts = np.asarray(counts, dtype=float)
    bin_centers = np.asarray(bin_centers, dtype=float)
    total = float(np.sum(counts))
    if total <= 0.0:
        return float("nan")
    return float(np.sum(counts * bin_centers) / total)


def write_replica_scaling_results(
    results: Sequence[Mapping[str, float | int | str]],
    output_file: str | Path = "replica_scaling_summary.txt",
) -> Path:
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    columns = [
        "replica",
        "file_name",
        "intended_center",
        "actual_center",
        "delta_actual_minus_intended",
        "n_total",
        "active_start_idx",
        "n_active",
        "n_tail",
    ]

    lines = ["\t".join(columns)]
    for result in results:
        fields: list[str] = []
        for column in columns:
            value = result[column]
            if isinstance(value, (int, np.integer)):
                fields.append(str(int(value)))
            elif isinstance(value, str):
                fields.append(value)
            elif np.isnan(value):
                fields.append("nan")
            else:
                fields.append(f"{float(value):.6f}")
        lines.append("\t".join(fields))

    output_path.write_text("\n".join(lines) + "\n")
    return output_path


def plot_replica_scaling_histograms(
    histogram_results: Sequence[Mapping[str, object]],
    output_file: str | Path = "replica_scaling_histograms.png",
    smooth_window: int = 5,
) -> Path:
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(10, 6))
    cmap = plt.get_cmap("tab20")

    global_max = 0.0
    for result in histogram_results:
        _, smooth_y = compute_kde_curve(
            result["tail_values"],
            result["bin_edges"],
            fallback_window=smooth_window,
        )
        if smooth_y.size > 0:
            global_max = max(global_max, float(np.max(smooth_y)))

    for idx, result in enumerate(histogram_results):
        color = cmap(idx % cmap.N)
        bin_edges = np.asarray(result["bin_edges"], dtype=float)
        raw_counts = np.asarray(result["hist_counts"], dtype=float)
        smooth_x, smooth_y = compute_kde_curve(
            result["tail_values"],
            bin_edges,
            fallback_window=smooth_window,
        )

        ax.stairs(
            raw_counts,
            bin_edges,
            fill=True,
            alpha=0.18,
            color=color,
            linewidth=1.0,
        )

        ax.plot(
            smooth_x,
            smooth_y,
            linewidth=2.0,
            color=color,
            label=f"{result['replica']} (target={float(result['intended_center']):.2f})",
        )

        if smooth_y.size > 0:
            peak_idx = int(np.argmax(smooth_y))
            peak_x = float(smooth_x[peak_idx])
            peak_y = float(smooth_y[peak_idx])
        else:
            peak_x = float(result["actual_center"])
            peak_y = 0.0

        delta = float(result["delta_actual_minus_intended"])
        delta_color = "green" if delta < 0.0 else "red"
        y_offset = 0.03 * global_max if global_max > 0.0 else 0.1
        ax.text(
            peak_x,
            peak_y + y_offset,
            f"{delta:+.2f}",
            color=delta_color,
            fontsize=9,
            ha="center",
            va="bottom",
        )

    ax.set_xlabel("COM distance")
    ax.set_ylabel("Count")
    ax.set_title("Replica scaling histograms")
    ax.legend(fontsize=8, ncols=2)
    fig.tight_layout()
    fig.savefig(output_path, dpi=200)
    plt.close(fig)
    return output_path


def analyze_replica_scaling_files(
    replica_files: Mapping[str, str | Path] | Sequence[str | Path],
    output_dir: str | Path = "analysis",
    prefix: str = "com_pull_",
    bins: int | str = "auto",
    smooth_window: int = 5,
):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if isinstance(replica_files, Mapping):
        replica_items = list(replica_files.items())
    else:
        replica_items = [
            (Path(file_path).stem, file_path)
            for file_path in replica_files
        ]

    prepared_results: list[dict[str, object]] = []
    all_tail_values: list[np.ndarray] = []

    for replica_name, file_path in replica_items:
        intended_center = parse_intended_center_from_filename(file_path, prefix=prefix)
        series = load_replica_scaling_series(file_path)
        extracted = extract_active_tail(series)
        tail_values = np.asarray(extracted["tail_values"], dtype=float)

        prepared_results.append(
            {
                "replica": replica_name,
                "file_name": Path(file_path).name,
                "file_path": Path(file_path),
                "intended_center": intended_center,
                "series": np.asarray(extracted["series"], dtype=float),
                "active_start_idx": int(extracted["active_start_idx"]),
                "active_values": np.asarray(extracted["active_values"], dtype=float),
                "tail_values": tail_values,
            }
        )
        all_tail_values.append(tail_values)

    if len(all_tail_values) == 0:
        raise ValueError("No replica files available for replica scaling analysis.")

    combined_values = np.concatenate(all_tail_values)
    bin_edges = np.histogram_bin_edges(combined_values, bins=bins)
    bin_centers = 0.5 * (bin_edges[:-1] + bin_edges[1:])

    final_results: list[dict[str, object]] = []
    for result in prepared_results:
        counts, _ = np.histogram(result["tail_values"], bins=bin_edges)
        actual_center = compute_histogram_center(counts, bin_centers)
        delta = actual_center - float(result["intended_center"])

        final_results.append(
            {
                "replica": result["replica"],
                "file_name": result["file_name"],
                "intended_center": float(result["intended_center"]),
                "actual_center": actual_center,
                "delta_actual_minus_intended": delta,
                "n_total": int(len(result["series"])),
                "active_start_idx": int(result["active_start_idx"]),
                "n_active": int(len(result["active_values"])),
                "n_tail": int(len(result["tail_values"])),
                "tail_values": np.asarray(result["tail_values"], dtype=float),
                "hist_counts": counts,
                "bin_centers": bin_centers,
                "bin_edges": bin_edges,
            }
        )

    final_results.sort(key=lambda item: float(item["intended_center"]))

    summary_file = write_replica_scaling_results(
        final_results,
        output_file=output_dir / "replica_scaling_summary.txt",
    )
    plot_file = plot_replica_scaling_histograms(
        final_results,
        output_file=output_dir / "replica_scaling_histograms.png",
        smooth_window=smooth_window,
    )

    return {
        "results": final_results,
        "summary_file": summary_file,
        "plot_file": plot_file,
        "output_dir": output_dir,
    }
