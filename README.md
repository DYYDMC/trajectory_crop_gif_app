# Trajectory Crop GIF App

A simple desktop tool to:

1. Open an image (`.tif/.tiff/.png/.jpg/.jpeg`)
2. Draw one continuous line with your mouse
3. Set crop size + sampling frequency
4. Generate a 30 Hz GIF from crops along the line
5. Save JSON metadata and an annotated screenshot

Works on macOS, Windows, and Linux.

## What You Need

- Python 3.10+ (3.11 recommended)
- A terminal (Terminal, iTerm, PowerShell, Command Prompt, etc.)

## 1) First-Time Setup (Run from Source)

Open a terminal and run:

```bash
cd /Users/dengyuyao/Github/trajectory_crop_gif_app
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Windows (PowerShell):

```powershell
cd C:\Users\dengyuyao\Github\trajectory_crop_gif_app
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Windows (Command Prompt):

```bat
cd C:\Users\dengyuyao\Github\trajectory_crop_gif_app
py -m venv .venv
.venv\Scripts\activate.bat
pip install -r requirements.txt
```

## 2) Launch the App

With the virtual environment active:

```bash
python app.py
```

## 3) Typical User Flow

1. The app asks you to choose an image file.
2. Hold left mouse button and draw one continuous trajectory.
3. Release mouse:
- Choose `Continue` to keep trajectory.
- Choose `Redraw` to draw again.
4. Enter:
- `Crop size` (pixels, e.g. `64`)
- `Sample frequency` (every `N` points, e.g. `3`)
5. Review:
- Overlay on image shows sampled points and crop-size boxes.
- GIF preview plays on the right.
6. Choose:
- `Save Accept`: save outputs.
- `Change Something`: edit trajectory / crop size / sampling / upload another image.

## 4) Where Files Are Saved

Output folders are created automatically under:

```text
trajectory_crop_gif_app/outputs/
```

Each run gets a timestamped folder containing some or all of:

- `preview.gif`
- `trajectory_info.json`
- `image_with_trajectory.png`

## 5) Build a Native Executable Locally

If you want a standalone app (no `python app.py` needed), build with PyInstaller:

```bash
cd /Users/dengyuyao/Github/trajectory_crop_gif_app
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-build.txt
python build.py
```

Build output goes to:

```text
dist/<platform_arch>/
```

Examples:
- macOS: `dist/darwin_arm64/TrajectoryCropGIF.app`
- Linux: `dist/linux_x86_64/TrajectoryCropGIF`
- Windows: `dist/windows_amd64/TrajectoryCropGIF.exe`

Important:
- Build on the same OS you target.
- Windows executables must be built on Windows.
- macOS apps must be built on macOS.
- Linux binaries must be built on Linux.

## 6) Quick Troubleshooting

- `python` or `python3` not found:
- Install Python from python.org and reopen terminal.
- On Windows, try `py` instead of `python`.

- Tkinter missing (usually Linux):
- Install system Tk package (example Ubuntu: `sudo apt-get install python3-tk`).

- Permission issues on macOS:
- If blocked on first run, right-click app and choose Open.

- GIF looks empty or dark:
- Check trajectory is on image area.
- Try smaller crop size or denser sampling (lower `N`).
