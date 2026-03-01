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

## Optional single-file app

You can package it with PyInstaller:

```bash
pip install pyinstaller
pyinstaller --noconfirm --onefile --windowed app.py
```
