from __future__ import annotations

from datetime import datetime
from pathlib import Path
import shutil

import numpy as np

from src.utils.iterate_configured_methods import get_configured_method_names


class BackupManager:
    def __init__(self, cfg, paths: dict):
        self.cfg = cfg
        self.paths = paths

    def backup_run_targets(self) -> None:
        method_names = get_configured_method_names(self.cfg)

        if len(method_names) == 0:
            return

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

        for method_name in method_names:
            if method_name in {"eq", "rs_remd"}:
                self._backup_method_dir_if_present(method_name, timestamp=timestamp)
            elif method_name in {"pull", "us"}:
                self._backup_window_files(method_name, timestamp=timestamp)
            elif method_name == "us_remd":
                self._backup_us_remd_overlapping_blocks(timestamp=timestamp)
            else:
                self._backup_method_dir_if_present(method_name, timestamp=timestamp)

    def _format_window(self, window: float) -> str:
        return f"{float(window):.2f}"

    def _move_to_backup(self, path: Path, *, method_root: Path, backup_method_root: Path) -> None:
        if not path.exists():
            return

        rel_path = path.relative_to(method_root)
        dest_path = backup_method_root / rel_path
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(path), str(dest_path))
        print(f"[backup] moved {path} -> {dest_path}")

    def _backup_method_dir_if_present(self, method_name: str, *, timestamp: str) -> None:
        method_root = self.paths[method_name]["root"]
        if not method_root.exists() or not method_root.is_dir():
            return
        if not any(method_root.iterdir()):
            return

        backup_dest = self.paths["root"] / "_backup" / timestamp / method_name
        backup_dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(method_root), str(backup_dest))
        print(f"[backup] moved {method_root} -> {backup_dest}")

    def _windows_for_method(self, method_name: str) -> list[float]:
        if method_name == "pull":
            windows: list[float] = []
            for interval in self.cfg.methods.pull.pull_intervals:
                windows.extend(
                    self._format_window(window)
                    for window in np.arange(interval.start, interval.end + interval.step, interval.step)
                )
            window_values = [float(window) for window in windows]
        elif method_name == "us":
            windows = []
            for interval in self.cfg.methods.us.us_intervals:
                windows.extend(
                    self._format_window(window)
                    for window in np.arange(interval.start, interval.end + interval.step, interval.step)
                )
            window_values = [float(window) for window in windows]
        else:
            raise ValueError(f"_windows_for_method() only supports pull/us, got '{method_name}'")

        return window_values

    def _backup_window_files(self, method_name: str, *, timestamp: str) -> None:
        method_root = self.paths[method_name]["root"]
        if not method_root.exists():
            return

        backup_method_root = self.paths["root"] / "_backup" / timestamp / method_name
        windows = self._windows_for_method(method_name)

        for window in windows:
            window_str = self._format_window(window)
            if method_name == "pull":
                direct_paths = [
                    self.paths["pull"]["input"] / f"mdin5.w{window_str}",
                    self.paths["pull"]["input"] / f"pull{window_str}.r",
                    self.paths["pull"]["amber"] / f"restrt5.w{window_str}",
                    self.paths["pull"]["amber"] / f"mdout5.w{window_str}",
                    self.paths["pull"]["amber"] / f"traj5.w{window_str}.nc",
                    self.paths["pull"]["amber"] / f"mdinfo5.w{window_str}",
                    self.paths["pull"]["pmd"] / f"com_pull_{window_str}.txt",
                    self.paths["pull"]["pmd"] / f"pmd_pull_us{window_str}.txt",
                ]
                glob_patterns = [
                    self.paths["pull"]["slurm"] / f"slurm-*_pull{window_str}.out",
                ]
            elif method_name == "us":
                direct_paths = [
                    self.paths["us"]["input"] / f"mdin6.w{window_str}",
                    self.paths["us"]["input"] / f"_lroaus{window_str}.r",
                    self.paths["us"]["amber"] / f"restrt6.w{window_str}",
                    self.paths["us"]["amber"] / f"mdout6.w{window_str}",
                    self.paths["us"]["amber"] / f"traj6.w{window_str}.nc",
                    self.paths["us"]["amber"] / f"mdinfo6.w{window_str}",
                    self.paths["us"]["pmd"] / f"pmd_prod_us{window_str}.txt",
                ]
                glob_patterns = [
                    self.paths["us"]["slurm"] / f"slurm-*_us{window_str}.out",
                ]
            else:
                raise ValueError(f"Selective rerun backup is not implemented for method '{method_name}'")

            for direct_path in direct_paths:
                self._move_to_backup(direct_path, method_root=method_root, backup_method_root=backup_method_root)

            for pattern in glob_patterns:
                for matched_path in pattern.parent.glob(pattern.name):
                    self._move_to_backup(matched_path, method_root=method_root, backup_method_root=backup_method_root)

    def _backup_us_remd_overlapping_blocks(self, *, timestamp: str) -> None:
        method_root = self.paths["us_remd"]["root"]
        if not method_root.exists() or not method_root.is_dir():
            return

        input_dir = self.paths["us_remd"]["input"]
        amber_dir = self.paths["us_remd"]["amber"]
        slurm_dir = self.paths["us_remd"]["slurm"]
        backup_method_root = self.paths["root"] / "_backup" / timestamp / "us_remd"

        for block_idx, interval in enumerate(self.cfg.methods.us_remd.us_remd_intervals):
            windows = [
                self._format_window(window)
                for window in np.arange(interval.start, interval.end + interval.step, interval.step)
            ]
            overlap_detected = False

            block_specific_candidates = [
                input_dir / f"us_remd_block{block_idx}.groupfile",
            ]
            block_specific_candidates.extend(amber_dir.glob(f"restrt_usremd_b{block_idx}_rep*"))
            block_specific_candidates.extend(amber_dir.glob(f"mdout_usremd_b{block_idx}_rep*"))
            block_specific_candidates.extend(amber_dir.glob(f"traj_usremd_b{block_idx}_rep*.nc"))
            block_specific_candidates.extend(amber_dir.glob(f"mdinfo_usremd_b{block_idx}_rep*"))
            block_specific_candidates.extend(slurm_dir.glob(f"slurm-*_usremd_b{block_idx}.out"))

            for candidate in block_specific_candidates:
                if candidate.exists():
                    overlap_detected = True
                    break

            if not overlap_detected:
                for window_str in windows:
                    if (input_dir / f"mdin_usremd_w{window_str}").exists() or (
                        input_dir / f"_lroaus_usremd_w{window_str}.r"
                    ).exists():
                        overlap_detected = True
                        break

            if not overlap_detected:
                continue

            for candidate in block_specific_candidates:
                self._move_to_backup(candidate, method_root=method_root, backup_method_root=backup_method_root)

            for window_str in windows:
                self._move_to_backup(
                    input_dir / f"mdin_usremd_w{window_str}",
                    method_root=method_root,
                    backup_method_root=backup_method_root,
                )
                self._move_to_backup(
                    input_dir / f"_lroaus_usremd_w{window_str}.r",
                    method_root=method_root,
                    backup_method_root=backup_method_root,
                )
