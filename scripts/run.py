import argparse

from src.cli.run_common import bootstrap_run
from src.methods.launch_pipeline import launch_configured_jobs


def main(cfg_path: str, dry_run: bool = False):
    bootstrap = bootstrap_run(cfg_path, dry_run=dry_run)
    if bootstrap is None:
        return

    launch_configured_jobs(bootstrap.cfg, bootstrap.ctx)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load and run a simulation config.")
    parser.add_argument("config", help="Path to the YAML config file.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Load, validate, and print the config without running setup or submitting jobs.",
    )
    args = parser.parse_args()
    main(args.config, dry_run=args.dry_run)
