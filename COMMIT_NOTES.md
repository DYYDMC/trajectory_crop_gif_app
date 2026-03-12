# Commit Notes

This file tracks implementation explanations by commit hash for this repo.

## 4dad4d2
**Add cache-first loading for recorded-components trials**

What changed:
- Refactored `generate_gaze_from_recorded_components(...)` to load pre-extracted trial components from cache instead of parsing `.mat` on every call.
- Added recorded-components cache builder and loader utilities in `trajectory_generation.py`:
1. `build_recorded_components_cache(...)`
2. `_load_recorded_components_trials(...)`
3. `_extract_recorded_components_trials_from_mat(...)`
- Added versioned cache file path resolution:
1. `Michaiel_gaze_2020/derived/recorded_components_cache_v1.npz`
2. `RECORDED_COMPONENTS_CACHE_VERSION = 1`
- Added cache resilience behavior:
1. build once if cache is missing
2. auto-rebuild if cache is stale/corrupt/version-mismatched
3. then reload from cache
- Preserved trajectory output logic (same body/head/eye component fusion and gain application), with source of components switched to cache-first.

Why:
- Avoids repeated heavy `.mat` loading/interpolation for recorded-components mode, reducing latency and improving UI responsiveness for repeated runs.

## cb9f7ec
**Optimize dot overlay preview by using async in-memory rendering**

What changed:
- Reworked dot-overlay preview path to avoid disk roundtrip:
1. removed preview-time `save GIF -> reopen GIF -> decode`
2. now renders preview frames directly from in-memory NumPy arrays to `PhotoImage`
- Moved dot preview generation off the Tk main thread:
1. trajectory generation + overlay rendering run in a background worker thread
2. UI updates are applied via `root.after(...)`
3. added in-progress guard and job-id check to avoid stale preview writes
- Optimized dot rasterization with cached circular masks by radius:
1. precompute once per radius
2. reuse mask slices per frame/position
3. avoid per-frame circle-mask recomputation

Why:
- Removes the major UI freeze during `Configure Dot Overlay` by eliminating expensive synchronous GIF encode/decode and shifting heavy computation off the UI thread.

## ac8e01b
**Add configurable moving-dot overlay with secondary GIF preview**

What changed:
- Added a new post-processing dot-overlay stage on top of generated crop frames (`frames_normalized_uint8`), independent from the selected crop trajectory.
- Added dot overlay configuration in UI (`Configure Dot Overlay`) with parameters:
1. `size` in pixels (dot radius)
2. `intensity` (`uint8`, `0..255`)
3. independent dot trajectory mode + deterministic seed
- Reused existing trajectory generation logic family for dot motion:
1. `approach`
2. `nonapproach`
3. `stationary`
4. `running`
5. `recorded_components`
6. `michaiel_fitted`
- Added a second GIF preview viewport below the current preview to display dot-overlay result (`preview_with_dot.gif`).
- Added separate playback loop/state for the dot-overlay preview.
- Extended accept/save outputs when dot overlay is enabled:
1. `preview_with_dot.gif`
2. `frames_with_dot_uint8.npy`
3. `trajectory_info.json -> dot_overlay` metadata block (enabled, size, intensity, trajectory mode/seed, dot path)
- Added `Change Something -> Configure dot overlay` shortcut.

Why:
- Enables a final, independent visual marker layer without changing the base trajectory crop pipeline, while keeping outputs reproducible and reviewable in-app.

## (next commit)
**Add amplitude gain control for `Recorded Components` trajectories**

What changed:
- Added `gain` multiplier to recorded-components generator.
- Added UI prompt in `Recorded Components` flow to set gain (e.g. `0.1`, `0.2`, `0.5`, `1.0`).
- Applied gain to relative yaw/pitch movement before degree-to-pixel conversion.
- Saved selected gain in metadata as `recorded_components_gain`.

Why:
- Lets raw-data-derived trajectories be scaled down for smaller panoramas to reduce jumpiness while preserving motion pattern shape.

## (next commit)
**Pre-fit all four Michaiel modes in background and cache once**

What changed:
- `Michaiel Fitted` now performs one-time pre-fit for all behavior modes:
1. `approach`
2. `nonapproach`
3. `running`
4. `stationary`
- Pre-fit runs in a background thread with a modal progress dialog (UI stays responsive).
- Cached parameters are reused afterward (no repeated `.mat` refit when switching behavior).
- Cache remains persisted in:
1. `Michaiel_gaze_2020/derived/michaiel_fitted_params.json`

Why:
- Avoids repeated heavy fitting calls that caused freezes/not-responding crashes during mode switching.

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
