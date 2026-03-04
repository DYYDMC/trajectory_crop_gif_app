#!/usr/bin/env python3
import json
import time
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog

import numpy as np
from PIL import Image, ImageDraw, ImageTk
from gif_pipeline import build_crop_frames, save_gif_from_frames, to_rgb_native
from trajectory_generation import generate_gaze, generate_gaze_from_recorded_components


ALLOWED_EXTENSIONS = {".tif", ".tiff", ".png", ".jpg", ".jpeg"}
CANVAS_MAX_W = 900
CANVAS_MAX_H = 700
GIF_FPS = 30
GENERATED_TRAJECTORY_MODES = {"approach", "nonapproach", "stationary", "running", "recorded_components"}


class TrajectoryCropApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Trajectory Crop GIF App")
        self.root.geometry("1400x820")

        self.base_output_dir = Path(__file__).resolve().parent / "outputs"
        self.base_output_dir.mkdir(parents=True, exist_ok=True)

        self.image_path: Path | None = None
        self.original_image: Image.Image | None = None
        self.original_array_native: np.ndarray | None = None
        self.base_display_image: Image.Image | None = None
        self.display_image_tk: ImageTk.PhotoImage | None = None
        self.current_annotated_image: Image.Image | None = None
        self.current_annotated_tk: ImageTk.PhotoImage | None = None

        self.scale = 1.0
        self.offset_x = 0
        self.offset_y = 0

        self.drawing = False
        self.current_stroke: list[tuple[int, int]] = []
        self.trajectory: list[tuple[int, int]] = []
        self.sampled_trajectory: list[tuple[int, int]] = []
        self.preview_overlay_enabled = False
        self.trajectory_mode = "manual"
        self.generated_n_frames = 180
        self.trajectory_seed = 0
        self.recorded_trial_index: int | None = None

        self.crop_size: int | None = None
        self.sample_frequency: int | None = None
        self.gif_frames: list[ImageTk.PhotoImage] = []
        self.gif_frame_idx = 0
        self.gif_after_id: str | None = None
        self.latest_frames_unnormalized: np.ndarray | None = None
        self.latest_frames_normalized_u8: np.ndarray | None = None

        self._build_ui()
        self.prompt_image_selection()

    def _build_ui(self) -> None:
        top = tk.Frame(self.root)
        top.pack(fill=tk.X, padx=10, pady=8)

        tk.Button(top, text="Upload Image", command=self.prompt_image_selection).pack(side=tk.LEFT, padx=4)
        tk.Button(top, text="Redraw Trajectory", command=self.reset_trajectory).pack(side=tk.LEFT, padx=4)
        tk.Button(top, text="Approach Trajectory", command=self.use_approach_trajectory).pack(side=tk.LEFT, padx=4)
        tk.Button(top, text="Nonapproach Trajectory", command=self.use_nonapproach_trajectory).pack(side=tk.LEFT, padx=4)
        tk.Button(top, text="Stationary Trajectory", command=self.use_stationary_trajectory).pack(side=tk.LEFT, padx=4)
        tk.Button(top, text="Running Trajectory", command=self.use_running_trajectory).pack(side=tk.LEFT, padx=4)
        tk.Button(top, text="Recorded Components", command=self.use_recorded_components_trajectory).pack(side=tk.LEFT, padx=4)
        tk.Button(top, text="Continue", command=self.continue_with_params).pack(side=tk.LEFT, padx=4)
        tk.Button(top, text="Save Accept", command=self.accept_result).pack(side=tk.LEFT, padx=4)
        tk.Button(top, text="Change Something", command=self.change_something).pack(side=tk.LEFT, padx=4)

        self.status_var = tk.StringVar(value="Select an image to start.")
        tk.Label(top, textvariable=self.status_var, anchor="w").pack(side=tk.LEFT, fill=tk.X, expand=True, padx=12)

        content = tk.Frame(self.root)
        content.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        left = tk.LabelFrame(content, text="Image + Trajectory")
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))
        self.canvas = tk.Canvas(left, bg="black", width=900, height=700, highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<ButtonPress-1>", self.on_mouse_down)
        self.canvas.bind("<B1-Motion>", self.on_mouse_move)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)

        right = tk.LabelFrame(content, text="Generated GIF (30Hz)")
        right.pack(side=tk.LEFT, fill=tk.Y, expand=False, padx=(6, 0))

        # Keep a square viewport so crop GIF frames are never displayed squeezed.
        self.gif_viewport_size = 440
        gif_viewport = tk.Frame(right, width=self.gif_viewport_size, height=self.gif_viewport_size, bg="#1e1e1e")
        gif_viewport.pack(padx=8, pady=8)
        gif_viewport.pack_propagate(False)

        self.gif_label = tk.Label(gif_viewport, text="No GIF generated yet", bg="#1e1e1e", fg="white")
        self.gif_label.pack(fill=tk.BOTH, expand=True)

    def prompt_image_selection(self) -> None:
        filetypes = [
            ("Image files", "*.tif *.tiff *.png *.jpg *.jpeg"),
            ("TIFF", "*.tif *.tiff"),
            ("PNG", "*.png"),
            ("JPEG", "*.jpg *.jpeg"),
        ]
        path = filedialog.askopenfilename(title="Select image", filetypes=filetypes)
        if not path:
            if self.original_image is None:
                self.status_var.set("No image selected.")
            return

        p = Path(path)
        if p.suffix.lower() not in ALLOWED_EXTENSIONS:
            messagebox.showerror("Invalid file", "Allowed formats: .tiff, .png, .jpg")
            return

        try:
            with Image.open(p) as pil:
                self.original_array_native = np.array(pil.copy())
                display_pil = pil
                if display_pil.mode not in ("L", "RGB", "RGBA"):
                    display_pil = display_pil.convert("RGB")
                self.original_image = display_pil.copy()
            self.image_path = p
        except Exception as exc:
            messagebox.showerror("Load failed", f"Could not load image:\n{exc}")
            return

        self.reset_state_for_new_image()
        self.status_var.set("Image loaded. Draw one continuous line with left mouse button.")

    def reset_state_for_new_image(self) -> None:
        self.stop_gif_animation()
        self.gif_label.configure(image="", text="No GIF generated yet")
        self.gif_frames = []
        self.gif_frame_idx = 0
        self.crop_size = None
        self.sample_frequency = None
        self.latest_frames_unnormalized = None
        self.latest_frames_normalized_u8 = None
        self.reset_trajectory()
        self.refresh_display_image()

    def refresh_display_image(self) -> None:
        if self.original_image is None:
            return

        canvas_w = max(self.canvas.winfo_width(), 50)
        canvas_h = max(self.canvas.winfo_height(), 50)
        max_w = min(canvas_w, CANVAS_MAX_W)
        max_h = min(canvas_h, CANVAS_MAX_H)

        src_w, src_h = self.original_image.size
        self.scale = min(max_w / src_w, max_h / src_h)
        disp_w = max(1, int(src_w * self.scale))
        disp_h = max(1, int(src_h * self.scale))

        resized = self.original_image.resize((disp_w, disp_h), Image.Resampling.BILINEAR)
        self.base_display_image = resized.copy()
        self.offset_x = (canvas_w - disp_w) // 2
        self.offset_y = (canvas_h - disp_h) // 2

        self.redraw_annotated_image()

    def redraw_annotated_image(self) -> None:
        if self.base_display_image is None:
            return

        annotated = self.base_display_image.copy()
        draw = ImageDraw.Draw(annotated)

        if len(self.trajectory) >= 2:
            draw.line(self.trajectory, fill=(255, 0, 0), width=2)
        if len(self.current_stroke) >= 2:
            draw.line(self.current_stroke, fill=(255, 255, 255), width=2)

        if self.preview_overlay_enabled and self.crop_size is not None and self.sampled_trajectory:
            self._draw_sampling_preview(draw)

        self.current_annotated_image = annotated
        self.current_annotated_tk = ImageTk.PhotoImage(annotated)

        self.canvas.delete("all")
        self.canvas.create_image(self.offset_x, self.offset_y, anchor="nw", image=self.current_annotated_tk)
        self.canvas.create_text(
            10,
            10,
            anchor="nw",
            text="Hold left mouse button and draw a single stroke",
            fill="white",
            font=("Helvetica", 12, "bold"),
        )

    def on_mouse_down(self, event: tk.Event) -> None:
        if self.base_display_image is None:
            return
        if not self._point_inside_image(event.x, event.y):
            return

        self.drawing = True
        self.current_stroke = [(event.x - self.offset_x, event.y - self.offset_y)]
        self.status_var.set("Drawing trajectory...")

    def on_mouse_move(self, event: tk.Event) -> None:
        if not self.drawing or self.base_display_image is None:
            return
        if not self._point_inside_image(event.x, event.y):
            return

        self.current_stroke.append((event.x - self.offset_x, event.y - self.offset_y))
        self.redraw_annotated_image()

    def on_mouse_up(self, event: tk.Event) -> None:
        if not self.drawing:
            return

        self.drawing = False
        if len(self.current_stroke) < 2:
            self.current_stroke = []
            self.status_var.set("Trajectory too short. Draw again.")
            self.redraw_annotated_image()
            return

        self.trajectory = self.current_stroke[:]
        self.trajectory_mode = "manual"
        self.current_stroke = []
        self.redraw_annotated_image()

        keep = messagebox.askyesno("Trajectory fixed", "Continue with this trajectory?\nYes = Continue, No = Redraw")
        if keep:
            self.status_var.set("Trajectory fixed. Click Continue to set crop parameters.")
        else:
            self.reset_trajectory()
            self.status_var.set("Trajectory cleared. Draw again.")

    def reset_trajectory(self) -> None:
        self.trajectory_mode = "manual"
        self.drawing = False
        self.current_stroke = []
        self.trajectory = []
        self.sampled_trajectory = []
        self.preview_overlay_enabled = False
        self.redraw_annotated_image()

    def use_approach_trajectory(self) -> None:
        self._select_generated_trajectory_mode("approach", "Approach")

    def use_nonapproach_trajectory(self) -> None:
        self._select_generated_trajectory_mode("nonapproach", "Nonapproach")

    def use_stationary_trajectory(self) -> None:
        self._select_generated_trajectory_mode("stationary", "Stationary")

    def use_running_trajectory(self) -> None:
        self._select_generated_trajectory_mode("running", "Running")

    def use_recorded_components_trajectory(self) -> None:
        self._select_generated_trajectory_mode("recorded_components", "Recorded Components")

    def _select_generated_trajectory_mode(self, mode: str, label: str) -> None:
        if self.original_image is None:
            messagebox.showerror("No image", "Please upload an image first.")
            return

        n_frames = simpledialog.askinteger(
            f"{label} trajectory",
            f"Enter number of frames for {label.lower()} trajectory:",
            initialvalue=self.generated_n_frames,
            minvalue=1,
            parent=self.root,
        )
        if n_frames is None:
            return

        self.generated_n_frames = int(n_frames)
        self.trajectory_mode = mode
        self.recorded_trial_index = None
        self.drawing = False
        self.current_stroke = []
        self.trajectory = []
        self.sampled_trajectory = []
        self.preview_overlay_enabled = False
        self.redraw_annotated_image()
        self.status_var.set(f"{label} trajectory selected. Setting crop parameters...")
        self.continue_with_params()

    def continue_with_params(self) -> None:
        if self.original_image is None:
            messagebox.showerror("No image", "Please upload an image first.")
            return
        if self.trajectory_mode == "manual" and len(self.trajectory) < 2:
            messagebox.showerror("No trajectory", "Please draw a trajectory first.")
            return

        crop_size = simpledialog.askinteger("Crop size", "Enter crop size (pixels, e.g. 64):", minvalue=2, parent=self.root)
        if crop_size is None:
            return

        self.crop_size = int(crop_size)
        if self.trajectory_mode in GENERATED_TRAJECTORY_MODES:
            self.sample_frequency = 1
        else:
            sample_freq = simpledialog.askinteger(
                "Sample frequency",
                "Enter sampling frequency along the trajectory (every N points):",
                minvalue=1,
                parent=self.root,
            )
            if sample_freq is None:
                return
            self.sample_frequency = int(sample_freq)
        self.compute_sampled_points()
        self.preview_overlay_enabled = True
        self.redraw_annotated_image()
        self.generate_gif_preview()

    def generate_gif_preview(self) -> None:
        assert self.original_image is not None
        assert self.original_array_native is not None
        assert self.crop_size is not None
        assert self.sample_frequency is not None

        src = self.original_array_native

        self.compute_sampled_points()
        sampled_disp = self.sampled_trajectory

        try:
            src_native = to_rgb_native(src)
            frames_native, frames_uint8 = build_crop_frames(
                src_native=src_native,
                sampled_disp=sampled_disp,
                scale=self.scale,
                crop_size=self.crop_size,
            )
        except ValueError as exc:
            title = "Unsupported image" if "Unsupported image array shape" in str(exc) else "No frames"
            messagebox.showerror(title, str(exc))
            return

        self.latest_frames_unnormalized = frames_native
        self.latest_frames_normalized_u8 = frames_uint8

        ts = time.strftime("%Y%m%d_%H%M%S")
        run_dir = self.base_output_dir / f"run_{ts}"
        run_dir.mkdir(parents=True, exist_ok=True)
        gif_path = run_dir / "preview.gif"
        save_gif_from_frames(frames_uint8, gif_path, GIF_FPS)

        self.load_and_play_gif(gif_path)
        self.status_var.set("GIF generated. Review and choose Accept or Change Something.")

    def load_and_play_gif(self, gif_path: Path) -> None:
        self.stop_gif_animation()
        pil_gif = Image.open(gif_path)
        frames = []
        try:
            idx = 0
            while True:
                pil_gif.seek(idx)
                frame = pil_gif.convert("RGB").resize(
                    (self.gif_viewport_size, self.gif_viewport_size), Image.Resampling.NEAREST
                )
                frames.append(ImageTk.PhotoImage(frame))
                idx += 1
        except EOFError:
            pass

        if not frames:
            return

        self.gif_frames = frames
        self.gif_frame_idx = 0
        self._tick_gif()

    def _tick_gif(self) -> None:
        if not self.gif_frames:
            return
        frame = self.gif_frames[self.gif_frame_idx]
        self.gif_label.configure(image=frame, text="")
        self.gif_frame_idx = (self.gif_frame_idx + 1) % len(self.gif_frames)
        self.gif_after_id = self.root.after(int(1000 / GIF_FPS), self._tick_gif)

    def stop_gif_animation(self) -> None:
        if self.gif_after_id is not None:
            self.root.after_cancel(self.gif_after_id)
            self.gif_after_id = None

    def accept_result(self) -> None:
        if self.original_image is None or self.image_path is None:
            messagebox.showerror("Missing data", "Please load an image first.")
            return
        if self.crop_size is None or self.sample_frequency is None:
            messagebox.showerror("Missing parameters", "Generate a GIF first, then accept.")
            return
        if len(self.trajectory) < 2 or len(self.sampled_trajectory) < 1:
            messagebox.showerror("Missing trajectory", "Trajectory data is missing.")
            return
        if self.latest_frames_unnormalized is None or self.latest_frames_normalized_u8 is None:
            messagebox.showerror("Missing frames", "No generated frame data found. Generate a GIF first.")
            return

        ts = time.strftime("%Y%m%d_%H%M%S")
        run_dir = self.base_output_dir / f"accepted_{ts}"
        run_dir.mkdir(parents=True, exist_ok=True)

        metadata = {
            "image_path": str(self.image_path),
            "trajectory_mode": self.trajectory_mode,
            "trajectory_seed": self.trajectory_seed if self.trajectory_mode in GENERATED_TRAJECTORY_MODES else None,
            "recorded_trial_index": self.recorded_trial_index if self.trajectory_mode == "recorded_components" else None,
            "crop_size": self.crop_size,
            "sample_frequency": self.sample_frequency,
            "display_scale": self.scale,
            "original_trajectory_image_coords": self._to_original_coords(self.trajectory),
            "sampled_trajectory_image_coords": self._to_original_coords(self.sampled_trajectory),
            "display_trajectory_coords": self.trajectory,
            "display_sampled_coords": self.sampled_trajectory,
            "timestamp": ts,
            "saved_files": {
                "preview_gif": "preview.gif",
                "frames_unnormalized_npy": "frames_unnormalized.npy",
                "frames_normalized_uint8_npy": "frames_normalized_uint8.npy",
                "annotated_image_png": "image_with_trajectory.png",
                "trajectory_points_image_png": "image_with_trajectory_points.png",
                "trajectory_info_json": "trajectory_info.json",
            },
        }

        json_path = run_dir / "trajectory_info.json"
        with json_path.open("w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        preview_gif_path = run_dir / "preview.gif"
        save_gif_from_frames(self.latest_frames_normalized_u8, preview_gif_path, GIF_FPS)

        np.save(run_dir / "frames_unnormalized.npy", self.latest_frames_unnormalized)
        np.save(run_dir / "frames_normalized_uint8.npy", self.latest_frames_normalized_u8)

        if self.current_annotated_image is not None:
            screenshot_path = run_dir / "image_with_trajectory.png"
            self.current_annotated_image.save(screenshot_path)
        if self.base_display_image is not None:
            points_only_path = run_dir / "image_with_trajectory_points.png"
            self._make_trajectory_points_image().save(points_only_path)

        messagebox.showinfo("Saved", f"Saved JSON and screenshot to:\n{run_dir}")
        self.status_var.set(f"Accepted and saved to {run_dir}")

    def change_something(self) -> None:
        dialog = tk.Toplevel(self.root)
        dialog.title("Change Something")
        dialog.geometry("380x220")
        dialog.transient(self.root)
        dialog.grab_set()

        tk.Label(dialog, text="What do you want to change?", font=("Helvetica", 12, "bold")).pack(pady=10)

        tk.Button(dialog, text="1) Change trajectory", width=30, command=lambda: self._handle_change(dialog, 1)).pack(pady=4)
        tk.Button(dialog, text="2) Change crop size", width=30, command=lambda: self._handle_change(dialog, 2)).pack(pady=4)
        tk.Button(dialog, text="3) Change sample frequency", width=30, command=lambda: self._handle_change(dialog, 3)).pack(pady=4)
        tk.Button(dialog, text="4) Upload another image", width=30, command=lambda: self._handle_change(dialog, 4)).pack(pady=4)

    def _handle_change(self, dialog: tk.Toplevel, choice: int) -> None:
        dialog.destroy()
        if choice == 1:
            self.reset_trajectory()
            self.status_var.set("Trajectory cleared. Draw a new one.")
            return
        if choice == 2:
            if self.crop_size is None:
                self.crop_size = 64
            new_size = simpledialog.askinteger(
                "Change crop size",
                "Enter new crop size:",
                initialvalue=self.crop_size,
                minvalue=2,
                parent=self.root,
            )
            if new_size is not None:
                self.crop_size = int(new_size)
                if self.sample_frequency is None:
                    self.sample_frequency = 1
                self.compute_sampled_points()
                self.preview_overlay_enabled = True
                self.redraw_annotated_image()
                self.generate_gif_preview()
            return
        if choice == 3:
            if self.sample_frequency is None:
                self.sample_frequency = 1
            new_freq = simpledialog.askinteger(
                "Change sample frequency",
                "Enter new sample frequency:",
                initialvalue=self.sample_frequency,
                minvalue=1,
                parent=self.root,
            )
            if new_freq is not None:
                self.sample_frequency = int(new_freq)
                if self.crop_size is None:
                    self.crop_size = 64
                self.compute_sampled_points()
                self.preview_overlay_enabled = True
                self.redraw_annotated_image()
                self.generate_gif_preview()
            return
        if choice == 4:
            self.prompt_image_selection()

    def _point_inside_image(self, canvas_x: int, canvas_y: int) -> bool:
        if self.base_display_image is None:
            return False
        w, h = self.base_display_image.size
        return self.offset_x <= canvas_x < self.offset_x + w and self.offset_y <= canvas_y < self.offset_y + h

    def _to_original_coords(self, pts: list[tuple[int, int]]) -> list[list[int]]:
        converted = []
        for x, y in pts:
            ox = int(round(x / self.scale))
            oy = int(round(y / self.scale))
            converted.append([ox, oy])
        return converted

    def compute_sampled_points(self) -> None:
        if self.trajectory_mode in GENERATED_TRAJECTORY_MODES:
            self._compute_generated_sampled_points()
            return
        if not self.trajectory:
            self.sampled_trajectory = []
            return
        if self.sample_frequency is None or self.sample_frequency < 1:
            self.sample_frequency = 1
        sampled_disp = self.trajectory[:: self.sample_frequency]
        if not sampled_disp:
            sampled_disp = [self.trajectory[0]]
        self.sampled_trajectory = sampled_disp

    def _compute_generated_sampled_points(self) -> None:
        if self.original_image is None or self.crop_size is None:
            self.sampled_trajectory = []
            self.trajectory = []
            return

        pano_w, pano_h = self.original_image.size
        if self.trajectory_mode == "recorded_components":
            mat_path = Path(__file__).resolve().parent / "Michaiel_gaze_2020" / "Michaiel_et_al.2020_fullDataset.mat"
            if not mat_path.exists():
                messagebox.showerror("Missing .mat", f"Expected dataset not found:\n{mat_path}")
                self.sampled_trajectory = []
                self.trajectory = []
                return
            try:
                sampled_orig, trial_idx = generate_gaze_from_recorded_components(
                    n_frames=self.generated_n_frames,
                    mat_path=mat_path,
                    pano_w=pano_w,
                    pano_h=pano_h,
                    crop_size=self.crop_size,
                    px_per_deg=35,
                    seed=self.trajectory_seed,
                )
                self.recorded_trial_index = trial_idx
            except Exception as exc:
                messagebox.showerror("Recorded trajectory failed", str(exc))
                self.sampled_trajectory = []
                self.trajectory = []
                return
        else:
            sampled_orig = generate_gaze(
                n_frames=self.generated_n_frames,
                mode=self.trajectory_mode,
                pano_w=pano_w,
                pano_h=pano_h,
                crop_size=self.crop_size,
                fps=GIF_FPS,
                px_per_deg=35,
                seed=self.trajectory_seed,
            )

        sampled_disp = []
        for ox, oy in sampled_orig:
            dx = int(round(ox * self.scale))
            dy = int(round(oy * self.scale))
            sampled_disp.append((dx, dy))

        self.sampled_trajectory = sampled_disp
        self.trajectory = sampled_disp[:]

    def _draw_sampling_preview(self, draw: ImageDraw.ImageDraw) -> None:
        assert self.crop_size is not None
        box_size_disp = max(1, int(round(self.crop_size * self.scale)))
        half = box_size_disp // 2

        for i, (x, y) in enumerate(self.sampled_trajectory):
            x0 = x - half
            y0 = y - half
            x1 = x0 + box_size_disp
            y1 = y0 + box_size_disp

            color = (255, 255, 0) if i == 0 else (255, 165, 0)
            draw.rectangle([x0, y0, x1, y1], outline=color, width=1)
            r = 2
            draw.ellipse([x - r, y - r, x + r, y + r], fill=color)

    def _make_trajectory_points_image(self) -> Image.Image:
        assert self.base_display_image is not None
        img = self.base_display_image.copy()
        draw = ImageDraw.Draw(img)

        if len(self.trajectory) >= 2:
            draw.line(self.trajectory, fill=(255, 0, 0), width=2)

        for i, (x, y) in enumerate(self.sampled_trajectory):
            color = (255, 255, 0) if i == 0 else (255, 165, 0)
            r = 3
            draw.ellipse([x - r, y - r, x + r, y + r], fill=color)

        return img


def main() -> None:
    root = tk.Tk()
    app = TrajectoryCropApp(root)
    root.bind("<Configure>", lambda _e: app.refresh_display_image() if app.original_image is not None else None)
    root.mainloop()


if __name__ == "__main__":
    main()
