"""Render the PWA icons (192 & 512 px) from the modular-synth icon source.

Reuses the 1024px renderer in ios/tools/make_icon.py and area-downsamples, so
the web app and the iOS app share one icon design. Outputs to web/icons/.

    python tools/make_icons.py        # run from web/
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
WEB = HERE.parent
REPO = WEB.parent
sys.path.insert(0, str(REPO / "ios" / "tools"))

import make_icon  # noqa: E402  (the iOS icon renderer)


def downscale(img: np.ndarray, target: int) -> np.ndarray:
    """Area-average downscale (summed-area table) to target x target."""
    src = img.astype(np.float64)
    h, w, _ = src.shape
    sat = np.zeros((h + 1, w + 1, 3))
    sat[1:, 1:] = np.cumsum(np.cumsum(src, axis=0), axis=1)
    out = np.zeros((target, target, 3))
    edges = np.linspace(0, h, target + 1).astype(int)
    for i in range(target):
        y0, y1 = edges[i], edges[i + 1]
        for j in range(target):
            x0, x1 = edges[j], edges[j + 1]
            area = max((y1 - y0) * (x1 - x0), 1)
            total = sat[y1, x1] - sat[y0, x1] - sat[y1, x0] + sat[y0, x0]
            out[i, j] = total / area
    return np.clip(out, 0, 255).astype(np.uint8)


def main() -> None:
    base = make_icon.render()  # 1024x1024 uint8
    (WEB / "icons").mkdir(parents=True, exist_ok=True)
    for size in (192, 512):
        make_icon.write_png(WEB / "icons" / f"icon-{size}.png",
                            downscale(base, size))
        print(f"Wrote web/icons/icon-{size}.png")


if __name__ == "__main__":
    main()
