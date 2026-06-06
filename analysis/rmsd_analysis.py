from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

try:
    from scipy.stats import gaussian_kde
except ImportError:  # pragma: no cover - optional dependency
    gaussian_kde = None


def load_rmsd_components(file_path: str | Path) -> dict[str, np.ndarray]:
    path = Path(file_path)
    time_values: list[float] = []
    ligand_values: list[float] = []
    receptor_values: list[float] = []

    with path.open() as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            parts = stripped.split()
            if len(parts) < 3:
                raise ValueError(
                    f"Expected at least 3 columns in {path} at line {line_number}: {stripped}"
                )

            try:
                time_value = float(parts[0])
                ligand_value = float(parts[1])
                receptor_value = float(parts[2])
            except ValueError as exc:
                raise ValueError(
                    f"Failed to parse time/ligand/receptor RMSD columns from {path} at line {line_number}: {stripped}"
                ) from exc

            time_values.append(time_value)
            ligand_values.append(ligand_value)
            receptor_values.append(receptor_value)

    if len(time_values) == 0:
        raise ValueError(f"No RMSD data rows found in {path}")

    time_array = np.asarray(time_values, dtype=float)
    ligand_array = np.asarray(ligand_values, dtype=float)
    receptor_array = np.asarray(receptor_values, dtype=float)
    finite_mask = np.isfinite(time_array) & np.isfinite(ligand_array) & np.isfinite(receptor_array)
    if not np.any(finite_mask):
        raise ValueError(f"No finite RMSD samples found in {path}")

    return {
        "time": time_array[finite_mask],
        "ligand_rmsd": ligand_array[finite_mask],
        "receptor_rmsd": receptor_array[finite_mask],
    }


def split_series_blocks(
    x_values: Sequence[float],
    y_values: Sequence[float],
    n_blocks: int,
) -> list[dict[str, object]]:
    x_array = np.asarray(x_values, dtype=float).ravel()
    y_array = np.asarray(y_values, dtype=float).ravel()
    if x_array.size != y_array.size:
        raise ValueError("x_values and y_values must have the same length.")
    if x_array.size == 0:
        raise ValueError("Cannot split an empty RMSD series.")
    if n_blocks < 1:
        raise ValueError("n_blocks must be at least 1.")

    blocks: list[dict[str, object]] = []
    x_splits = np.array_split(x_array, n_blocks)
    y_splits = np.array_split(y_array, n_blocks)

    for block_idx, (block_x, block_y) in enumerate(zip(x_splits, y_splits, strict=False)):
        block_x = np.asarray(block_x, dtype=float)
        block_y = np.asarray(block_y, dtype=float)
        if block_x.size == 0:
            continue

        fraction_start = float(block_idx) / float(n_blocks)
        fraction_end = float(block_idx + 1) / float(n_blocks)
        blocks.append(
            {
                "block_index": block_idx,
                "fraction_start": fraction_start,
                "fraction_end": fraction_end,
                "label": f"{int(round(fraction_start * 100.0))}-{int(round(fraction_end * 100.0))}%",
                "x": block_x,
                "y": block_y,
                "x_mean": float(np.mean(block_x)),
                "y_mean": float(np.mean(block_y)),
                "n_samples": int(block_y.size),
            }
        )

    if len(blocks) == 0:
        raise ValueError("No non-empty RMSD blocks were created.")

    return blocks


def build_histogram_bin_edges(values: Sequence[float], bins: int | str = "auto") -> np.ndarray:
    sample_values = np.asarray(values, dtype=float).ravel()
    sample_values = sample_values[np.isfinite(sample_values)]
    if sample_values.size == 0:
        raise ValueError("Cannot build histogram bins from an empty RMSD series.")

    bin_edges = np.histogram_bin_edges(sample_values, bins=bins)
    if np.unique(bin_edges).size < 2:
        value = float(sample_values[0])
        bin_edges = np.array([value - 0.5, value + 0.5], dtype=float)
    return np.asarray(bin_edges, dtype=float)


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


def plot_rmsd_vs_time(series: Mapping[str, np.ndarray], output_file: str | Path) -> Path:
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(series["time"], series["ligand_rmsd"], color="teal", linewidth=1.2, label="Ligand RMSD")
    ax.plot(series["time"], series["receptor_rmsd"], color="darkorange", linewidth=1.2, label="Receptor RMSD")
    ax.set_xlabel("Time")
    ax.set_ylabel("RMSD")
    ax.set_title("Ligand and receptor RMSD vs time")
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_path, dpi=200)
    plt.close(fig)
    return output_path


def plot_block_averages_vs_time(
    ligand_blocks: Sequence[Mapping[str, object]],
    receptor_blocks: Sequence[Mapping[str, object]],
    output_file: str | Path,
) -> Path:
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    ligand_x = np.asarray([block["x_mean"] for block in ligand_blocks], dtype=float)
    ligand_y = np.asarray([block["y_mean"] for block in ligand_blocks], dtype=float)
    receptor_x = np.asarray([block["x_mean"] for block in receptor_blocks], dtype=float)
    receptor_y = np.asarray([block["y_mean"] for block in receptor_blocks], dtype=float)

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(ligand_x, ligand_y, marker="o", color="teal", linewidth=2.0, label="Ligand RMSD block mean")
    ax.plot(receptor_x, receptor_y, marker="o", color="darkorange", linewidth=2.0, label="Receptor RMSD block mean")
    ax.set_xlabel("Block-mean time")
    ax.set_ylabel("Average RMSD")
    ax.set_title("Ligand and receptor RMSD block averages")
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_path, dpi=200)
    plt.close(fig)
    return output_path


def plot_ligand_block_histograms(
    ligand_blocks: Sequence[Mapping[str, object]],
    output_file: str | Path,
    bins: int | str = "auto",
    smooth_window: int = 5,
) -> Path:
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    all_values = np.concatenate([np.asarray(block["y"], dtype=float) for block in ligand_blocks])
    bin_edges = build_histogram_bin_edges(all_values, bins=bins)

    fig, ax = plt.subplots(figsize=(8, 5))
    colors = plt.get_cmap("Set2")
    global_max = 0.0

    for block in ligand_blocks:
        _, smooth_y = compute_kde_curve(
            block["y"],
            bin_edges,
            fallback_window=smooth_window,
        )
        if smooth_y.size > 0:
            global_max = max(global_max, float(np.max(smooth_y)))

    for idx, block in enumerate(ligand_blocks):
        block_values = np.asarray(block["y"], dtype=float)
        counts, _ = np.histogram(block_values, bins=bin_edges)
        smooth_x, smooth_y = compute_kde_curve(
            block_values,
            bins=bin_edges,
            fallback_window=smooth_window,
        )
        color = colors(idx % colors.N)

        ax.stairs(
            counts,
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
            label=f"{block['label']} (mean={float(block['y_mean']):.2f})",
        )

        if smooth_y.size > 0:
            peak_idx = int(np.argmax(smooth_y))
            peak_x = float(smooth_x[peak_idx])
            peak_y = float(smooth_y[peak_idx])
        else:
            peak_x = float(block["y_mean"])
            peak_y = 0.0

        y_offset = 0.03 * global_max if global_max > 0.0 else 0.1
        ax.text(
            peak_x,
            peak_y + y_offset,
            f"{float(block['y_mean']):.2f}",
            color=colors(idx % colors.N),
            fontsize=9,
            ha="center",
            va="bottom",
        )

    ax.set_xlabel("Ligand RMSD")
    ax.set_ylabel("Count")
    ax.set_title("Ligand RMSD histograms by time block")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(output_path, dpi=200)
    plt.close(fig)
    return output_path


def write_rmsd_summary(
    rmsd_file: str | Path,
    series: Mapping[str, np.ndarray],
    ligand_avg_blocks: Sequence[Mapping[str, object]],
    receptor_avg_blocks: Sequence[Mapping[str, object]],
    ligand_hist_blocks: Sequence[Mapping[str, object]],
    output_file: str | Path = "rmsd_summary.txt",
) -> Path:
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    ligand_values = np.asarray(series["ligand_rmsd"], dtype=float)
    receptor_values = np.asarray(series["receptor_rmsd"], dtype=float)

    lines = [
        f"file={Path(rmsd_file).name}",
        f"n_samples={ligand_values.size}",
        "",
        "[ligand]",
        f"mean={float(np.mean(ligand_values)):.6f}",
        f"std={float(np.std(ligand_values)):.6f}",
        f"min={float(np.min(ligand_values)):.6f}",
        f"max={float(np.max(ligand_values)):.6f}",
        "",
        "[receptor]",
        f"mean={float(np.mean(receptor_values)):.6f}",
        f"std={float(np.std(receptor_values)):.6f}",
        f"min={float(np.min(receptor_values)):.6f}",
        f"max={float(np.max(receptor_values)):.6f}",
        "",
        "[block_average_10]",
        "series\tblock_index\tblock_label\tx_mean\ty_mean\tn_samples",
    ]

    for series_name, blocks in (("ligand", ligand_avg_blocks), ("receptor", receptor_avg_blocks)):
        for block in blocks:
            lines.append(
                "\t".join(
                    [
                        series_name,
                        str(int(block["block_index"])),
                        str(block["label"]),
                        f"{float(block['x_mean']):.6f}",
                        f"{float(block['y_mean']):.6f}",
                        str(int(block["n_samples"])),
                    ]
                )
            )

    lines.append("")
    lines.append("[ligand_histogram_blocks]")
    lines.append("block_index\tblock_label\tfraction_start\tfraction_end\ty_mean\tn_samples")
    for block in ligand_hist_blocks:
        lines.append(
            "\t".join(
                [
                    str(int(block["block_index"])),
                    str(block["label"]),
                    f"{float(block['fraction_start']):.6f}",
                    f"{float(block['fraction_end']):.6f}",
                    f"{float(block['y_mean']):.6f}",
                    str(int(block["n_samples"])),
                ]
            )
        )

    output_path.write_text("\n".join(lines) + "\n")
    return output_path


def analyze_rmsd_file(
    rmsd_file: str | Path,
    output_dir: str | Path = "analysis",
    average_blocks: int = 10,
    histogram_blocks: int = 4,
    bins: int | str = "auto",
    smooth_window: int = 5,
) -> dict[str, object]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    series = load_rmsd_components(rmsd_file)

    ligand_avg_blocks = split_series_blocks(series["time"], series["ligand_rmsd"], n_blocks=average_blocks)
    receptor_avg_blocks = split_series_blocks(series["time"], series["receptor_rmsd"], n_blocks=average_blocks)
    ligand_hist_blocks = split_series_blocks(series["time"], series["ligand_rmsd"], n_blocks=histogram_blocks)

    rmsd_time_plot = plot_rmsd_vs_time(
        series,
        output_file=output_path / "rmsd_vs_time.png",
    )
    block_average_plot = plot_block_averages_vs_time(
        ligand_avg_blocks,
        receptor_avg_blocks,
        output_file=output_path / "rmsd_block_averages_vs_time.png",
    )
    ligand_histogram_plot = plot_ligand_block_histograms(
        ligand_hist_blocks,
        output_file=output_path / "ligand_rmsd_block_histograms.png",
        bins=bins,
        smooth_window=smooth_window,
    )
    summary_file = write_rmsd_summary(
        rmsd_file=rmsd_file,
        series=series,
        ligand_avg_blocks=ligand_avg_blocks,
        receptor_avg_blocks=receptor_avg_blocks,
        ligand_hist_blocks=ligand_hist_blocks,
        output_file=output_path / "rmsd_summary.txt",
    )

    return {
        "series": series,
        "ligand_avg_blocks": ligand_avg_blocks,
        "receptor_avg_blocks": receptor_avg_blocks,
        "ligand_hist_blocks": ligand_hist_blocks,
        "summary_file": summary_file,
        "rmsd_time_plot": rmsd_time_plot,
        "block_average_plot": block_average_plot,
        "ligand_histogram_plot": ligand_histogram_plot,
        "output_dir": output_path,
    }


def analyze_rmsd_files(
    rmsd_files: Mapping[str, str | Path] | Sequence[str | Path],
    output_dir: str | Path = "analysis",
    average_blocks: int = 10,
    histogram_blocks: int = 4,
    bins: int | str = "auto",
    smooth_window: int = 5,
) -> dict[str, object]:
    root_output_dir = Path(output_dir)
    root_output_dir.mkdir(parents=True, exist_ok=True)

    if isinstance(rmsd_files, Mapping):
        file_items = list(rmsd_files.items())
    else:
        file_items = [(Path(file_path).stem, file_path) for file_path in rmsd_files]

    if len(file_items) == 0:
        raise ValueError("No RMSD files were provided for analysis.")

    all_results: dict[str, dict[str, object]] = {}
    for file_label, file_path in file_items:
        per_file_output_dir = root_output_dir / str(file_label)
        all_results[str(file_label)] = analyze_rmsd_file(
            file_path,
            output_dir=per_file_output_dir,
            average_blocks=average_blocks,
            histogram_blocks=histogram_blocks,
            bins=bins,
            smooth_window=smooth_window,
        )

    return {
        "results": all_results,
        "output_dir": root_output_dir,
    }
