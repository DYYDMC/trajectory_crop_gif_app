from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np


@dataclass
class MichaielParams:
    mode: str
    fps_data: int
    fps_generate: int
    fixation_median_frames: float
    fixation_sigma: float
    alpha: float
    beta: float
    emax_deg: float
    sigma_vx_deg_per_frame: float
    sigma_vy_deg_per_frame: float
    jitter_x_deg: float
    jitter_y_deg: float
    saccade_amp_median_deg: float
    saccade_amp_sigma: float
    vertical_coupling: float
    saccade_threshold_deg_per_frame: float
    running_threshold_cm_s: float


def _interp_nan_1d(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=float).ravel()
    if x.size == 0:
        return x
    idx = np.arange(x.size)
    valid = np.isfinite(x)
    if not np.any(valid):
        return np.zeros_like(x)
    if np.sum(valid) == 1:
        return np.full_like(x, float(x[valid][0]))
    return np.interp(idx, idx[valid], x[valid])


def _robust_std(x: np.ndarray) -> float:
    x = np.asarray(x, dtype=float).ravel()
    x = x[np.isfinite(x)]
    if x.size == 0:
        return 0.0
    med = np.median(x)
    mad = np.median(np.abs(x - med))
    return float(1.4826 * mad)


def _dominant_label(approach: np.ndarray, mouse_vel: np.ndarray, mode: str, run_thresh: float) -> bool:
    approach_frac = float(np.mean(approach > 0.5))
    vel = mouse_vel[np.isfinite(mouse_vel)]
    vel_med = float(np.median(vel)) if vel.size else 0.0
    if mode == "approach":
        return approach_frac >= 0.1
    if mode == "nonapproach":
        return approach_frac < 0.1
    if mode == "running":
        return vel_med >= run_thresh
    if mode == "stationary":
        return vel_med < run_thresh
    raise ValueError(f"Unknown mode: {mode}")


def fit_michaiel_params_from_mat(
    mat_path: str | Path,
    mode: str,
    fps_data: int = 60,
    fps_generate: int = 30,
    saccade_threshold_deg_per_frame: float = 5.0,
    running_threshold_cm_s: float = 10.0,
) -> MichaielParams:
    try:
        import scipy.io as sio
    except ImportError as exc:
        raise RuntimeError("scipy is required to fit Michaiel parameters from .mat") from exc

    m = sio.loadmat(Path(mat_path), squeeze_me=True, struct_as_record=False)
    theta_l_cell = np.ravel(m["thetaL"])
    theta_r_cell = np.ravel(m["thetaR"])
    phi_l_cell = np.ravel(m["phiL"])
    phi_r_cell = np.ravel(m["phiR"])
    head_theta_cell = np.ravel(m["headTheta"])
    approach_cell = np.ravel(m["approachEpochs"])
    mouse_vel_cell = np.ravel(m["mouseVel"])

    fixation_lengths = []
    dhead_fix = []
    deye_fix = []
    eye_yaw_fix = []
    eye_pitch_fix = []
    saccade_amps = []
    vertical_coupling_vals = []

    for i in range(len(theta_l_cell)):
        theta_l = _interp_nan_1d(np.asarray(theta_l_cell[i], dtype=float))
        theta_r = _interp_nan_1d(np.asarray(theta_r_cell[i], dtype=float))
        phi_l = _interp_nan_1d(np.asarray(phi_l_cell[i], dtype=float))
        phi_r = _interp_nan_1d(np.asarray(phi_r_cell[i], dtype=float))
        head_yaw = _interp_nan_1d(np.asarray(head_theta_cell[i], dtype=float))
        app = _interp_nan_1d(np.asarray(approach_cell[i], dtype=float))
        vel = _interp_nan_1d(np.asarray(mouse_vel_cell[i], dtype=float))

        n = min(len(theta_l), len(theta_r), len(phi_l), len(phi_r), len(head_yaw), len(app), len(vel))
        if n < 10:
            continue
        theta_l = theta_l[:n]
        theta_r = theta_r[:n]
        phi_l = phi_l[:n]
        phi_r = phi_r[:n]
        head_yaw = head_yaw[:n]
        app = app[:n]
        vel = vel[:n]

        if not _dominant_label(app, vel, mode, running_threshold_cm_s):
            continue

        eye_yaw = 0.5 * (theta_l + theta_r)
        eye_pitch = 0.5 * (phi_l + phi_r)
        deye = np.diff(eye_yaw, prepend=eye_yaw[0])
        dhead = np.diff(head_yaw, prepend=head_yaw[0])
        gaze_vel = np.abs(deye + dhead)
        sacc = gaze_vel > saccade_threshold_deg_per_frame
        fix = ~sacc

        starts = np.where((sacc[1:]) & (~sacc[:-1]))[0] + 1
        if sacc[0]:
            starts = np.r_[0, starts]
        ends = np.where((~sacc[1:]) & (sacc[:-1]))[0] + 1
        if sacc[-1]:
            ends = np.r_[ends, n]

        if len(starts) > 0 and len(ends) > 0:
            for e, s in zip(ends[:-1], starts[1:]):
                d = s - e
                if d > 0:
                    fixation_lengths.append(d)
            for s0, e0 in zip(starts, ends):
                if e0 - s0 <= 0:
                    continue
                amp = float(np.sum(np.abs(deye[s0:e0] + dhead[s0:e0])))
                saccade_amps.append(amp)
                dx = float(np.sum(dhead[s0:e0]))
                dy = float(np.sum(np.diff(eye_pitch[s0:e0], prepend=eye_pitch[s0])))
                if np.abs(dx) > 1e-6:
                    vertical_coupling_vals.append(dy / dx)

        dhead_fix.extend(dhead[fix].tolist())
        deye_fix.extend(deye[fix].tolist())
        eye_yaw_fix.extend(eye_yaw[fix].tolist())
        eye_pitch_fix.extend(eye_pitch[fix].tolist())

    if not fixation_lengths:
        raise RuntimeError(f"No usable trials for mode={mode}; check threshold/mode filters.")

    fix_arr = np.asarray(fixation_lengths, dtype=float)
    fix_arr = fix_arr[fix_arr > 0]
    log_fix = np.log(fix_arr)
    fixation_median_frames = float(np.median(fix_arr))
    fixation_sigma = float(np.std(log_fix))

    dhead_fix = np.asarray(dhead_fix, dtype=float)
    deye_fix = np.asarray(deye_fix, dtype=float)
    if dhead_fix.size and np.any(np.abs(dhead_fix) > 1e-8):
        alpha = float(np.clip(-np.cov(deye_fix, dhead_fix)[0, 1] / (np.var(dhead_fix) + 1e-8), 0.2, 1.2))
    else:
        alpha = 0.8

    beta = 0.9 if mode in ("approach", "running") else 0.85
    emax_deg = float(np.quantile(np.abs(np.asarray(eye_yaw_fix, dtype=float)), 0.995)) if eye_yaw_fix else 12.0

    sigma_vx = _robust_std(dhead_fix)
    sigma_vy = _robust_std(np.diff(np.asarray(eye_pitch_fix), prepend=eye_pitch_fix[0])) if eye_pitch_fix else sigma_vx * 0.5
    jitter_x = _robust_std(deye_fix)
    jitter_y = _robust_std(np.diff(np.asarray(eye_pitch_fix), prepend=eye_pitch_fix[0])) if eye_pitch_fix else jitter_x * 0.5

    saccade_amps = np.asarray(saccade_amps, dtype=float)
    saccade_amps = saccade_amps[saccade_amps > 0]
    if saccade_amps.size:
        saccade_amp_median = float(np.median(saccade_amps))
        saccade_amp_sigma = float(np.std(np.log(saccade_amps)))
    else:
        saccade_amp_median = 6.0
        saccade_amp_sigma = 0.5

    vertical_coupling = float(np.clip(np.median(vertical_coupling_vals), -1.0, 1.0)) if vertical_coupling_vals else 0.2

    scale = fps_data / max(1, fps_generate)
    return MichaielParams(
        mode=mode,
        fps_data=fps_data,
        fps_generate=fps_generate,
        fixation_median_frames=fixation_median_frames / scale,
        fixation_sigma=max(0.05, fixation_sigma),
        alpha=alpha,
        beta=beta,
        emax_deg=max(3.0, emax_deg),
        sigma_vx_deg_per_frame=max(0.1, sigma_vx / scale),
        sigma_vy_deg_per_frame=max(0.1, sigma_vy / scale),
        jitter_x_deg=max(0.05, jitter_x / scale),
        jitter_y_deg=max(0.05, jitter_y / scale),
        saccade_amp_median_deg=max(1.0, saccade_amp_median),
        saccade_amp_sigma=max(0.05, saccade_amp_sigma),
        vertical_coupling=vertical_coupling,
        saccade_threshold_deg_per_frame=saccade_threshold_deg_per_frame,
        running_threshold_cm_s=running_threshold_cm_s,
    )


def generate_gaze_michaiel(
    n_frames: int,
    params: MichaielParams,
    pano_w: int,
    pano_h: int,
    crop_size: int = 577,
    px_per_deg: float = 35.0,
    seed: int = 0,
) -> list[tuple[float, float]]:
    rng = np.random.default_rng(seed)
    half = crop_size // 2

    center_x = pano_w / 2.0
    center_y = pano_h / 2.0
    h = np.array([0.0, 0.0], dtype=float)  # deg
    e = np.array([0.0, 0.0], dtype=float)  # deg
    v = np.array([0.0, 0.0], dtype=float)  # deg/frame
    theta = 1.0 / max(1.0, 0.25 * params.fps_generate)

    out = []
    frame = 0
    while frame < n_frames:
        L = int(np.clip(rng.lognormal(np.log(max(1e-3, params.fixation_median_frames)), params.fixation_sigma), 2, 40))
        for _ in range(L):
            if frame >= n_frames:
                break
            h_prev = h.copy()
            noise = np.array(
                [
                    rng.normal(0, params.sigma_vx_deg_per_frame),
                    rng.normal(0, params.sigma_vy_deg_per_frame),
                ]
            )
            v = v * (1 - theta) + noise
            h += v
            if params.mode == "approach":
                h[1] += -0.02 * h[1]

            dh = h - h_prev
            e -= params.alpha * dh
            e = np.clip(e, -params.emax_deg, params.emax_deg)

            g = h + e
            g[0] += rng.normal(0, params.jitter_x_deg)
            g[1] += rng.normal(0, params.jitter_y_deg)

            x = center_x + g[0] * px_per_deg
            y = center_y + g[1] * px_per_deg
            x = float(np.clip(x, half, pano_w - half - 1))
            y = float(np.clip(y, half, pano_h - half - 1))
            out.append((x, y))
            frame += 1

        e *= (1 - params.beta)
        A = float(rng.lognormal(np.log(max(1e-3, params.saccade_amp_median_deg)), params.saccade_amp_sigma))
        direction = rng.choice([-1.0, 1.0])
        h[0] += direction * A
        h[1] += params.vertical_coupling * direction * A

    return out


def params_to_dict(params: MichaielParams) -> dict[str, Any]:
    return asdict(params)
