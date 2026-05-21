from __future__ import annotations

import argparse
from pathlib import Path

try:
    from analysis.gaussian_distance_analysis import analyze_gauss_rank_replica_files
except ImportError:
    from gaussian_distance_analysis import analyze_gauss_rank_replica_files


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Gaussian COM-distance analysis for all replica files in a directory."
    )
    parser.add_argument(
        "input_dir",
        help="Directory containing replica CV files. The last column of each data row is used as COM distance.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory for the summary text file and plots. Defaults to <input_dir>/analysis.",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=300.0,
        help="Temperature in K used for k_eff. Default: 300.0",
    )
    return parser.parse_args()


def _collect_replica_files(input_dir: Path) -> dict[str, Path]:
    if not input_dir.is_dir():
        raise NotADirectoryError(f"Input directory does not exist or is not a directory: {input_dir}")

    replica_files = {
        file_path.stem: file_path
        for file_path in sorted(input_dir.iterdir())
        if file_path.is_file()
    }

    if len(replica_files) == 0:
        raise ValueError(f"No files found in input directory: {input_dir}")

    return replica_files


def main() -> None:
    args = _parse_args()

    input_dir = Path(args.input_dir).resolve()
    output_dir = (
        Path(args.output_dir).resolve()
        if args.output_dir is not None
        else input_dir / "analysis"
    )

    replica_files = _collect_replica_files(input_dir)
    result = analyze_gauss_rank_replica_files(
        replica_files,
        output_dir=output_dir,
        temperature=args.temperature,
    )

    print(f"Processed {len(replica_files)} replica files from {input_dir}")
    print(f"Summary file: {result['summary_file']}")
    print(f"Plots directory: {result['output_dir']}")


if __name__ == "__main__":
    main()
