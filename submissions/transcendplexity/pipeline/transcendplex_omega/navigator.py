#!/usr/bin/env python3
"""
TranscendPlexity Omega — System 2 Navigator

3-Stream Bidirectional Vortex on a Toroidal Manifold:
  Stream 1 (Centripetal / Inward):  Rule extraction via compression
  Stream 2 (Centrifugal / Outward): Pattern projection / expansion
  Stream 3 (Braid / Transversal):   Cross-validation & generalization
  Stream 6 (Engram / Memory):       Associative pattern memory (pre-attention)

Integrates:
  - purple-clay periodic-boundary lattice & curvature
  - NGVT torus position encoding  (u,v) ∈ [0,2π]²
  - Gupta CCC scaling  G ~ c³ ~ h³ ~ k^(3/2)
  - ARC DSL operations from arc_solver.py
  - Engram associative memory (DeepSeek Engram, 2025)
"""
from __future__ import annotations

import numpy as np
from typing import List, Tuple, Optional, Dict, Callable
from collections import Counter, deque
from copy import deepcopy

from engram import EngramMemory

Grid = List[List[int]]
Point = Tuple[int, int]


# ---------------------------------------------------------------------------
# Toroidal Lattice  (from purple-clay core/lattice.py pattern)
# ---------------------------------------------------------------------------

class ToroidalLattice:
    """ARC grid mapped onto a torus with periodic boundary conditions."""

    def __init__(self, grid: Grid):
        self.grid = [row[:] for row in grid]
        self.H = len(grid)
        self.W = len(grid[0]) if grid else 0
        self.info_density = self._compute_info_density()

    # -- periodic neighbours (toroidal wrap) --------------------------------
    def adj4(self, r: int, c: int) -> List[Point]:
        return [((r + dr) % self.H, (c + dc) % self.W)
                for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]]

    def adj8(self, r: int, c: int) -> List[Point]:
        return [((r + dr) % self.H, (c + dc) % self.W)
                for dr in (-1, 0, 1) for dc in (-1, 0, 1)
                if (dr, dc) != (0, 0)]

    # -- information density  |ψ|² analog ----------------------------------
    def _compute_info_density(self) -> np.ndarray:
        arr = np.array(self.grid, dtype=float)
        return (arr != 0).astype(float)

    # -- discrete Laplacian curvature (purple-clay pattern) -----------------
    def local_curvature(self, r: int, c: int) -> float:
        center = self.info_density[r, c]
        nbr_sum = sum(self.info_density[nr, nc] for nr, nc in self.adj4(r, c))
        return nbr_sum - 4 * center

    # -- NGVT torus position encoding  (u,v) ∈ [0,2π]² --------------------
    @staticmethod
    def torus_encode(r: int, c: int, H: int, W: int) -> Tuple[float, float]:
        u = (r / H) * 2 * np.pi
        v = (c / W) * 2 * np.pi
        return u, v

    # -- toroidal distance --------------------------------------------------
    def torus_distance(self, p1: Point, p2: Point) -> float:
        dr = min(abs(p1[0] - p2[0]), self.H - abs(p1[0] - p2[0]))
        dc = min(abs(p1[1] - p2[1]), self.W - abs(p1[1] - p2[1]))
        return (dr * dr + dc * dc) ** 0.5


# ---------------------------------------------------------------------------
# DSL Operations  (extracted from arc_solver.py)
# ---------------------------------------------------------------------------

def _copy(g: Grid) -> Grid:
    return [row[:] for row in g]

def rotate_90(g: Grid) -> Grid:
    return [list(row) for row in zip(*g[::-1])]

def rotate_180(g: Grid) -> Grid:
    return [row[::-1] for row in g[::-1]]

def rotate_270(g: Grid) -> Grid:
    return [list(row) for row in zip(*g)][::-1]

def flip_h(g: Grid) -> Grid:
    return [row[::-1] for row in g]

def flip_v(g: Grid) -> Grid:
    return g[::-1]

def transpose(g: Grid) -> Grid:
    return [list(row) for row in zip(*g)]

def tile(g: Grid, h_tiles: int = 2, v_tiles: int = 2) -> Grid:
    result: Grid = []
    for _ in range(v_tiles):
        for row in g:
            result.append(row * h_tiles)
    return result

def scale_up(g: Grid, factor: int = 2) -> Grid:
    result: Grid = []
    for row in g:
        new_row = []
        for cell in row:
            new_row.extend([cell] * factor)
        for _ in range(factor):
            result.append(new_row[:])
    return result

def crop_to_nonzero(g: Grid) -> Grid:
    arr = np.array(g)
    rows = np.any(arr != 0, axis=1)
    cols = np.any(arr != 0, axis=0)
    if not rows.any():
        return g
    r_min, r_max = np.where(rows)[0][[0, -1]]
    c_min, c_max = np.where(cols)[0][[0, -1]]
    return [row[c_min:c_max + 1] for row in g[r_min:r_max + 1]]

def most_common_color(g: Grid, exclude_zero: bool = True) -> int:
    flat = [c for row in g for c in row if (not exclude_zero or c != 0)]
    if not flat:
        return 0
    return Counter(flat).most_common(1)[0][0]

def extract_objects(g: Grid, bg: int = 0) -> List[Tuple[set, int]]:
    """BFS connected-component extraction."""
    H, W = len(g), len(g[0])
    visited: set = set()
    objects: List[Tuple[set, int]] = []
    for r in range(H):
        for c in range(W):
            if (r, c) in visited or g[r][c] == bg:
                continue
            color = g[r][c]
            component: set = set()
            q = deque([(r, c)])
            visited.add((r, c))
            while q:
                cr, cc = q.popleft()
                component.add((cr, cc))
                for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nr, nc = cr + dr, cc + dc
                    if 0 <= nr < H and 0 <= nc < W and (nr, nc) not in visited and g[nr][nc] == color:
                        visited.add((nr, nc))
                        q.append((nr, nc))
            objects.append((component, color))
    return objects

# all single-grid transforms for the braid to test
TRANSFORMS: Dict[str, Callable[[Grid], Grid]] = {
    "identity":   lambda g: _copy(g),
    "rot90":      rotate_90,
    "rot180":     rotate_180,
    "rot270":     rotate_270,
    "flip_h":     flip_h,
    "flip_v":     flip_v,
    "transpose":  transpose,
    "crop":       crop_to_nonzero,
    "tile2x2":    lambda g: tile(g, 2, 2),
    "scale2":     lambda g: scale_up(g, 2),
    "scale3":     lambda g: scale_up(g, 3),
}


# ---------------------------------------------------------------------------
# CCC Scaling  (Gupta G ~ c³)
# ---------------------------------------------------------------------------

class CCCScaling:
    """Co-Varying Coupling Constants from Gupta's paper."""

    def __init__(self, c_variation: float = 1.065):
        self.c = c_variation
        self.G = c_variation ** 3        # G ~ c³
        self.h = c_variation ** 3        # h ~ c³  (same exponent)
        self.k = c_variation ** 1.5      # k ~ c^(3/2)

    def gravity_weight(self, distance: float) -> float:
        if distance < 1e-9:
            return 1.0
        return self.G / (distance * distance)


# ---------------------------------------------------------------------------
# 3-Stream Vortex Navigator  (the System 2 brain)
# ---------------------------------------------------------------------------

class TranscendPlexNavigator:
    """
    System 2: 3-stream bidirectional vortex on a toroidal manifold.

    The navigator tries multiple reasoning strategies in parallel:
      1. Direct transform matching  (try every DSL op)
      2. Color-mapping inference     (learn a pixel→pixel recolor)
      3. Centripetal gravity          (move objects toward seed)
      4. Flood-fill / boundary logic  (fill regions respecting walls)
    """

    def __init__(self, c_variation: float = 1.065):
        self.ccc = CCCScaling(c_variation)

    # -- public entry point -------------------------------------------------
    def solve(self, task: Dict, task_id: str = "") -> Optional[Grid]:
        """
        Attempt to solve an ARC task dict with keys 'train' and 'test'.
        Returns predicted output grid or None.
        """
        train = task.get("train", [])
        test_input = task.get("test", [{}])[0].get("input")
        if not train or test_input is None:
            return None

        pairs = [(p["input"], p["output"]) for p in train]

        # --- Stream 1: Centripetal (inward) — direct transform matching ---
        result = self._stream_transform_match(pairs, test_input)
        if result is not None:
            return result

        # --- Stream 2: Centrifugal (outward) — color mapping inference ---
        result = self._stream_color_mapping(pairs, test_input)
        if result is not None:
            return result

        # --- Stream 3: Braid (transversal) — flood-fill / gravity --------
        result = self._stream_gravity_fill(pairs, test_input)
        if result is not None:
            return result

        # --- Stream 4: Size-ratio scale detection -------------------------
        result = self._stream_size_ratio(pairs, test_input)
        if result is not None:
            return result

        # --- Stream 5: Bounding-box crop ----------------------------------
        result = self._stream_object_crop(pairs, test_input)
        if result is not None:
            return result

        # --- Stream 6: Engram associative memory --------------------------
        result = self._stream_engram(pairs, test_input)
        if result is not None:
            return result

        return None

    # -----------------------------------------------------------------------
    # Stream 4 — Size Ratio (detect consistent integer scale between I/O)
    # -----------------------------------------------------------------------
    def _stream_size_ratio(self, pairs: List[Tuple[Grid, Grid]],
                           test_in: Grid) -> Optional[Grid]:
        """Output = scale_up(input, k) or tile(input, k×k) for integer k ≥ 2."""
        if not pairs:
            return None
        scale = None
        for inp, out in pairs:
            if not inp or not out or not inp[0] or not out[0]:
                return None
            h_in, w_in = len(inp), len(inp[0])
            h_out, w_out = len(out), len(out[0])
            if h_out % h_in != 0 or w_out % w_in != 0:
                return None
            sh, sw = h_out // h_in, w_out // w_in
            if sh != sw:
                return None  # non-uniform scale
            if scale is None:
                scale = sh
            elif scale != sh:
                return None
        if scale is None or scale <= 1 or scale > 8:
            return None
        # try pixel-repeat scale
        fn_scale = lambda g: scale_up(g, scale)
        if all(fn_scale(inp) == out for inp, out in pairs):
            return fn_scale(test_in)
        # try tiling
        fn_tile = lambda g: tile(g, scale, scale)
        if all(fn_tile(inp) == out for inp, out in pairs):
            return fn_tile(test_in)
        return None

    # -----------------------------------------------------------------------
    # Stream 5 — Object Crop (output = bounding-box crop of non-bg content)
    # -----------------------------------------------------------------------
    def _stream_object_crop(self, pairs: List[Tuple[Grid, Grid]],
                            test_in: Grid) -> Optional[Grid]:
        """Output = bounding-box crop of all non-zero pixels in input."""
        if not pairs:
            return None
        for inp, out in pairs:
            if crop_to_nonzero(inp) != out:
                return None
        return crop_to_nonzero(test_in)

    # -----------------------------------------------------------------------
    # Stream 6 — Engram (associative pattern memory, pre-attention style)
    # -----------------------------------------------------------------------
    def _stream_engram(self, pairs: List[Tuple[Grid, Grid]],
                       test_in: Grid) -> Optional[Grid]:
        """Engram: query learned unigram/bigram/3×3-context tables.

        Only fires when same-shape, leave-one-out validation passes, and
        context coverage is sufficient — conservative by design so it never
        crowds out the exact streams above it.
        """
        try:
            return EngramMemory().solve(pairs, test_in)
        except Exception:
            return None

    # -- single-grid vortex (System 2 fallback) -----------------------------
    def solve_vortex(self, grid, task_id: str = ""):
        """8-stream centripetal vortex. Accepts list or numpy grid."""
        arr = np.array(grid) if not isinstance(grid, np.ndarray) else grid
        coords = np.argwhere(arr != 0)
        if coords.size == 0:
            return grid
        seed = np.median(coords, axis=0).astype(int)
        H, W = arr.shape
        output = np.zeros_like(arr)
        for (r, c), val in np.ndenumerate(arr):
            if val == 0:
                continue
            dr = (seed[0] - r + H // 2) % H - H // 2
            dc = (seed[1] - c + W // 2) % W - W // 2
            nr = (r + int(np.sign(dr))) % H
            nc = (c + int(np.sign(dc))) % W
            output[nr, nc] = val
        return output.tolist() if isinstance(grid, list) else output

    # -----------------------------------------------------------------------
    # Stream 1 — Transform Matching (Centripetal: compress to a rule)
    # -----------------------------------------------------------------------
    def _stream_transform_match(self, pairs: List[Tuple[Grid, Grid]],
                                test_in: Grid) -> Optional[Grid]:
        for name, fn in TRANSFORMS.items():
            if all(fn(inp) == out for inp, out in pairs):
                return fn(test_in)
        # try chained pairs (two transforms)
        for n1, f1 in TRANSFORMS.items():
            for n2, f2 in TRANSFORMS.items():
                chain = lambda g, _f1=f1, _f2=f2: _f2(_f1(g))
                if all(chain(inp) == out for inp, out in pairs):
                    return chain(test_in)
        return None

    # -----------------------------------------------------------------------
    # Stream 2 — Color Mapping (Centrifugal: project a recoloring rule)
    # -----------------------------------------------------------------------
    def _stream_color_mapping(self, pairs: List[Tuple[Grid, Grid]],
                              test_in: Grid) -> Optional[Grid]:
        # check if grids are same size and only colors differ
        for inp, out in pairs:
            if len(inp) != len(out) or len(inp[0]) != len(out[0]):
                return None

        # learn per-color mapping from first pair, verify on rest
        color_map: Dict[int, int] = {}
        inp0, out0 = pairs[0]
        for r in range(len(inp0)):
            for c in range(len(inp0[0])):
                src, dst = inp0[r][c], out0[r][c]
                if src in color_map:
                    if color_map[src] != dst:
                        return None
                else:
                    color_map[src] = dst

        # verify on remaining pairs
        for inp, out in pairs[1:]:
            for r in range(len(inp)):
                for c in range(len(inp[0])):
                    if color_map.get(inp[r][c]) != out[r][c]:
                        return None

        # apply to test
        return [[color_map.get(cell, cell) for cell in row] for row in test_in]

    # -----------------------------------------------------------------------
    # Stream 3 — Gravity / Flood-Fill (Braid: toroidal boundary logic)
    # -----------------------------------------------------------------------
    def _stream_gravity_fill(self, pairs: List[Tuple[Grid, Grid]],
                             test_in: Grid) -> Optional[Grid]:
        # try flood-fill from each non-bg color, stopping at walls
        inp0, out0 = pairs[0]
        # must be same dimensions
        if len(inp0) != len(out0) or len(inp0[0]) != len(out0[0]):
            return None
        bg = most_common_color(inp0, exclude_zero=False)

        lattice = ToroidalLattice(inp0)
        H, W = lattice.H, lattice.W
        # find seed colors (colors present in output but expanded vs input)
        seed_colors = set()
        for r in range(H):
            for c in range(W):
                if out0[r][c] != bg and inp0[r][c] == bg:
                    seed_colors.add(out0[r][c])

        if not seed_colors:
            return None

        # for each seed color, find its source pixels in input
        wall_color = None
        for color_val in range(10):
            if color_val != bg and color_val not in seed_colors:
                in_count = sum(1 for row in inp0 for c in row if c == color_val)
                out_count = sum(1 for row in out0 for c in row if c == color_val)
                if in_count > 0 and in_count == out_count:
                    wall_color = color_val
                    break

        # attempt flood-fill from seed pixels, blocked by wall_color
        def flood_fill_solve(grid_in: Grid, sc: int, wall: Optional[int]) -> Grid:
            g = _copy(grid_in)
            h, w = len(g), len(g[0])
            seeds = [(r, c) for r in range(h) for c in range(w) if g[r][c] == sc]
            visited: set = set(seeds)
            q = deque(seeds)
            while q:
                r, c = q.popleft()
                g[r][c] = sc
                for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < h and 0 <= nc < w and (nr, nc) not in visited:
                        if wall is not None and grid_in[nr][nc] == wall:
                            continue
                        visited.add((nr, nc))
                        q.append((nr, nc))
            return g

        # verify on all training pairs
        for sc in seed_colors:
            ok = True
            for inp, out in pairs:
                candidate = flood_fill_solve(inp, sc, wall_color)
                if candidate != out:
                    ok = False
                    break
            if ok:
                return flood_fill_solve(test_in, sc, wall_color)

        return None
