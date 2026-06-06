from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


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
) -> Path:
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    all_values = np.concatenate([np.asarray(block["y"], dtype=float) for block in ligand_blocks])
    bin_edges = build_histogram_bin_edges(all_values, bins=bins)

    fig, ax = plt.subplots(figsize=(8, 5))
    colors = plt.get_cmap("Set2")

    for idx, block in enumerate(ligand_blocks):
        block_values = np.asarray(block["y"], dtype=float)
        ax.hist(
            block_values,
            bins=bin_edges,
            histtype="stepfilled",
            alpha=0.28,
            color=colors(idx % colors.N),
            linewidth=1.5,
            label=f"{block['label']} (mean={float(block['y_mean']):.2f})",
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
        )

    return {
        "results": all_results,
        "output_dir": root_output_dir,
    }
