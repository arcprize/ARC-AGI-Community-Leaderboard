"""
DSL Primitives
==============
All pure functions on Grid / ObjSet / Color.
A Grid is List[List[int]].  0 is the conventional background.
An Object is a frozenset of (row, col) int pairs.
A BBox is (r0, c0, r1, c1) — inclusive on both ends.
A ColorMap is Dict[int, int].
"""

from __future__ import annotations

import copy
from collections import Counter
from typing import Dict, FrozenSet, List, Optional, Set, Tuple

# ── Type aliases ─────────────────────────────────────────────────────────────
Grid     = List[List[int]]
Object   = FrozenSet[Tuple[int, int]]
BBox     = Tuple[int, int, int, int]         # (r0, c0, r1, c1) inclusive
ColorMap = Dict[int, int]


# ── Grid constructors ─────────────────────────────────────────────────────────

def empty_grid(h: int, w: int, fill: int = 0) -> Grid:
    return [[fill] * w for _ in range(h)]

def copy_grid(g: Grid) -> Grid:
    return [row[:] for row in g]

def grid_size(g: Grid) -> Tuple[int, int]:
    return (len(g), len(g[0]) if g else 0)


# ── Geometric transforms ──────────────────────────────────────────────────────

def rotate(g: Grid, k: int = 1) -> Grid:
    """Rotate 90*k degrees clockwise."""
    k = k % 4
    for _ in range(k):
        g = [list(row) for row in zip(*g[::-1])]
    return g

def flip_h(g: Grid) -> Grid:
    """Flip horizontally (left ↔ right)."""
    return [row[::-1] for row in g]

def flip_v(g: Grid) -> Grid:
    """Flip vertically (top ↔ bottom)."""
    return g[::-1]

def flip_diag(g: Grid) -> Grid:
    """Transpose (flip along main diagonal)."""
    h, w = grid_size(g)
    return [[g[r][c] for r in range(h)] for c in range(w)]

def flip_antidiag(g: Grid) -> Grid:
    """Flip along anti-diagonal."""
    h, w = grid_size(g)
    return [[g[h - 1 - c][w - 1 - r] for r in range(h)] for c in range(w)]


# ── Crop / slice ──────────────────────────────────────────────────────────────

def crop(g: Grid, r0: int, c0: int, r1: int, c1: int) -> Grid:
    """Extract sub-grid [r0..r1, c0..c1] inclusive."""
    return [row[c0 : c1 + 1] for row in g[r0 : r1 + 1]]

def crop_bbox(g: Grid, bbox: BBox) -> Grid:
    return crop(g, *bbox)

def crop_to_content(g: Grid, bg: int = 0) -> Grid:
    """Crop away border rows/cols that are all bg."""
    h, w = grid_size(g)
    rows = [r for r in range(h) if any(g[r][c] != bg for c in range(w))]
    cols = [c for c in range(w) if any(g[r][c] != bg for r in range(h))]
    if not rows or not cols:
        return [[bg]]
    return crop(g, rows[0], cols[0], rows[-1], cols[-1])


# ── Concatenate ───────────────────────────────────────────────────────────────

def hstack(grids: List[Grid]) -> Grid:
    """Concatenate grids side-by-side (same height required)."""
    return [sum((g[r] for g in grids), []) for r in range(len(grids[0]))]

def vstack(grids: List[Grid]) -> Grid:
    """Stack grids vertically (same width required)."""
    return sum(grids, [])


# ── Paint / fill ──────────────────────────────────────────────────────────────

def paint(g: Grid, cells: Object, color: int) -> Grid:
    """Return new grid with given cells painted color."""
    g2 = copy_grid(g)
    for r, c in cells:
        g2[r][c] = color
    return g2

def paint_grid(base: Grid, overlay: Grid, skip: int = 0) -> Grid:
    """Overlay grid onto base, skipping cells equal to skip."""
    g2 = copy_grid(base)
    h, w = grid_size(overlay)
    for r in range(min(len(base), h)):
        for c in range(min(len(base[0]), w)):
            if overlay[r][c] != skip:
                g2[r][c] = overlay[r][c]
    return g2

def stamp(base: Grid, patch: Grid, r0: int, c0: int, skip: int = 0) -> Grid:
    """Stamp patch onto base at offset (r0, c0)."""
    g2 = copy_grid(base)
    for r in range(len(patch)):
        for c in range(len(patch[0])):
            nr, nc = r0 + r, c0 + c
            if 0 <= nr < len(base) and 0 <= nc < len(base[0]):
                if patch[r][c] != skip:
                    g2[nr][nc] = patch[r][c]
    return g2

def clear_grid(g: Grid, color: int = 0) -> Grid:
    h, w = grid_size(g)
    return [[color] * w for _ in range(h)]

def fill_grid(g: Grid, color: int) -> Grid:
    return [[color] * len(row) for row in g]


# ── Color operations ──────────────────────────────────────────────────────────

def background(g: Grid) -> int:
    """Most frequent color — conventionally the background."""
    flat = [c for row in g for c in row]
    return Counter(flat).most_common(1)[0][0]

def colors_in(g: Grid) -> Set[int]:
    return {c for row in g for c in row}

def color_histogram(g: Grid) -> Dict[int, int]:
    hist: Dict[int, int] = {}
    for row in g:
        for c in row:
            hist[c] = hist.get(c, 0) + 1
    return hist

def recolor(g: Grid, src: int, dst: int) -> Grid:
    return [[dst if c == src else c for c in row] for row in g]

def apply_color_map(g: Grid, cmap: ColorMap) -> Grid:
    return [[cmap.get(c, c) for c in row] for row in g]

def swap_colors(g: Grid, a: int, b: int) -> Grid:
    return apply_color_map(g, {a: b, b: a})


# ── Boolean grid ops ──────────────────────────────────────────────────────────

def grid_or(g1: Grid, g2: Grid, true_color: int = 1) -> Grid:
    h, w = grid_size(g1)
    return [[g1[r][c] or g2[r][c] for c in range(w)] for r in range(h)]

def grid_and(g1: Grid, g2: Grid) -> Grid:
    h, w = grid_size(g1)
    return [[g1[r][c] if g1[r][c] and g2[r][c] else 0 for c in range(w)] for r in range(h)]

def grid_xor(g1: Grid, g2: Grid) -> Grid:
    h, w = grid_size(g1)
    bg1, bg2 = background(g1), background(g2)
    return [
        [g1[r][c] if (g1[r][c] != bg1) != (g2[r][c] != bg2) else 0 for c in range(w)]
        for r in range(h)
    ]


# ── Tiling ────────────────────────────────────────────────────────────────────

def tile_grid(pattern: Grid, rows: int, cols: int) -> Grid:
    """Tile pattern to fill a (rows × cols)-cell region."""
    ph, pw = grid_size(pattern)
    out = empty_grid(rows, cols)
    for r in range(rows):
        for c in range(cols):
            out[r][c] = pattern[r % ph][c % pw]
    return out


# ── Object-level transforms ───────────────────────────────────────────────────

def translate_object(obj: Object, dr: int, dc: int) -> Object:
    return frozenset((r + dr, c + dc) for r, c in obj)

def object_cells(g: Grid, obj: Object) -> Dict[Tuple[int,int], int]:
    """Return {(r,c): color} for all cells in obj."""
    return {(r, c): g[r][c] for r, c in obj}

def object_to_grid(g: Grid, obj: Object, bg: int = 0) -> Grid:
    """Extract object as minimal bounding-box grid."""
    r0 = min(r for r, c in obj)
    c0 = min(c for r, c in obj)
    r1 = max(r for r, c in obj)
    c1 = max(c for r, c in obj)
    out = [[bg] * (c1 - c0 + 1) for _ in range(r1 - r0 + 1)]
    for r, c in obj:
        out[r - r0][c - c0] = g[r][c]
    return out

def scale_object(obj: Object, factor: int) -> Object:
    cells = set()
    for r, c in obj:
        for dr in range(factor):
            for dc in range(factor):
                cells.add((r * factor + dr, c * factor + dc))
    return frozenset(cells)


# ── Invariant checks ──────────────────────────────────────────────────────────

def grids_equal(g1: Grid, g2: Grid) -> bool:
    if len(g1) != len(g2) or (g1 and g2 and len(g1[0]) != len(g2[0])):
        return False
    return all(g1[r][c] == g2[r][c] for r in range(len(g1)) for c in range(len(g1[0])))

def output_size_matches(preds: Grid, target: Grid) -> bool:
    return len(preds) == len(target) and (
        not preds or not target or len(preds[0]) == len(target[0])
    )
