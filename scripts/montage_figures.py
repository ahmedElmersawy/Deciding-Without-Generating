#!/usr/bin/env python3
"""Combine the 9 paper figures into one contact-sheet image (3x3 grid).

Usage:
    python3 scripts/montage_figures.py results/replay/mock-pilot/paper_figures
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image

FIGS = [
    "fig1_pareto_accuracy_latency.png",
    "fig2_accuracy_ci.png",
    "fig3_energy_per_decision.png",
    "fig4_accuracy_vs_energy.png",
    "fig5_consistency.png",
    "fig6_calibration.png",
    "fig7_latency_distribution.png",
    "fig8_error_breakdown.png",
    "fig9_radar_summary.png",
]

COLS, ROWS = 3, 3
CELL_W, CELL_H = 900, 700  # target cell size; each figure is letterboxed to fit
PAD = 16
BG = (252, 252, 251)


def fit(img: Image.Image, w: int, h: int) -> Image.Image:
    img = img.convert("RGB")
    scale = min(w / img.width, h / img.height)
    new = img.resize((int(img.width * scale), int(img.height * scale)), Image.LANCZOS)
    canvas = Image.new("RGB", (w, h), BG)
    canvas.paste(new, ((w - new.width) // 2, (h - new.height) // 2))
    return canvas


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("dir", type=Path)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    out = args.out or (args.dir / "all_figures_grid.png")
    sheet_w = COLS * CELL_W + (COLS + 1) * PAD
    sheet_h = ROWS * CELL_H + (ROWS + 1) * PAD
    sheet = Image.new("RGB", (sheet_w, sheet_h), BG)

    for i, name in enumerate(FIGS):
        path = args.dir / name
        cell = fit(Image.open(path), CELL_W, CELL_H)
        r, c = divmod(i, COLS)
        x = PAD + c * (CELL_W + PAD)
        y = PAD + r * (CELL_H + PAD)
        sheet.paste(cell, (x, y))

    sheet.save(out)
    print(f"==> wrote {out} ({sheet.width}x{sheet.height})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
