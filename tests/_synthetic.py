"""Builders for synthetic raw files (format A and B)."""
from __future__ import annotations

X_OFF = 50_000_000
Y_OFF = 60_000_000

# x: 0, 1000, 2000 (nx=3); y: 0, 5000 (ny=2)
GRID32 = (0, 2000, 1000, 0, 5000, 5000)

PIXELS = [
    (0, 0, [0, 5, 5, 7]),
    (1000, 0, []),  # acquired pixel with zero events
    (2000, 0, [0]),
    (0, 5000, []),
    (1000, 5000, [12]),
    (2000, 5000, [12, 12]),
]
N_EVENTS = 8
MAX_CHANNEL = 12


def stream_lines(pixels, *, dup_first_x=False, dangling_eof_x=None):
    """pixels: list of (x, y, [channels]).

    dup_first_x: emit an extra duplicate X header right after the first
    pixel's X header (defensive pattern, not observed in the two known files).
    dangling_eof_x: x of a trailing X header at EOF (observed in Ragazzo).
    """
    lines = []
    first = True
    for (x, y, chans) in pixels:
        lines.append(str(X_OFF + x))
        if first and dup_first_x:
            lines.append(str(X_OFF + x))
        first = False
        lines.append(str(Y_OFF + y))
        lines.extend(str(c) for c in chans)
    if dangling_eof_x is not None:
        lines.append(str(X_OFF + dangling_eof_x))
    return lines


def write_format_a(path, grid, pixels, *, m=1.5, q=-0.25, velocity=8000,
                   dup_first_x=False, dangling_eof_x=None):
    x_min, x_max, x_step, y_min, y_max, y_step = grid
    lines = [
        '<?xml version="1.2" encoding="UTF-8"?>',
        "<XRFanalysis>",
        "\t<calibration>",
        f'\t\t<calibration_keV/ch>"{m}"</calibration_keV/ch>',
        f'\t\t<calibration_Offset>"{q}"</calibration_Offset>',
        "\t</calibration>",
        "\t<analysisInfo>",
        *[f'\t\t<{k}>"{v}"</{k}>' for k, v in [
            ("Xmin", x_min), ("Xmax", x_max), ("Ymin", y_min), ("Ymax", y_max),
            ("Xstep", x_step), ("Ystep", y_step), ("Velocity", velocity)]],
        "\t</analysisInfo>",
        "\t<analysisData>",
    ]
    lines.extend(stream_lines(pixels, dup_first_x=dup_first_x,
                              dangling_eof_x=dangling_eof_x))
    lines.extend(["</analysisData>", "</XRFanalysis>", ""])
    path.write_text("\n".join(lines))


def write_format_b(path, pixels, *, dup_first_x=False, dangling_eof_x=None):
    lines = stream_lines(pixels, dup_first_x=dup_first_x,
                         dangling_eof_x=dangling_eof_x)
    lines.extend(["</analysisData>", "</XRFanalysis>", ""])
    path.write_text("\n".join(lines))
