#!/usr/bin/env python3
import argparse
import csv
import json
from pathlib import Path
from typing import Any

import numpy as np


def _safe_stats(x: np.ndarray) -> dict[str, float]:
    x = np.asarray(x, dtype=float).ravel()
    valid = np.isfinite(x)
    if not np.any(valid):
        return {
            "n": 0,
            "mean": float("nan"),
            "std": float("nan"),
            "p25": float("nan"),
            "p50": float("nan"),
            "p75": float("nan"),
        }
    xv = x[valid]
    q25, q50, q75 = np.quantile(xv, [0.25, 0.5, 0.75])
    return {
        "n": int(xv.size),
        "mean": float(np.mean(xv)),
        "std": float(np.std(xv)),
        "p25": float(q25),
        "p50": float(q50),
        "p75": float(q75),
    }


def _flatten_cell_pair(values_cell: np.ndarray, labels_cell: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    out_values = []
    out_labels = []
    for values, labels in zip(np.ravel(values_cell), np.ravel(labels_cell)):
        v = np.asarray(values).ravel().astype(float)
        l = np.asarray(labels).ravel().astype(int)
        n = min(len(v), len(l))
        if n == 0:
            continue
        out_values.append(v[:n])
        out_labels.append(l[:n])
    if not out_values:
        return np.array([], dtype=float), np.array([], dtype=int)
    return np.concatenate(out_values), np.concatenate(out_labels)


def extract_summary(mat_path: Path, fps: int, run_thresh_cm_s: float) -> dict[str, Any]:
    try:
        import scipy.io as sio
    except ImportError as exc:
        raise RuntimeError("scipy is required for reading this .mat file") from exc

    mat = sio.loadmat(mat_path, squeeze_me=True, struct_as_record=False)

    all_app = np.asarray(mat["allAppT"]).astype(int).ravel()
    all_avg_phi = np.asarray(mat["allAvgPhi"]).astype(float).ravel()
    d_all_avg_phi = np.asarray(mat["d_allAvgPhi"]).astype(float).ravel()
    d_head = np.asarray(mat["d_headThDLC"]).astype(float).ravel()
    vergence = np.asarray(mat["vergence"]).astype(float).ravel()
    d_vergence = np.asarray(mat["dVergence"]).astype(float).ravel()

    approach_mask = all_app == 1
    nonapproach_mask = all_app == 0

    mouse_vel, app_epoch = _flatten_cell_pair(mat["mouseVel"], mat["approachEpochs"])
    valid_mv = np.isfinite(mouse_vel)
    running_mask = valid_mv & (mouse_vel >= run_thresh_cm_s)
    stationary_mask = valid_mv & (mouse_vel < run_thresh_cm_s)

    summary = {
        "source_mat": str(mat_path),
        "fps": int(fps),
        "velocity_units_note": "All d* fields in dataset are deg/frame; multiply by fps for deg/s.",
        "labels": {
            "approach": int(np.sum(approach_mask)),
            "nonapproach": int(np.sum(nonapproach_mask)),
        },
        "gaze_stats_deg_per_frame": {
            "approach": {
                "allAvgPhi": _safe_stats(all_avg_phi[approach_mask]),
                "d_allAvgPhi": _safe_stats(d_all_avg_phi[approach_mask]),
                "d_headThDLC": _safe_stats(d_head[approach_mask]),
                "vergence": _safe_stats(vergence[approach_mask]),
                "dVergence": _safe_stats(d_vergence[approach_mask]),
            },
            "nonapproach": {
                "allAvgPhi": _safe_stats(all_avg_phi[nonapproach_mask]),
                "d_allAvgPhi": _safe_stats(d_all_avg_phi[nonapproach_mask]),
                "d_headThDLC": _safe_stats(d_head[nonapproach_mask]),
                "vergence": _safe_stats(vergence[nonapproach_mask]),
                "dVergence": _safe_stats(d_vergence[nonapproach_mask]),
            },
        },
        "mouse_velocity_cm_per_s": {
            "threshold_for_running": float(run_thresh_cm_s),
            "all_valid": _safe_stats(mouse_vel[valid_mv]),
            "running": _safe_stats(mouse_vel[running_mask]),
            "stationary": _safe_stats(mouse_vel[stationary_mask]),
            "approach_only": _safe_stats(mouse_vel[(app_epoch == 1) & valid_mv]),
            "nonapproach_only": _safe_stats(mouse_vel[(app_epoch == 0) & valid_mv]),
        },
        "gaze_velocity_deg_per_second": {
            "approach_d_allAvgPhi": _safe_stats(d_all_avg_phi[approach_mask] * fps),
            "nonapproach_d_allAvgPhi": _safe_stats(d_all_avg_phi[nonapproach_mask] * fps),
            "approach_d_headThDLC": _safe_stats(d_head[approach_mask] * fps),
            "nonapproach_d_headThDLC": _safe_stats(d_head[nonapproach_mask] * fps),
        },
    }
    return summary


def simulate_to_csv(
    output_csv: Path,
    n_frames: int,
    mode: str,
    pano_w: int,
    pano_h: int,
    crop_size: int,
    fps: int,
    px_per_deg: int,
    seed: int,
) -> None:
    import sys

    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    from trajectory_generation import generate_gaze

    pts = generate_gaze(
        n_frames=n_frames,
        mode=mode,
        pano_w=pano_w,
        pano_h=pano_h,
        crop_size=crop_size,
        fps=fps,
        px_per_deg=px_per_deg,
        seed=seed,
    )

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["frame_idx", "x", "y", "mode", "seed"])
        for i, (x, y) in enumerate(pts):
            writer.writerow([i, float(x), float(y), mode, seed])


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract quantified gaze stats and simulate gaze trajectories.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_extract = sub.add_parser("extract", help="Extract summary stats from Michaiel et al. .mat dataset.")
    p_extract.add_argument(
        "--mat",
        type=Path,
        default=Path(__file__).resolve().parent / "Michaiel_et_al.2020_fullDataset.mat",
    )
    p_extract.add_argument(
        "--out",
        type=Path,
        default=Path(__file__).resolve().parent / "derived" / "gaze_summary.json",
    )
    p_extract.add_argument("--fps", type=int, default=60)
    p_extract.add_argument("--run-thresh-cm-s", type=float, default=10.0)

    p_sim = sub.add_parser("simulate", help="Simulate gaze trajectory to CSV using mode-based generator.")
    p_sim.add_argument("--out", type=Path, required=True)
    p_sim.add_argument("--mode", choices=["stationary", "running", "approach", "nonapproach"], required=True)
    p_sim.add_argument("--n-frames", type=int, default=180)
    p_sim.add_argument("--pano-w", type=int, default=4433)
    p_sim.add_argument("--pano-h", type=int, default=1110)
    p_sim.add_argument("--crop-size", type=int, default=577)
    p_sim.add_argument("--fps", type=int, default=30)
    p_sim.add_argument("--px-per-deg", type=int, default=35)
    p_sim.add_argument("--seed", type=int, default=0)

    args = parser.parse_args()
    if args.cmd == "extract":
        summary = extract_summary(args.mat, fps=args.fps, run_thresh_cm_s=args.run_thresh_cm_s)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)
        print(f"Wrote: {args.out}")
        return

    simulate_to_csv(
        output_csv=args.out,
        n_frames=args.n_frames,
        mode=args.mode,
        pano_w=args.pano_w,
        pano_h=args.pano_h,
        crop_size=args.crop_size,
        fps=args.fps,
        px_per_deg=args.px_per_deg,
        seed=args.seed,
    )
    print(f"Wrote: {args.out}")


if __name__ == "__main__":
    main()
