# HOW2MICHAIEL

This guide explains how to use `trajectory_generation_Michaiel.py` in a practical way, without needing to read the full code.

## What This Module Does

`trajectory_generation_Michaiel.py` has two main steps:

1. Fit parameters from the real recorded dataset (`.mat`).
2. Generate a realistic trajectory using those fitted parameters.

So instead of hand-picking all trajectory constants, you estimate them from data first.

## What You Need

- File present:
  - `Michaiel_gaze_2020/Michaiel_et_al.2020_fullDataset.mat`
- Python packages:
  - `numpy`
  - `scipy`

## Quick Start (Copy/Paste)

Run this from repo root:

```bash
python3 - <<'PY'
from trajectory_generation_Michaiel import fit_michaiel_params_from_mat, generate_gaze_michaiel

mat = "Michaiel_gaze_2020/Michaiel_et_al.2020_fullDataset.mat"
mode = "approach"  # approach | nonapproach | running | stationary

params = fit_michaiel_params_from_mat(
    mat_path=mat,
    mode=mode,
    fps_data=60,
    fps_generate=30,
)

pts = generate_gaze_michaiel(
    n_frames=180,
    params=params,
    pano_w=4433,
    pano_h=1110,
    crop_size=577,
    px_per_deg=35,
    seed=0,
)

print("n_points:", len(pts))
print("first_5:", pts[:5])
print("last_5:", pts[-5:])
PY
```

## Save Trajectory to CSV

```bash
python3 - <<'PY'
import csv
from pathlib import Path
from trajectory_generation_Michaiel import fit_michaiel_params_from_mat, generate_gaze_michaiel

mat = "Michaiel_gaze_2020/Michaiel_et_al.2020_fullDataset.mat"
out = Path("Michaiel_gaze_2020/derived/michaiel_approach_seed0.csv")
out.parent.mkdir(parents=True, exist_ok=True)

params = fit_michaiel_params_from_mat(mat_path=mat, mode="approach")
pts = generate_gaze_michaiel(
    n_frames=180,
    params=params,
    pano_w=4433,
    pano_h=1110,
    crop_size=577,
    px_per_deg=35,
    seed=0,
)

with out.open("w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["frame_idx", "x", "y"])
    for i, (x, y) in enumerate(pts):
        w.writerow([i, x, y])

print(f"Wrote {out}")
PY
```

## How To Read The Output

Each trajectory point is `(x, y)` in panorama pixel coordinates.

- `x`: horizontal gaze center in pixels
- `y`: vertical gaze center in pixels
- one row ~= one frame in your generated sequence

If `fps_generate=30`, then:
- frame 0 -> 0 ms
- frame 1 -> 33.3 ms
- frame 30 -> 1 second

## Parameters You Will Most Often Change

- `mode`:
  - `approach`: approach-like behavior
  - `nonapproach`: non-approach behavior
  - `running`: faster movement profile
  - `stationary`: slower movement profile
- `n_frames`:
  - total trajectory length
- `seed`:
  - same seed -> same trajectory (reproducible)
- `px_per_deg`:
  - conversion from visual angle to pixels (controls movement amplitude on image)

## Reproducibility Tips

- Save these four values with your run:
  - `mode`
  - `seed`
  - `fps_generate`
  - `px_per_deg`
- If these match, your generated trajectory should match.

## Common Pitfalls

- No `scipy` installed:
  - fitting from `.mat` will fail
- Wrong path to `.mat`:
  - check file exists exactly at the given path
- Very different image/pano size:
  - same degree movement maps to different pixel movement

## Practical Validation Checklist

After generating, quickly check:

1. Trajectory stays inside valid crop bounds.
2. Motion looks plausible for selected mode.
3. Same seed repeats exactly.
4. Different seed changes trajectory shape but not overall style.

## Optional: Print Fitted Parameters

```bash
python3 - <<'PY'
from trajectory_generation_Michaiel import fit_michaiel_params_from_mat, params_to_dict

mat = "Michaiel_gaze_2020/Michaiel_et_al.2020_fullDataset.mat"
params = fit_michaiel_params_from_mat(mat_path=mat, mode="approach")
print(params_to_dict(params))
PY
```

This helps you inspect what was learned from the recording before generation.
