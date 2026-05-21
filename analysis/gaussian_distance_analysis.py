from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

try:
    from scipy.stats import norm
except ImportError:  # pragma: no cover - optional dependency
    norm = None

try:
    from scipy.signal import find_peaks
except ImportError:  # pragma: no cover - optional dependency
    find_peaks = None


k_B = 0.0019872041  # kcal/mol/K


def load_distances_for_replica(file_path: str | Path) -> np.ndarray:
    """
    Load COM distances from a gauss-rank style CV file.

    The parser skips comment/header lines starting with '#'
    and reads the last whitespace-separated column from each
    remaining data line as the COM distance in Angstrom.
    """
    path = Path(file_path)
    distances: list[float] = []

    with path.open() as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            parts = stripped.split()
            if len(parts) < 2:
                continue

            try:
                distances.append(float(parts[-1]))
            except ValueError as exc:
                raise ValueError(
                    f"Failed to parse COM distance from {path} at line {line_number}: {stripped}"
                ) from exc

    if len(distances) == 0:
        raise ValueError(f"No COM distance values found in {path}")

    return np.asarray(distances, dtype=float)


def _clean_distances(distances) -> np.ndarray:
    values = np.asarray(distances, dtype=float).ravel()
    values = values[np.isfinite(values)]
    if values.size == 0:
        raise ValueError("No finite distance values available for Gaussian analysis.")
    return values


def detect_multimodality(
    distances,
    bins="auto",
    peak_height_fraction=0.2,
    min_peak_distance_bins=2,
):
    distances = _clean_distances(distances)

    counts, edges = np.histogram(distances, bins=bins)
    centers = 0.5 * (edges[:-1] + edges[1:])

    if counts.size == 0 or counts.max() <= 0:
        peak_indices = np.asarray([], dtype=int)
    else:
        min_height = float(peak_height_fraction) * float(counts.max())
        min_distance = max(1, int(min_peak_distance_bins))

        if find_peaks is not None:
            peak_indices, properties = find_peaks(
                counts,
                height=min_height,
                distance=min_distance,
            )
            peak_heights = properties.get("peak_heights", counts[peak_indices])
        else:
            peak_index_list: list[int] = []
            for idx in range(1, len(counts) - 1):
                is_peak = counts[idx] > counts[idx - 1] and counts[idx] > counts[idx + 1]
                is_tall_enough = counts[idx] >= min_height
                is_far_enough = (
                    len(peak_index_list) == 0
                    or idx - peak_index_list[-1] >= min_distance
                )
                if is_peak and is_tall_enough and is_far_enough:
                    peak_index_list.append(idx)
            peak_indices = np.asarray(peak_index_list, dtype=int)
            peak_heights = counts[peak_indices]

        return {
            "n_major_peaks": int(len(peak_indices)),
            "major_peak_positions": centers[peak_indices].tolist(),
            "major_peak_heights": np.asarray(peak_heights, dtype=float).tolist(),
            "is_multimodal": bool(len(peak_indices) > 1),
            "hist_counts": counts.tolist(),
            "hist_edges": edges.tolist(),
        }

    return {
        "n_major_peaks": 0,
        "major_peak_positions": [],
        "major_peak_heights": [],
        "is_multimodal": False,
        "hist_counts": counts.tolist(),
        "hist_edges": edges.tolist(),
    }


def fit_gaussian_distance(distances, temperature=300.0):
    distances = _clean_distances(distances)

    n_samples = int(distances.size)
    mu = float(np.mean(distances))
    sigma = float(np.std(distances))
    variance = float(sigma ** 2)
    median = float(np.median(distances))
    min_value = float(np.min(distances))
    max_value = float(np.max(distances))

    if norm is not None:
        fit_mu, fit_sigma = norm.fit(distances)
        fit_mu = float(fit_mu)
        fit_sigma = float(fit_sigma)
    else:
        fit_mu = mu
        fit_sigma = sigma

    kBT = float(k_B * temperature)
    if sigma <= 0.0:
        k_eff = np.nan
    else:
        k_eff = float(kBT / variance)

    result = {
        "n_samples": n_samples,
        "mu": mu,
        "sigma": sigma,
        "variance": variance,
        "median": median,
        "min": min_value,
        "max": max_value,
        "fit_mu": fit_mu,
        "fit_sigma": fit_sigma,
        "kBT": kBT,
        "k_eff": k_eff,
    }

    multimodal_result = detect_multimodality(distances)
    result.update(multimodal_result)
    result["warning"] = ""
    if result["is_multimodal"]:
        result["warning"] = (
            "WARNING: COM-distance distribution appears multimodal. "
            "A single Gaussian fit may not be meaningful."
        )

    return result


def write_gaussian_results(
    results: Mapping[str, Mapping[str, float | int]],
    output_file: str | Path = "gaussian_distance_summary.txt",
) -> Path:
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    columns = [
        "n_samples",
        "mu",
        "sigma",
        "variance",
        "median",
        "min",
        "max",
        "fit_mu",
        "fit_sigma",
        "kBT",
        "k_eff",
        "n_major_peaks",
        "major_peak_positions",
        "major_peak_heights",
        "is_multimodal",
        "warning",
    ]

    lines = ["replica\t" + "\t".join(columns)]
    for replica_name, result in results.items():
        fields = [replica_name]
        for column in columns:
            value = result[column]
            if isinstance(value, bool):
                fields.append(str(value))
            elif isinstance(value, (int, np.integer)):
                fields.append(str(int(value)))
            elif isinstance(value, str):
                fields.append(value)
            elif isinstance(value, list):
                if len(value) == 0:
                    fields.append("")
                else:
                    fields.append(",".join(f"{float(item):.6f}" for item in value))
            elif np.isnan(value):
                fields.append("nan")
            else:
                fields.append(f"{float(value):.6f}")
        lines.append("\t".join(fields))

    output_path.write_text("\n".join(lines) + "\n")
    return output_path


def plot_gaussian_distance(distances, result, output_file="gaussian_fit.png"):
    distances = _clean_distances(distances)
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(8, 5))

    n_bins = min(50, max(10, int(np.sqrt(distances.size))))
    ax.hist(
        distances,
        bins=n_bins,
        density=True,
        alpha=0.6,
        color="steelblue",
        edgecolor="black",
        label="Distances",
    )

    fit_mu = float(result["fit_mu"])
    fit_sigma = float(result["fit_sigma"])
    if fit_sigma > 0.0:
        x_values = np.linspace(float(np.min(distances)), float(np.max(distances)), 400)
        if norm is not None:
            y_values = norm.pdf(x_values, loc=fit_mu, scale=fit_sigma)
        else:
            prefactor = 1.0 / (fit_sigma * np.sqrt(2.0 * np.pi))
            y_values = prefactor * np.exp(-0.5 * ((x_values - fit_mu) / fit_sigma) ** 2)
        ax.plot(
            x_values,
            y_values,
            color="crimson",
            linewidth=2.0,
            label=f"Gaussian fit ($\\mu$={fit_mu:.3f}, $\\sigma$={fit_sigma:.3f})",
        )

    for peak_idx, peak_position in enumerate(result.get("major_peak_positions", [])):
        label = "Major peak" if peak_idx == 0 else None
        ax.axvline(
            float(peak_position),
            color="darkgreen",
            linestyle="--",
            linewidth=1.5,
            label=label,
        )

    ax.set_xlabel("COM distance (Å)")
    ax.set_ylabel("Probability density")
    ax.set_title("Gaussian fit of COM distance")
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_path, dpi=200)
    plt.close(fig)
    return output_path


def analyze_gauss_rank_replicas(
    replica_distances: Mapping[str, Sequence[float]] | Sequence[Sequence[float]],
    output_dir: str | Path = "analysis",
    temperature: float = 300.0,
):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if isinstance(replica_distances, Mapping):
        replica_items = list(replica_distances.items())
    else:
        replica_items = [
            (f"rep{replica_idx}", distances)
            for replica_idx, distances in enumerate(replica_distances)
        ]

    all_results: dict[str, dict[str, float | int]] = {}
    for replica_name, distances in replica_items:
        result = fit_gaussian_distance(distances, temperature=temperature)
        all_results[replica_name] = result
        plot_gaussian_distance(
            distances,
            result,
            output_file=output_dir / f"{replica_name}_gaussian_fit.png",
        )

    summary_file = write_gaussian_results(
        all_results,
        output_file=output_dir / "gaussian_distance_summary.txt",
    )

    return {
        "results": all_results,
        "summary_file": summary_file,
        "output_dir": output_dir,
    }


def analyze_gauss_rank_replica_files(
    replica_files: Mapping[str, str | Path] | Sequence[str | Path],
    output_dir: str | Path = "analysis",
    temperature: float = 300.0,
):
    if isinstance(replica_files, Mapping):
        replica_distances = {
            replica_name: load_distances_for_replica(file_path)
            for replica_name, file_path in replica_files.items()
        }
    else:
        replica_distances = {
            f"rep{replica_idx}": load_distances_for_replica(file_path)
            for replica_idx, file_path in enumerate(replica_files)
        }

    return analyze_gauss_rank_replicas(
        replica_distances,
        output_dir=output_dir,
        temperature=temperature,
    )
