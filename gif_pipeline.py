from pathlib import Path

import imageio.v2 as imageio
import numpy as np


def to_rgb_native(src: np.ndarray) -> np.ndarray:
    if src.ndim == 2:
        return np.stack([src, src, src], axis=2)
    if src.ndim == 3 and src.shape[2] >= 3:
        return src[..., :3]
    if src.ndim == 3 and src.shape[2] == 2:
        return np.stack([src[..., 0], src[..., 0], src[..., 0]], axis=2)
    raise ValueError(f"Unsupported image array shape: {src.shape}")


def build_crop_frames(
    src_native: np.ndarray,
    sampled_disp: list[tuple[int, int]],
    scale: float,
    crop_size: int,
) -> tuple[np.ndarray, np.ndarray]:
    src_h, src_w, _ = src_native.shape
    half = crop_size // 2

    frames_native: list[np.ndarray] = []
    frames_uint8: list[np.ndarray] = []

    for dx, dy in sampled_disp:
        ox = int(round(dx / scale))
        oy = int(round(dy / scale))

        x0 = ox - half
        y0 = oy - half
        x1 = x0 + crop_size
        y1 = y0 + crop_size

        crop_native = np.zeros((crop_size, crop_size, 3), dtype=src_native.dtype)

        sx0 = max(0, x0)
        sy0 = max(0, y0)
        sx1 = min(src_w, x1)
        sy1 = min(src_h, y1)

        if sx1 > sx0 and sy1 > sy0:
            tx0 = sx0 - x0
            ty0 = sy0 - y0
            tx1 = tx0 + (sx1 - sx0)
            ty1 = ty0 + (sy1 - sy0)
            crop_native[ty0:ty1, tx0:tx1, :] = src_native[sy0:sy1, sx0:sx1, :]

        maxv = float(crop_native.max())
        if maxv > 0:
            crop_norm = crop_native.astype(np.float32) / maxv
        else:
            crop_norm = crop_native.astype(np.float32)
        crop_u8 = np.clip(crop_norm * 255.0, 0, 255).astype(np.uint8)

        frames_native.append(crop_native)
        frames_uint8.append(crop_u8)

    if not frames_uint8:
        raise ValueError("No frames could be generated from the sampled trajectory.")

    return np.stack(frames_native, axis=-1), np.stack(frames_uint8, axis=-1)


def save_gif_from_frames(frames_uint8: np.ndarray, output_path: Path, fps: int) -> None:
    num_frames = frames_uint8.shape[-1]
    frames_for_gif = [frames_uint8[..., i] for i in range(num_frames)]
    imageio.mimsave(output_path, frames_for_gif, duration=1.0 / fps, loop=0)
