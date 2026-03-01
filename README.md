# Trajectory Crop GIF App

Lightweight cross-platform desktop app (Windows 11, macOS, Linux) for:

1. Loading `.tiff/.png/.jpg` image files.
2. Drawing one continuous mouse trajectory.
3. Sampling along that trajectory and cropping a moving window.
4. Normalizing each crop to `[0, 1]` by crop max and converting to `uint8`.
5. Building a 30 Hz replay GIF.
6. Accepting or changing trajectory/parameters.
7. Saving metadata JSON and screenshot on accept.

## Run

```bash
cd trajectory_crop_gif_app
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

## Output

Outputs are saved under:

```text
trajectory_crop_gif_app/outputs/
```

Each run creates a timestamped folder containing:

- `preview.gif` (when generated)
- `trajectory_info.json` (on accept)
- `image_with_trajectory.png` (on accept)

## Build native executable locally

Use PyInstaller through the provided build helper:

```bash
cd trajectory_crop_gif_app
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements-build.txt
python build.py
```

Build output is created under:

```text
trajectory_crop_gif_app/dist/<platform_arch>/
```

Notes:
- Windows builds must be produced on Windows.
- macOS builds must be produced on macOS.
- Linux builds must be produced on Linux.

## GitHub Actions cross-platform build

This repo includes a matrix workflow at:

`/.github/workflows/build-trajectory-crop-gif.yml`

It builds native binaries on:
- `windows-latest`
- `macos-latest`
- `ubuntu-latest`

Run it from the Actions tab (`workflow_dispatch`) and download artifacts for each OS.
