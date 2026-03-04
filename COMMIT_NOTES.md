# Commit Notes

This file tracks implementation explanations by commit hash for this repo.

## (next commit)
**Cache Michaiel fitted parameters to avoid repeated .mat refits**

What changed:
- Added in-memory cache for fitted Michaiel parameters keyed by mode/fps.
- Added persistent cache file:
1. `Michaiel_gaze_2020/derived/michaiel_fitted_params.json`
- Added lazy fit behavior:
1. first use of mode fits from `.mat`
2. subsequent uses load from cache (no refit)
- `Michaiel Fitted` generation now calls cache-backed parameter loader.

Why:
- Prevents repeated heavy `.mat` loading/fitting and reduces UI hangs/crash risk.

## (next commit)
**Wire `trajectory_generation_Michaiel.py` into app UI as `Michaiel Fitted` mode**

What changed:
- Added new button: `Michaiel Fitted`.
- Added mode selector dropdown (`approach`, `nonapproach`, `running`, `stationary`) before generation.
- Integrated fitted pipeline in app generation flow:
1. fit parameters from `.mat` via `fit_michaiel_params_from_mat(...)`
2. generate trajectory via `generate_gaze_michaiel(...)`
- Added metadata fields for this mode:
1. `michaiel_mode`
2. `michaiel_params` (fitted parameter snapshot)

Why:
- Enables direct in-app testing of data-fitted trajectory generation without replacing existing generators.

## (next commit)
**Add layman guide for fitted Michaiel generator usage (`HOW2MICHAIEL.md`)**

What changed:
- Added `HOW2MICHAIEL.md` with practical, copy-paste usage instructions for:
1. fitting parameters from `.mat`
2. generating trajectories
3. exporting CSV
4. interpreting output coordinates and timing

Why:
- Makes the new fitted trajectory workflow accessible without requiring code-level understanding.

## (next commit)
**Add new fitted-from-recording generator module (`trajectory_generation_Michaiel.py`)**

What changed:
- Added a separate module for a paper-oriented, data-fitted trajectory workflow without touching existing app logic.
- New parameter-fitting function:
1. `fit_michaiel_params_from_mat(...)`
2. infers fixation/saccade and noise-control parameters from `.mat` per mode (`approach`, `nonapproach`, `running`, `stationary`)
- New generator:
1. `generate_gaze_michaiel(...)`
2. uses fitted parameters to generate trajectories in degrees, converts to pixels, centers, clamps to crop-valid bounds.
- Added helper:
1. `params_to_dict(...)` for metadata/debug logging.

Why:
- Keeps current baseline generator unchanged while enabling a more realistic intermediate model that is grounded in recorded signals.

## (next commit)
**Replace recorded trial inputbox with annotated dropdown selector**

What changed:
- Replaced numeric inputbox for recorded trial selection with a modal dropdown.
- Dropdown options now show trial-level approach context from `approachEpochs`, e.g.:
1. `trial 087 | mixed | approach 23.4%`
2. `trial 012 | non-approach | approach 0.0%`
- Kept `Auto-select by seed` as the first option.

Why:
- Easier and safer trial selection with direct behavioral context visible in UI.

## 9a9da66
**Prompt seed and optional trial index for recorded-components mode**

What changed:
- Added two prompts when selecting `Recorded Components`:
1. deterministic `seed`
2. optional fixed `trial index` (`0-104`, cancel means auto-select by seed)
- Metadata now records both:
1. `recorded_trial_index` (actual selected trial)
2. `recorded_trial_index_override` (forced trial if provided)

Why:
- Makes recorded-components runs reproducible and controllable.

## 68b7084
**Add recorded-components trajectory mode from .mat body/head/eye signals**

What changed:
- Added new generated mode: `recorded_components`.
- Added `Recorded Components` button in app UI.
- Implemented trajectory generation from dataset components:
1. body heading from `mouse_xy`
2. head yaw from `headTheta`
3. eye yaw/pitch from `thetaL/thetaR` and `phiL/phiR`
- Combined gaze in degrees:
1. `gaze_yaw = body + head + eye_yaw`
2. `gaze_pitch = eye_pitch`
- Converted degrees to pixels with `px_per_deg`, centered trajectory in panorama, clamped to valid crop bounds.
- Stored selected trial index in metadata (`recorded_trial_index`).

Why:
- Moves from purely synthetic dynamics toward trajectories derived from recorded gaze components.

## 38c6c53
**Add Michaiel dataset extraction and gaze simulation CLI tool**

What changed:
- Added `Michaiel_gaze_2020/gaze_dataset_tools.py`.
- `extract` command:
1. reads `.mat`
2. summarizes approach/nonapproach gaze metrics
3. exports JSON
- `simulate` command:
1. runs mode-based gaze simulation
2. exports per-frame CSV trajectory

Why:
- Provides a reproducible analysis/simulation entrypoint for the dataset.

## c0364d2
**Save additional trajectory-only screenshot on accept**

What changed:
- Kept existing screenshot output intact.
- Added second screenshot output:
1. `image_with_trajectory_points.png` (trajectory + sampled points only, without crop boxes)
- Added this file to `trajectory_info.json -> saved_files`.

Why:
- Gives a clean visual of trajectory shape while preserving original annotated export.

## 834950b
**Auto-open crop size flow after generated trajectory selection**

What changed:
- After selecting generated trajectory mode, app immediately opens crop-size flow (`continue_with_params()`), instead of requiring hidden status text + manual `Continue`.

Why:
- Fixes usability issue when top status text is not visible due to crowded controls.

## 79d5b7d
**Fix generated mode being overwritten by incidental canvas click**

What changed:
- Removed forced `trajectory_mode = "manual"` on mouse-down.
- Set manual mode only after a valid drawn stroke is accepted.

Why:
- Prevents accidental mode reset that caused incorrect metadata logging (`trajectory_mode/manual` and null seed).

## bdd02d4
**Extract GIF/frame processing into gif_pipeline module**

What changed:
- Added `gif_pipeline.py` with:
1. `to_rgb_native`
2. `build_crop_frames`
3. `save_gif_from_frames`
- Refactored `app.py` to call these functions for preview generation and accept/save flow.

Why:
- Separates processing logic from UI/controller code and improves maintainability.

## 10ca8fe
**Refactor to unified gaze generator with 4 trajectory modes**

What changed:
- Added `trajectory_generation.py` with single `generate_gaze(...)` API.
- Unified generation modes into one path:
1. `approach`
2. `nonapproach`
3. `stationary`
4. `running`
- Removed duplicated per-mode generator code in `app.py`.

Why:
- Modularized overlapping trajectory logic and made future pattern additions simpler.

## dfb0230
**Add deterministic nonapproach trajectory mode**

What changed:
- Added `Nonapproach Trajectory` button and mode.
- Added deterministic nonapproach generator (seeded RNG).
- Wired mode into sampling/gif generation flow.

Why:
- Adds second deterministic behavior pattern beyond approach mode.

## 4170119
**Record approach trajectory seed in saved metadata**

What changed:
- Added `approach_seed` in accepted-run metadata when mode is `approach`.

Why:
- Ensures generated outputs can be exactly reproduced later.

## f27c4ce
**Add deterministic approach trajectory mode and UI button**

What changed:
- Added `Approach Trajectory` button and mode.
- Added deterministic approach trajectory generation with seeded RNG.
- Integrated generated mode into existing preview and save pipeline.

Why:
- Replaced hand-drawn dependency with reproducible deterministic trajectory generation.
