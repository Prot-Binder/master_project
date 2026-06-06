from __future__ import annotations

import argparse
from pathlib import Path

try:
    from analysis.rmsd_analysis import analyze_rmsd_files
except ImportError:
    from rmsd_analysis import analyze_rmsd_files


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run ligand/receptor RMSD analysis for pmd_pull_us*.txt files."
    )
    parser.add_argument(
        "input_path",
        help="Either a single pmd_pull_us*.txt file or a directory containing such files.",
    )
    parser.add_argument(
        "--prefix",
        default="pmd_pull_us",
        help="Filename prefix used when input_path is a directory. Default: pmd_pull_us",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory for output files. Defaults to <input_path>/analysis or <file_dir>/analysis.",
    )
    parser.add_argument(
        "--average-blocks",
        type=int,
        default=10,
        help="Number of contiguous blocks for the averaged RMSD-vs-time plot. Default: 10",
    )
    parser.add_argument(
        "--histogram-blocks",
        type=int,
        default=4,
        help="Number of contiguous blocks for the ligand RMSD histogram plot. Default: 4",
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
        help="Moving-average smoothing window for RMSD histogram overlays. Default: 5",
    )
    return parser.parse_args()


def _parse_bins(value: str) -> int | str:
    if value == "auto":
        return value
    return int(value)


def _collect_rmsd_files(input_path: Path, prefix: str) -> dict[str, Path]:
    if input_path.is_file():
        return {input_path.stem: input_path}

    if not input_path.is_dir():
        raise NotADirectoryError(f"Input path does not exist or is neither a file nor a directory: {input_path}")

    rmsd_files = {
        file_path.stem: file_path
        for file_path in sorted(input_path.iterdir())
        if file_path.is_file() and file_path.stem.startswith(prefix)
    }
    if len(rmsd_files) == 0:
        raise ValueError(f"No files with prefix '{prefix}' found in {input_path}")
    return rmsd_files


def main() -> None:
    args = _parse_args()

    input_path = Path(args.input_path).resolve()
    output_dir = (
        Path(args.output_dir).resolve()
        if args.output_dir is not None
        else (input_path / "analysis" if input_path.is_dir() else input_path.parent / "analysis")
    )

    rmsd_files = _collect_rmsd_files(input_path, prefix=args.prefix)
    result = analyze_rmsd_files(
        rmsd_files,
        output_dir=output_dir,
        average_blocks=args.average_blocks,
        histogram_blocks=args.histogram_blocks,
        bins=_parse_bins(args.bins),
        smooth_window=args.smooth_window,
    )

    print(f"Processed {len(rmsd_files)} RMSD file(s) from {input_path}")
    print(f"Output directory: {result['output_dir']}")
    for file_label, file_result in result["results"].items():
        print(f"[{file_label}] summary: {file_result['summary_file']}")
        print(f"[{file_label}] time plot: {file_result['rmsd_time_plot']}")
        print(f"[{file_label}] block-average plot: {file_result['block_average_plot']}")
        print(f"[{file_label}] ligand histogram plot: {file_result['ligand_histogram_plot']}")


if __name__ == "__main__":
    main()
