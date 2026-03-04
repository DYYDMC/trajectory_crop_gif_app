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
