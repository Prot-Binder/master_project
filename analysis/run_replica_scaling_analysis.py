from __future__ import annotations

import argparse
from pathlib import Path

try:
    from analysis.replica_scaling_analysis import analyze_replica_scaling_files
    from analysis.rmsd_analysis import analyze_rmsd_files
except ImportError:
    from replica_scaling_analysis import analyze_replica_scaling_files
    from rmsd_analysis import analyze_rmsd_files


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run replica scaling analysis for all matching files in a directory."
    )
    parser.add_argument(
        "input_dir",
        help="Directory containing replica scaling files.",
    )
    parser.add_argument(
        "--prefix",
        default="com_pull_",
        help="Filename prefix used to select files and parse the intended COM distance.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory for output files. Defaults to <input_dir>/analysis.",
    )
    parser.add_argument(
        "--bins",
        default="auto",
        help="Histogram bin setting passed to NumPy. Default: auto",
    )
    parser.add_argument(
        "--smooth-window",
        type=int,
        default=5,
        help="Moving-average smoothing window for plotted histograms. Default: 5",
    )
    parser.add_argument(
        "--time-blocks",
        type=int,
        default=4,
        help="Number of contiguous blocks used to split the active value>0 region. Default: 4",
    )
    parser.add_argument(
        "--rmsd-prefix",
        default="pmd_pull_us",
        help="Filename prefix used to collect RMSD files for integrated RMSD analysis. Default: pmd_pull_us",
    )
    parser.add_argument(
        "--rmsd-average-blocks",
        type=int,
        default=10,
        help="Number of contiguous blocks for RMSD block-average plots. Default: 10",
    )
    parser.add_argument(
        "--rmsd-histogram-blocks",
        type=int,
        default=4,
        help="Number of contiguous blocks for ligand RMSD histogram plots. Default: 4",
    )
    return parser.parse_args()


def _collect_replica_files(input_dir: Path, prefix: str) -> dict[str, Path]:
    if not input_dir.is_dir():
        raise NotADirectoryError(f"Input directory does not exist or is not a directory: {input_dir}")

    replica_files = {
        file_path.stem: file_path
        for file_path in sorted(input_dir.iterdir())
        if file_path.is_file() and file_path.stem.startswith(prefix)
    }

    if len(replica_files) == 0:
        raise ValueError(f"No files with prefix '{prefix}' found in {input_dir}")

    return replica_files


def _collect_optional_files(input_dir: Path, prefix: str) -> dict[str, Path]:
    return {
        file_path.stem: file_path
        for file_path in sorted(input_dir.iterdir())
        if file_path.is_file() and file_path.stem.startswith(prefix)
    }


def _parse_bins(value: str) -> int | str:
    if value == "auto":
        return value
    return int(value)


def main() -> None:
    args = _parse_args()

    input_dir = Path(args.input_dir).resolve()
    output_dir = (
        Path(args.output_dir).resolve()
        if args.output_dir is not None
        else input_dir / "analysis"
    )

    replica_files = _collect_replica_files(input_dir, prefix=args.prefix)
    scaling_result = analyze_replica_scaling_files(
        replica_files,
        output_dir=output_dir,
        prefix=args.prefix,
        bins=_parse_bins(args.bins),
        smooth_window=args.smooth_window,
        n_blocks=args.time_blocks,
    )
    rmsd_files = _collect_optional_files(input_dir, prefix=args.rmsd_prefix)
    rmsd_result = None
    if len(rmsd_files) > 0:
        rmsd_result = analyze_rmsd_files(
            rmsd_files,
            output_dir=output_dir / "rmsd",
            average_blocks=args.rmsd_average_blocks,
            histogram_blocks=args.rmsd_histogram_blocks,
            bins=_parse_bins(args.bins),
        )

    print(f"Processed {len(replica_files)} replica scaling files from {input_dir}")
    print(f"Summary file: {scaling_result['summary_file']}")
    print(f"Block summary file: {scaling_result['block_summary_file']}")
    print(f"Plot file: {scaling_result['plot_file']}")
    print(f"Block histogram directory: {Path(scaling_result['output_dir']) / 'block_histograms'}")
    if rmsd_result is None:
        print(f"No RMSD files with prefix '{args.rmsd_prefix}' found in {input_dir}")
    else:
        print(f"Processed {len(rmsd_files)} RMSD file(s) from {input_dir}")
        print(f"RMSD output directory: {rmsd_result['output_dir']}")


if __name__ == "__main__":
    main()
