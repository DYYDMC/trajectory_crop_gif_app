import numpy as np


def generate_gaze(
    n_frames,
    mode,
    pano_w=4433,
    pano_h=1110,
    crop_size=577,
    fps=30,
    px_per_deg=35,
    seed=0,
):
    rng = np.random.default_rng(seed)
    half = crop_size // 2

    fixation_median_frames = 7
    fixation_sigma = 0.55

    if mode == "stationary":
        sigma_vx, sigma_vy = 2, 1
        jitter_x, jitter_y = 1, 0.5
        alpha = 0.9
        beta = 0.95
    elif mode == "running":
        sigma_vx, sigma_vy = 18, 6
        jitter_x, jitter_y = 5, 3
        alpha = 0.85
        beta = 0.95
    elif mode == "approach":
        sigma_vx, sigma_vy = 18, 4
        jitter_x, jitter_y = 4, 1.5
        alpha = 0.85
        beta = 0.95
    elif mode == "nonapproach":
        sigma_vx, sigma_vy = 20, 10
        jitter_x, jitter_y = 7, 5
        alpha = 0.75
        beta = 0.85
    else:
        raise ValueError(f"Unknown mode: {mode}")

    emax = 12 * px_per_deg
    tau = 0.25
    tau_frames = tau * fps
    theta = 1.0 / tau_frames

    center_x = pano_w / 2.0
    center_y = pano_h / 2.0
    h = np.array([center_x, center_y], dtype=float)
    e = np.array([0.0, 0.0])
    v = np.array([0.0, 0.0])

    sampled_disp = []
    frame = 0

    while frame < n_frames:
        L = int(np.clip(rng.lognormal(np.log(fixation_median_frames), fixation_sigma), 3, 20))

        for _ in range(L):
            if frame >= n_frames:
                break

            h_prev = h.copy()
            noise = np.array([rng.normal(0, sigma_vx), rng.normal(0, sigma_vy)])
            v = v * (1 - theta) + noise
            h += v

            if mode == "approach":
                h[1] += -0.02 * (h[1] - center_y)

            dh = h - h_prev
            e -= alpha * dh
            e = np.clip(e, -emax, emax)

            g = h + e
            g[0] += rng.normal(0, jitter_x)
            g[1] += rng.normal(0, jitter_y)
            g[0] = np.clip(g[0], half, pano_w - half - 1)
            g[1] = np.clip(g[1], half, pano_h - half - 1)

            sampled_disp.append((float(g[0]), float(g[1])))
            frame += 1

        e *= (1 - beta)
        A = rng.lognormal(np.log(6 * px_per_deg), 0.5)

        if mode == "approach":
            dx = rng.choice([-1, 1]) * A
            dy = 0.2 * dx
        elif mode == "stationary":
            dx = rng.normal(0, 0.3 * A)
            dy = rng.normal(0, 0.2 * A)
        else:
            dx = rng.choice([-1, 1]) * A
            dy = rng.normal(0, 0.5 * A)

        h[0] += dx
        h[1] += dy
        h[0] = np.clip(h[0], half, pano_w - half - 1)
        h[1] = np.clip(h[1], half, pano_h - half - 1)

    return sampled_disp


def _interp_nan_1d(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=float).ravel()
    n = x.size
    if n == 0:
        return x
    idx = np.arange(n)
    mask = np.isfinite(x)
    if not np.any(mask):
        return np.zeros_like(x)
    if np.sum(mask) == 1:
        return np.full_like(x, float(x[mask][0]))
    return np.interp(idx, idx[mask], x[mask])


def generate_gaze_from_recorded_components(
    n_frames,
    mat_path,
    pano_w,
    pano_h,
    crop_size=577,
    px_per_deg=35,
    seed=0,
    trial_index=None,
    gain=1.0,
):
    try:
        import scipy.io as sio
    except ImportError as exc:
        raise RuntimeError("scipy is required for recorded-components trajectory mode") from exc

    mat = sio.loadmat(mat_path, squeeze_me=True, struct_as_record=False)
    mouse_xy_cell = np.ravel(mat["mouse_xy"])
    head_theta_cell = np.ravel(mat["headTheta"])
    theta_l_cell = np.ravel(mat["thetaL"])
    theta_r_cell = np.ravel(mat["thetaR"])
    phi_l_cell = np.ravel(mat["phiL"])
    phi_r_cell = np.ravel(mat["phiR"])

    if trial_index is not None:
        if trial_index < 0 or trial_index >= len(mouse_xy_cell):
            raise ValueError(f"trial_index out of range: {trial_index} (valid: 0..{len(mouse_xy_cell)-1})")
        trial_order = np.array([int(trial_index)], dtype=int)
    else:
        rng = np.random.default_rng(seed)
        trial_order = rng.permutation(len(mouse_xy_cell))

    selected = None
    for t in trial_order:
        mxy = np.asarray(mouse_xy_cell[t], dtype=float)
        if mxy.ndim != 2 or mxy.shape[0] < 2:
            continue
        body_x = _interp_nan_1d(mxy[0])
        body_y = _interp_nan_1d(mxy[1])
        body_yaw = np.degrees(np.arctan2(np.diff(body_y, prepend=body_y[0]), np.diff(body_x, prepend=body_x[0])))
        head_yaw = _interp_nan_1d(np.asarray(head_theta_cell[t], dtype=float))
        eye_yaw = 0.5 * (
            _interp_nan_1d(np.asarray(theta_l_cell[t], dtype=float))
            + _interp_nan_1d(np.asarray(theta_r_cell[t], dtype=float))
        )
        eye_pitch = 0.5 * (
            _interp_nan_1d(np.asarray(phi_l_cell[t], dtype=float))
            + _interp_nan_1d(np.asarray(phi_r_cell[t], dtype=float))
        )
        lens = [len(body_yaw), len(head_yaw), len(eye_yaw), len(eye_pitch)]
        n = int(min(lens))
        if n >= max(5, n_frames):
            selected = (t, body_yaw[:n], head_yaw[:n], eye_yaw[:n], eye_pitch[:n])
            break

    if selected is None:
        raise RuntimeError("No valid trial found in .mat for recorded-components trajectory.")

    trial_idx, body_yaw, head_yaw, eye_yaw, eye_pitch = selected
    gaze_yaw_deg = body_yaw + head_yaw + eye_yaw
    gaze_pitch_deg = eye_pitch

    # Integrate relative to first frame to keep path centered in current panorama.
    yaw_rel = (gaze_yaw_deg - gaze_yaw_deg[0]) * float(gain)
    pitch_rel = (gaze_pitch_deg - gaze_pitch_deg[0]) * float(gain)

    half = crop_size // 2
    cx = pano_w / 2.0
    cy = pano_h / 2.0
    x = cx + yaw_rel * px_per_deg
    y = cy + pitch_rel * px_per_deg
    x = np.clip(x, half, pano_w - half - 1)
    y = np.clip(y, half, pano_h - half - 1)

    n_out = min(n_frames, x.size)
    points = [(float(x[i]), float(y[i])) for i in range(n_out)]
    return points, int(trial_idx)
