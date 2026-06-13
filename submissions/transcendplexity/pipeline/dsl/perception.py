"""
DSL Perception Layer
====================
Reusable functions for extracting structure from grids:
  - connected-component object detection
  - bounding boxes, centroids, shape normalization
  - separator detection, region splitting
  - symmetry analysis
  - color chain / mapping extraction (abc82100-style)
"""

from __future__ import annotations

from collections import Counter, deque
from typing import Dict, FrozenSet, List, Optional, Set, Tuple

from dsl.primitives import Grid, Object, BBox, background, color_histogram

# ── Object detection ──────────────────────────────────────────────────────────

def find_objects(
    g: Grid,
    include: Optional[Set[int]] = None,
    exclude: Optional[Set[int]] = None,
    connectivity: int = 4,
) -> List[Object]:
    """
    Connected-component labeling.

    Args:
        include:  only consider cells with these colors (None = all non-zero)
        exclude:  skip cells with these colors (applied after include)
        connectivity: 4 (orthogonal) or 8 (includes diagonals)
    """
    h, w = len(g), len(g[0])
    excl = set(exclude) if exclude else {0}
    if include is not None:
        excl = excl | (set(range(10)) - set(include))

    visited: List[List[bool]] = [[False] * w for _ in range(h)]
    objects: List[Object] = []

    if connectivity == 8:
        deltas = [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]
    else:
        deltas = [(-1,0),(1,0),(0,-1),(0,1)]

    for sr in range(h):
        for sc in range(w):
            if visited[sr][sc] or g[sr][sc] in excl:
                continue
            # BFS
            cells: Set[Tuple[int,int]] = set()
            q: deque = deque([(sr, sc)])
            visited[sr][sc] = True
            while q:
                r, c = q.popleft()
                cells.add((r, c))
                for dr, dc in deltas:
                    nr, nc = r + dr, c + dc
                    if (0 <= nr < h and 0 <= nc < w
                            and not visited[nr][nc]
                            and g[nr][nc] not in excl):
                        visited[nr][nc] = True
                        q.append((nr, nc))
            objects.append(frozenset(cells))
    return objects


def find_objects_of_color(g: Grid, color: int, connectivity: int = 4) -> List[Object]:
    return find_objects(g, include={color}, exclude=set(), connectivity=connectivity)


def find_objects_excluding(g: Grid, excluded: Set[int], connectivity: int = 4) -> List[Object]:
    return find_objects(g, exclude=excluded, connectivity=connectivity)


# ── Bounding box / geometry ────────────────────────────────────────────────────

def bounding_box(obj: Object) -> BBox:
    """(r0, c0, r1, c1) inclusive."""
    rows = [r for r, c in obj]
    cols = [c for r, c in obj]
    return (min(rows), min(cols), max(rows), max(cols))

def centroid(obj: Object) -> Tuple[float, float]:
    return (sum(r for r, c in obj) / len(obj),
            sum(c for r, c in obj) / len(obj))

def dist_sq(p1: Tuple[float,float], p2: Tuple[float,float]) -> float:
    return (p1[0]-p2[0])**2 + (p1[1]-p2[1])**2

def normalize_shape(obj: Object) -> FrozenSet[Tuple[int,int]]:
    """Translate object so its minimum row and column are both 0."""
    r0 = min(r for r, c in obj)
    c0 = min(c for r, c in obj)
    return frozenset((r - r0, c - c0) for r, c in obj)

def object_orientations(obj: Object) -> List[FrozenSet[Tuple[int,int]]]:
    """All distinct orientations: 4 rotations × 2 flips."""
    def rot90(cells):
        return [(-c, r) for r, c in cells]
    def fliph(cells):
        return [(r, -c) for r, c in cells]

    results: List[FrozenSet] = []
    seen: Set = set()
    curr = list(obj)
    for _ in range(4):
        for base in [curr, fliph(curr)]:
            norm = normalize_shape(frozenset(base))
            if norm not in seen:
                seen.add(norm)
                results.append(norm)
        curr = rot90(curr)
    return results


# ── Color queries ─────────────────────────────────────────────────────────────

def object_color(g: Grid, obj: Object) -> Optional[int]:
    """Return the single color of all cells in obj, or None if mixed."""
    colors = {g[r][c] for r, c in obj}
    return next(iter(colors)) if len(colors) == 1 else None

def object_colors(g: Grid, obj: Object) -> Set[int]:
    return {g[r][c] for r, c in obj}

def object_majority_color(g: Grid, obj: Object) -> int:
    return Counter(g[r][c] for r, c in obj).most_common(1)[0][0]


# ── Separator detection ───────────────────────────────────────────────────────

def find_separators(
    g: Grid,
    sep_color: Optional[int] = None,
) -> Tuple[List[int], List[int]]:
    """
    Find rows and columns that are entirely one color (the separator).

    If sep_color is None, tries each non-background color and picks whichever
    makes the most full rows/cols.

    Returns (sep_rows, sep_cols).
    """
    h, w = len(g), len(g[0])
    bg = background(g)

    candidates = {sep_color} if sep_color is not None else (
        {c for row in g for c in row if c != bg}
    )

    best_rows: List[int] = []
    best_cols: List[int] = []
    best_score = -1

    for color in candidates:
        rows = [r for r in range(h) if all(g[r][c] == color for c in range(w))]
        cols = [c for c in range(w) if all(g[r][c] == color for r in range(h))]
        score = len(rows) + len(cols)
        if score > best_score:
            best_score = score
            best_rows, best_cols = rows, cols

    return best_rows, best_cols


def split_by_separators(
    g: Grid,
    sep_rows: List[int],
    sep_cols: List[int],
) -> List[List[Grid]]:
    """
    Split grid into a 2-D list of sub-grids defined by separator rows/cols.
    Returns regions[row_band][col_band].
    """
    h, w = len(g), len(g[0])
    sep_rows_s = sorted(set(sep_rows))
    sep_cols_s = sorted(set(sep_cols))

    row_edges = [-1] + sep_rows_s + [h]
    col_edges = [-1] + sep_cols_s + [w]

    row_bands = [(row_edges[i]+1, row_edges[i+1]) for i in range(len(row_edges)-1)
                 if row_edges[i]+1 < row_edges[i+1]]
    col_bands = [(col_edges[i]+1, col_edges[i+1]) for i in range(len(col_edges)-1)
                 if col_edges[i]+1 < col_edges[i+1]]

    result = []
    for r0, r1 in row_bands:
        row_result = []
        for c0, c1 in col_bands:
            sub = [g[r][c0:c1] for r in range(r0, r1)]
            row_result.append(sub)
        result.append(row_result)
    return result


def find_separator_color(g: Grid) -> Optional[int]:
    """Return the color used as separator, or None."""
    sep_rows, sep_cols = find_separators(g)
    if not sep_rows and not sep_cols:
        return None
    h, w = len(g), len(g[0])
    if sep_rows:
        return g[sep_rows[0]][0]
    return g[0][sep_cols[0]]


# ── Symmetry ──────────────────────────────────────────────────────────────────

def symmetry_flags(g: Grid) -> Dict[str, bool]:
    """Check horizontal, vertical, rotational 180° symmetry."""
    fh = [row[::-1] for row in g]
    fv = g[::-1]
    rot180 = [row[::-1] for row in g[::-1]]
    return {
        "flip_h":   g == fh,
        "flip_v":   g == fv,
        "rot180":   g == rot180,
        "rot90":    g == [list(row) for row in zip(*g[::-1])],
    }


# ── Color-chain / mapping extraction (abc82100-style) ─────────────────────────

def extract_color_chains(
    g: Grid,
    chain_objs: List[Object],
) -> Dict[int, int]:
    """
    For each 2-cell, 2-color object (a "chain"), extract a source→target
    color mapping.  The "far" cell from any nearby anchor is the source;
    the "near" cell is the target.

    If no spatial anchor is available, we use color frequency as tie-breaker
    (rarer color = source, because it represents the "key").
    """
    hist = color_histogram(g)
    mapping: Dict[int, int] = {}
    for obj in chain_objs:
        cells = list(obj)
        if len(cells) != 2:
            continue
        c1 = g[cells[0][0]][cells[0][1]]
        c2 = g[cells[1][0]][cells[1][1]]
        if c1 == c2:
            continue
        # Less frequent color = source
        src, dst = (c1, c2) if hist.get(c1, 0) >= hist.get(c2, 0) else (c2, c1)
        mapping[src] = dst
    return mapping


def assign_objects_to_nearest(
    objs: List[Object],
    groups: List[Object],
) -> List[int]:
    """
    For each object in objs, return the index of the nearest group
    (by centroid Euclidean distance).
    """
    group_centroids = [centroid(g) for g in groups]
    assignments = []
    for obj in objs:
        obj_c = centroid(obj)
        best = min(range(len(groups)),
                   key=lambda i: dist_sq(obj_c, group_centroids[i]))
        assignments.append(best)
    return assignments
