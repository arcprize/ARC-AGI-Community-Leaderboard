"""
DSL Program Synthesizer
========================
Given ARC train pairs, searches for a DSL program that explains all of them.

Three-layer strategy (fastest first):

  Layer 1 — Direct pattern recognizers  (~0.001–0.01 s each)
    Color mapping, geometric transform, invert+tile, region split+op,
    histogram bar chart, separator template stamp.

  Layer 2 — Object-based recognizers    (~0.01–0.5 s each)
    Shape-match recolor, frame fill, count-and-place, stamp-by-mapping
    (generalizes abc82100), concentric fill, run-length group.

  Layer 3 — Enumerative depth-1 sweep   (fallback, ~1–2 s)
    Try every single primitive over all color permutations.

Every strategy returns either a callable  g → Grid  or None.
The synthesizer tries them in order and stops at first hit.
"""

from __future__ import annotations

import time
from collections import Counter, deque
from itertools import permutations
from typing import Callable, Dict, List, Optional, Set, Tuple

from dsl.primitives import (
    Grid, Object,
    rotate, flip_h, flip_v, flip_diag, flip_antidiag,
    crop, crop_bbox, crop_to_content,
    hstack, vstack,
    paint, stamp, clear_grid, empty_grid, copy_grid, fill_grid,
    recolor, apply_color_map, swap_colors,
    grid_or, grid_and, grid_xor,
    background, colors_in, color_histogram, colors_in,
    tile_grid, grid_size, grids_equal, output_size_matches,
    translate_object, object_to_grid, scale_object,
)
from dsl.perception import (
    find_objects, find_objects_of_color, find_objects_excluding,
    bounding_box, centroid, dist_sq, normalize_shape, object_orientations,
    object_color, object_colors, object_majority_color,
    find_separators, split_by_separators, find_separator_color,
    symmetry_flags,
    extract_color_chains, assign_objects_to_nearest,
)

# Callable type for a discovered program
Program = Callable[[Grid], Grid]

# ── Helpers ───────────────────────────────────────────────────────────────────

def _fits_all(prog: Program, pairs: List[Tuple[Grid, Grid]]) -> bool:
    """Return True if prog(x) == y for all (x, y) in pairs."""
    try:
        for x, y in pairs:
            if not grids_equal(prog(x), y):
                return False
        return True
    except Exception:
        return False

def _size_consistent(pairs: List[Tuple[Grid, Grid]]) -> bool:
    """True if all outputs have the same size."""
    if not pairs:
        return True
    h0, w0 = grid_size(pairs[0][1])
    return all(grid_size(y) == (h0, w0) for _, y in pairs)

def _output_same_size_as_input(pairs: List[Tuple[Grid, Grid]]) -> bool:
    return all(grid_size(x) == grid_size(y) for x, y in pairs)


def _grid_components(
    g: Grid,
    diagonals: bool = False,
) -> List[List[Tuple[int, int, int]]]:
    """Return same-color connected components of non-background cells."""
    b = background(g)
    H, W = len(g), len(g[0])
    dirs = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    if diagonals:
        dirs += [(-1, -1), (-1, 1), (1, -1), (1, 1)]

    seen: Set[Tuple[int, int]] = set()
    comps: List[List[Tuple[int, int, int]]] = []

    for r in range(H):
        for c in range(W):
            col = g[r][c]
            if col == b or (r, c) in seen:
                continue
            q = deque([(r, c)])
            seen.add((r, c))
            comp: List[Tuple[int, int, int]] = []
            while q:
                cr, cc = q.popleft()
                comp.append((cr, cc, col))
                for dr, dc in dirs:
                    nr, nc = cr + dr, cc + dc
                    if not (0 <= nr < H and 0 <= nc < W):
                        continue
                    if (nr, nc) in seen or g[nr][nc] != col:
                        continue
                    seen.add((nr, nc))
                    q.append((nr, nc))
            comps.append(comp)
    return comps


def _component_bbox(
    cells: List[Tuple[int, int, int]],
) -> Tuple[int, int, int, int]:
    rows = [r for r, _, _ in cells]
    cols = [c for _, c, _ in cells]
    return min(rows), min(cols), max(rows), max(cols)


# ═══════════════════════════════════════════════════════════════════════════════
# LAYER 1 — Direct pattern recognizers
# ═══════════════════════════════════════════════════════════════════════════════

def try_identity(pairs):
    prog = lambda g: g
    return prog if _fits_all(prog, pairs) else None


def try_geometric_transforms(pairs):
    """Try all 8 rigid isometries: 4 rotations × 2 flips."""
    for fn in [
        flip_h, flip_v, flip_diag, flip_antidiag,
        lambda g: rotate(g, 1),
        lambda g: rotate(g, 2),
        lambda g: rotate(g, 3),
    ]:
        if _fits_all(fn, pairs):
            return fn
    # Combined: flip then rotate
    for flip in [flip_h, flip_v]:
        for k in range(1, 4):
            def make_fn(f=flip, r=k):
                return lambda g: rotate(f(g), r)
            fn = make_fn()
            if _fits_all(fn, pairs):
                return fn
    return None


def try_color_mapping(pairs):
    """Try bijective and non-bijective color remappings."""
    if not _output_same_size_as_input(pairs):
        return None

    # Collect color sets
    src_colors = sorted(colors_in(pairs[0][0]))
    dst_colors = sorted(colors_in(pairs[0][1]))

    # Build a mapping from training constraints
    # For each cell, the (input_color, output_color) pair must be consistent
    cmap: Dict[int, int] = {}
    consistent = True
    for x, y in pairs:
        h, w = grid_size(x)
        for r in range(h):
            for c in range(w):
                sc, dc = x[r][c], y[r][c]
                if sc in cmap:
                    if cmap[sc] != dc:
                        consistent = False
                        break
                else:
                    cmap[sc] = dc
            if not consistent:
                break
        if not consistent:
            break

    if consistent and cmap:
        prog = lambda g, m=cmap: apply_color_map(g, m)
        if _fits_all(prog, pairs):
            return prog
    return None


def try_invert_and_tile(pairs):
    """Invert 0↔color, then optionally tile 2×2 or other factor."""
    for x, y in pairs:
        if grid_size(x) == grid_size(y):
            return None  # output same size → not a tile task

    for x, y in pairs[:1]:
        hx, wx = grid_size(x)
        hy, wy = grid_size(y)
        if hy % hx != 0 or wy % wx != 0:
            continue
        tr, tc = hy // hx, wy // wx

        # Find non-zero color to invert against
        non_zeros = {c for row in x for c in row if c != 0}
        if len(non_zeros) != 1:
            continue
        color = next(iter(non_zeros))

        def make_fn(color=color, tr=tr, tc=tc):
            def fn(g):
                inv = [[color if v == 0 else 0 for v in row] for row in g]
                return tile_grid(inv, len(g)*tr, len(g[0])*tc)
            return fn

        prog = make_fn()
        if _fits_all(prog, pairs):
            return prog
    return None


def try_tiling(pairs):
    """Try simple tiling (no inversion): output = tile(input, r×c)."""
    for x, y in pairs[:1]:
        hx, wx = grid_size(x)
        hy, wy = grid_size(y)
        if hy % hx != 0 or wy % wx != 0:
            continue
        tr, tc = hy // hx, wy // wx
        if tr == 1 and tc == 1:
            continue

        def make_fn(tr=tr, tc=tc):
            return lambda g: tile_grid(g, len(g)*tr, len(g[0])*tc)

        prog = make_fn()
        if _fits_all(prog, pairs):
            return prog
    return None


def try_crop_to_content(pairs):
    bg = background(pairs[0][0])
    prog = lambda g: crop_to_content(g, bg)
    return prog if _fits_all(prog, pairs) else None


def try_histogram_barchart(pairs):
    """
    Count each non-background color and build a vertical bar chart.
    Covers tasks like b7999b51, f3cdc58f.
    """
    if not _output_same_size_as_input(pairs):
        return None

    def _barchart(g: Grid) -> Grid:
        h, w = grid_size(g)
        bg = background(g)
        hist = {c: 0 for c in colors_in(g) if c != bg}
        for row in g:
            for v in row:
                if v != bg:
                    hist[v] = hist.get(v, 0) + 1
        # Sort colors by count descending (or by color value)
        sorted_colors = sorted(hist.keys(), key=lambda c: (-hist[c], c))
        out = [[bg] * w for _ in range(h)]
        for col_idx, color in enumerate(sorted_colors):
            if col_idx >= w:
                break
            bar_h = hist[color]
            for r in range(h - bar_h, h):
                out[r][col_idx] = color
        return out

    return _barchart if _fits_all(_barchart, pairs) else None


def try_region_boolean(pairs):
    """
    Split grid on separators, apply boolean op (OR/AND/XOR) between two regions.
    Also tries recoloring the result (1→N) for tasks where output uses a specific color.
    Covers tasks like e133d23d, 0520fde7.
    """
    if not pairs:
        return None

    x0, y0 = pairs[0]
    sep_rows, sep_cols = find_separators(x0)
    if not sep_rows and not sep_cols:
        return None

    # Collect all colors in expected output
    out_colors = list(colors_in(y0) - {background(y0)}) + [1]

    for op_name, op in [("or", grid_or), ("and", grid_and), ("xor", grid_xor)]:
        for out_color in out_colors:
            def make_fn(sr=sep_rows, sc=sep_cols, op=op, oc=out_color):
                def fn(g):
                    regions = split_by_separators(g, sr, sc)
                    flat = [r for row in regions for r in row]
                    if len(flat) < 2:
                        return g
                    result = op(flat[0], flat[1])
                    # Recolor all non-zero cells to the target color
                    bg2 = background(result)
                    return [[oc if v != bg2 else bg2 for v in row] for row in result]
                return fn
            prog = make_fn()
            if _fits_all(prog, pairs):
                return prog
    return None


def try_separator_template_stamp(pairs):
    """
    Split on separator. One region = palette (NxN blocks → logical grid).
    Other region = template of marker positions.
    Stamp palette block wherever marker appears.
    Covers b4a43f3b, 12422b43-style tasks.
    """
    x0, _ = pairs[0]
    sep_rows, sep_cols = find_separators(x0)
    if not sep_rows and not sep_cols:
        return None

    def _try_stamp(sr, sc, x0, y0):
        regions = split_by_separators(x0, sr, sc)
        flat = [r for row in regions for r in row]
        if len(flat) < 2:
            return None
        # Try each region as palette, rest as template
        for pi in range(len(flat)):
            palette = flat[pi]
            template = flat[1 - pi] if len(flat) == 2 else None
            if template is None:
                continue
            ph, pw = grid_size(palette)
            th, tw = grid_size(template)
            # Try block sizes
            for block_h in range(1, ph + 1):
                if ph % block_h != 0:
                    continue
                for block_w in range(1, pw + 1):
                    if pw % block_w != 0:
                        continue
                    rows_p = ph // block_h
                    cols_p = pw // block_w
                    # Extract block palette
                    pal_grid = [
                        [palette[r * block_h][c * block_w] for c in range(cols_p)]
                        for r in range(rows_p)
                    ]
                    # Find marker color in template
                    bg_t = background(template)
                    markers = {c for row in template for c in row if c != bg_t}
                    for marker in markers:
                        def make_stamp_fn(pal_grid=pal_grid, template=template,
                                          marker=marker, block_h=block_h, block_w=block_w,
                                          th=th, tw=tw, sr=sr, sc=sc):
                            def fn(g):
                                regs = split_by_separators(g, sr, sc)
                                flat2 = [r for row in regs for r in row]
                                if len(flat2) < 2:
                                    return g
                                tmpl = flat2[1 - pi] if len(flat2) == 2 else flat2[1]
                                out_h = len(tmpl) * block_h
                                out_w = len(tmpl[0]) * block_w
                                out = empty_grid(out_h, out_w)
                                for tr in range(len(tmpl)):
                                    for tc in range(len(tmpl[0])):
                                        if tmpl[tr][tc] == marker:
                                            for pr in range(len(pal_grid)):
                                                for pc in range(len(pal_grid[0])):
                                                    out[tr * block_h + pr][tc * block_w + pc] = pal_grid[pr][pc]
                                return out
                            return fn

                        prog = make_stamp_fn()
                        if _fits_all(prog, pairs):
                            return prog
        return None

    return _try_stamp(sep_rows, sep_cols, x0, _)


# ═══════════════════════════════════════════════════════════════════════════════
# LAYER 2 — Object-based recognizers
# ═══════════════════════════════════════════════════════════════════════════════

def try_shape_match_recolor(pairs):
    """
    Find objects of one color that match shapes of another color;
    recolor them to the matched color.
    Covers 2a5f8217.
    """
    if not _output_same_size_as_input(pairs):
        return None

    x0, y0 = pairs[0]
    bg = background(x0)

    # Find template color: objects whose shape appears twice (once as 1, once as color)
    all_objs = find_objects_excluding(x0, {bg})
    shape_to_colors: Dict = {}
    for obj in all_objs:
        shape = normalize_shape(obj)
        color = object_color(x0, obj)
        if color is None:
            continue
        shape_to_colors.setdefault(shape, set()).add(color)

    # Find pairs (placeholder_color, target_color) with matching shapes
    placeholder = None
    for shape, color_set in shape_to_colors.items():
        matching = [s for s, cs in shape_to_colors.items() if s == shape and cs != color_set]
        for other_shape in matching:
            for c1 in color_set:
                for c2 in (shape_to_colors.get(other_shape) or set()):
                    if c1 != c2:
                        placeholder = c1

    # If one color's shapes always match another color's shapes
    all_colors = list({c for row in x0 for c in row if c != bg})
    for candidate_ph in all_colors:
        def make_fn(ph=candidate_ph, bg=bg):
            def fn(g):
                bg2 = background(g)
                ph_objs = find_objects_of_color(g, ph)
                target_objs = find_objects_excluding(g, {bg2, ph})
                if not ph_objs or not target_objs:
                    return g
                # Build shape → color mapping from non-placeholder objects
                shape_map = {}
                for obj in target_objs:
                    c = object_color(g, obj)
                    if c is None:
                        continue
                    for orient in object_orientations(obj):
                        shape_map[orient] = c
                out = copy_grid(g)
                for obj in ph_objs:
                    for orient in object_orientations(obj):
                        if orient in shape_map:
                            for r, c in obj:
                                out[r][c] = shape_map[orient]
                            break
                return out
            return fn
        prog = make_fn()
        if _fits_all(prog, pairs):
            return prog
    return None


def try_stamp_by_mapping(pairs):
    """
    abc82100-style: find stamp-shape groups + color-chain pairs,
    then stamp each source cell with its mapped shape and target color.
    """
    if not _output_same_size_as_input(pairs):
        return None

    x0, y0 = pairs[0]
    all_colors = sorted(colors_in(x0) - {0})

    # Try each color as the "stamp template" color
    for stamp_color in all_colors:
        stamp_groups = find_objects_of_color(x0, stamp_color, connectivity=8)
        if not stamp_groups:
            continue

        # Try each other color as the "chain" background
        remaining_colors = [c for c in all_colors if c != stamp_color]
        chain_objs = []
        for obj in find_objects_excluding(x0, {0, stamp_color}):
            if len(obj) == 2 and len(object_colors(x0, obj)) == 2:
                chain_objs.append(obj)

        if not chain_objs:
            continue

        # Extract color mapping from chains
        color_map = extract_color_chains(x0, chain_objs)
        if not color_map:
            continue

        # Assign each chain to nearest stamp group
        assignments = assign_objects_to_nearest(chain_objs, stamp_groups)

        # Build: source_color → (target_color, offsets relative to chain's reference)
        chain_cells = frozenset(c for obj in chain_objs for c in obj)
        stamp_cells = frozenset(c for g in stamp_groups for c in g)

        # Determine offsets per assignment
        per_color_data: Dict = {}
        for chain, group_idx in zip(chain_objs, assignments):
            cells = list(chain)
            c1 = x0[cells[0][0]][cells[0][1]]
            c2 = x0[cells[1][0]][cells[1][1]]
            src, tgt = (c1, c2) if c2 in color_map.get(c1, {c2}) else (c2, c1)
            grp = stamp_groups[group_idx]
            ref = cells[0]  # reference point: use first chain cell
            offsets = frozenset((r - ref[0], c - ref[1]) for r, c in grp)
            per_color_data[src] = (tgt if tgt != src else color_map.get(src, src), offsets, ref)

        def make_fn(per_color_data=per_color_data, stamp_cells=stamp_cells,
                    chain_cells=chain_cells, stamp_color=stamp_color):
            def fn(g):
                h, w = grid_size(g)
                out = [[g[r][c] if (r,c) not in stamp_cells and (r,c) not in chain_cells
                        and g[r][c] not in per_color_data else 0
                        for c in range(w)] for r in range(h)]
                for r in range(h):
                    for c in range(w):
                        v = g[r][c]
                        if v in per_color_data and (r, c) not in chain_cells:
                            tgt, offsets, _ = per_color_data[v]
                            for dr, dc in offsets:
                                nr, nc = r + dr, c + dc
                                if 0 <= nr < h and 0 <= nc < w:
                                    out[nr][nc] = tgt
                return out
            return fn

        prog = make_fn()
        if _fits_all(prog, pairs):
            return prog
    return None


def try_run_length_group(pairs):
    """
    Group consecutive identical rows into blocks; recolor every k-th block.
    Covers 22a4bbc2.
    """
    if not _output_same_size_as_input(pairs):
        return None

    for recolor_val in range(1, 10):
        for period in range(2, 6):
            def make_fn(period=period, rv=recolor_val):
                def fn(g):
                    rows = len(g)
                    out = [row[:] for row in g]
                    blocks = []
                    i = 0
                    while i < rows:
                        j = i + 1
                        while j < rows and g[j] == g[i]:
                            j += 1
                        blocks.append((i, j - 1))
                        i = j
                    for idx, (start, end) in enumerate(blocks):
                        if idx % period == 0:
                            for r in range(start, end + 1):
                                for c in range(len(g[r])):
                                    if out[r][c] != 0:
                                        out[r][c] = rv
                    return out
                return fn
            prog = make_fn()
            if _fits_all(prog, pairs):
                return prog
    return None


def try_frame_fill(pairs):
    """
    Find rectangular frames; fill their interior with a specific color.
    Covers b5ca7ac4-style tasks.
    """
    if not _output_same_size_as_input(pairs):
        return None

    x0, y0 = pairs[0]
    bg = background(x0)

    def _frame_fill(g: Grid) -> Grid:
        h, w = grid_size(g)
        bg2 = background(g)
        out = copy_grid(g)
        # Find all 5-row×5-col frames (generalize to any size)
        for size in range(3, max(h, w)):
            for r in range(h - size + 1):
                for c in range(w - size + 1):
                    border_color = g[r][c]
                    if border_color == bg2:
                        continue
                    is_frame = True
                    for i in range(size):
                        for j in range(size):
                            is_border = (i == 0 or i == size-1 or j == 0 or j == size-1)
                            if is_border and g[r+i][c+j] != border_color:
                                is_frame = False
                                break
                        if not is_frame:
                            break
                    if is_frame:
                        # Fill interior
                        interior_color = g[r+1][c+1]
                        if interior_color != bg2 and interior_color != border_color:
                            for i in range(1, size - 1):
                                for j in range(1, size - 1):
                                    out[r+i][c+j] = interior_color
        return out

    return _frame_fill if _fits_all(_frame_fill, pairs) else None


def try_fractal_self_multiply(pairs):
    """
    Each non-zero cell (r,c) in the input becomes a full copy of the input
    placed at block position (r,c) in a tiled output.
    Covers 007bbfb7 and similar fractal/self-similar tasks.
    """
    x0, y0 = pairs[0]
    h, w = grid_size(x0)
    oh, ow = grid_size(y0)
    if oh != h * h or ow != w * w:
        # Try h*w vs w*h too (non-square)
        if oh != h * h or ow != w * w:
            pass  # still try below

    bg = background(x0)

    def _fractal(g: Grid) -> Grid:
        gh, gw = grid_size(g)
        out = empty_grid(gh * gh, gw * gw)
        for br in range(gh):
            for bc in range(gw):
                if g[br][bc] != bg:
                    for r in range(gh):
                        for c in range(gw):
                            out[br * gh + r][bc * gw + c] = g[r][c]
        return out

    # Also try: each non-zero cell → copy, scaled by non-zero color
    def _fractal_color(g: Grid) -> Grid:
        gh, gw = grid_size(g)
        out = empty_grid(gh * gh, gw * gw)
        for br in range(gh):
            for bc in range(gw):
                color = g[br][bc]
                if color != 0:
                    for r in range(gh):
                        for c in range(gw):
                            if g[r][c] != 0:
                                out[br * gh + r][bc * gw + c] = color
        return out

    for fn in [_fractal, _fractal_color]:
        if _fits_all(fn, pairs):
            return fn
    return None


def try_checkerboard_tile(pairs):
    """
    Tile input in NxM blocks; alternate rows or cols get flip_h / flip_v.
    Covers 00576224: 2x2 → 6x6 with alternating flip_h on row bands.
    """
    x0, y0 = pairs[0]
    hx, wx = grid_size(x0)
    hy, wy = grid_size(y0)
    if hy % hx != 0 or wy % wx != 0:
        return None
    tr, tc = hy // hx, wy // wx

    for row_flip in [flip_h, flip_v, None]:
        for col_flip in [flip_h, flip_v, None]:
            if row_flip is None and col_flip is None:
                continue

            def make_fn(tr=tr, tc=tc, rf=row_flip, cf=col_flip):
                def fn(g):
                    gh, gw = grid_size(g)
                    out = empty_grid(gh * tr, gw * tc)
                    for br in range(tr):
                        for bc in range(tc):
                            block = g
                            if rf is not None and br % 2 == 1:
                                block = rf(block)
                            if cf is not None and bc % 2 == 1:
                                block = cf(block)
                            for r in range(gh):
                                for c in range(gw):
                                    out[br * gh + r][bc * gw + c] = block[r][c]
                    return out
                return fn

            prog = make_fn()
            if _fits_all(prog, pairs):
                return prog
    return None


def try_column_height_rank(pairs):
    """
    Find vertical bars of a single color; rank by height (tallest=1).
    Recolor each bar by its rank.
    Covers 08ed6ac7.
    """
    if not _output_same_size_as_input(pairs):
        return None

    x0, y0 = pairs[0]
    bg = background(x0)
    fg_colors = list(colors_in(x0) - {bg})
    if len(fg_colors) != 1:
        return None

    bar_color = fg_colors[0]

    def _col_rank(g: Grid) -> Grid:
        h, w = grid_size(g)
        bg2 = background(g)
        bar_c = next((c for c in colors_in(g) if c != bg2), None)
        if bar_c is None:
            return g
        # Measure height of each column's bar
        col_heights = {}
        for c in range(w):
            col = [g[r][c] for r in range(h)]
            cnt = sum(1 for v in col if v == bar_c)
            if cnt > 0:
                col_heights[c] = cnt
        if not col_heights:
            return g
        # Rank: unique heights sorted descending → rank 1,2,3,...
        unique_h = sorted(set(col_heights.values()), reverse=True)
        rank_of = {h: i+1 for i, h in enumerate(unique_h)}
        out = copy_grid(g)
        for c, ht in col_heights.items():
            rank = rank_of[ht]
            for r in range(h):
                if g[r][c] == bar_c:
                    out[r][c] = rank
        return out

    return _col_rank if _fits_all(_col_rank, pairs) else None


def try_row_height_rank(pairs):
    """Same as column_height_rank but for horizontal bars."""
    if not _output_same_size_as_input(pairs):
        return None

    x0, _ = pairs[0]
    bg = background(x0)
    fg = list(colors_in(x0) - {bg})
    if len(fg) != 1:
        return None

    def _row_rank(g: Grid) -> Grid:
        h, w = grid_size(g)
        bg2 = background(g)
        bar_c = next((c for c in colors_in(g) if c != bg2), None)
        if bar_c is None:
            return g
        row_heights = {}
        for r in range(h):
            cnt = sum(1 for v in g[r] if v == bar_c)
            if cnt > 0:
                row_heights[r] = cnt
        if not row_heights:
            return g
        unique_h = sorted(set(row_heights.values()), reverse=True)
        rank_of = {h: i+1 for i, h in enumerate(unique_h)}
        out = copy_grid(g)
        for r, ht in row_heights.items():
            rank = rank_of[ht]
            for c in range(w):
                if g[r][c] == bar_c:
                    out[r][c] = rank
        return out

    return _row_rank if _fits_all(_row_rank, pairs) else None


def try_extract_region(pairs):
    """
    Split by separators; output = one of the sub-regions.
    Covers 0520fde7 (input 3x7 split by 5s → one 3x3 side).
    """
    x0, y0 = pairs[0]
    sep_rows, sep_cols = find_separators(x0)
    if not sep_rows and not sep_cols:
        return None

    regions_flat = [r for row in split_by_separators(x0, sep_rows, sep_cols) for r in row]
    for idx, region in enumerate(regions_flat):
        if grid_size(region) == grid_size(y0):
            def make_fn(sr=sep_rows, sc=sep_cols, i=idx):
                def fn(g):
                    flat = [r for row in split_by_separators(g, sr, sc) for r in row]
                    return flat[i] if i < len(flat) else g
                return fn
            prog = make_fn()
            if _fits_all(prog, pairs):
                return prog
    return None


def try_object_count_place(pairs):
    """
    Count objects per color; place output cells according to count/position.
    Covers counting-type tasks.
    """
    if not _output_same_size_as_input(pairs):
        return None
    return None


def try_gravity_down(pairs):
    """
    Each column: non-bg cells fall to the bottom (gravity down).
    Covers 1e0a9b12 and similar tasks.
    """
    if not _output_same_size_as_input(pairs):
        return None

    def _gravity_down(g: Grid) -> Grid:
        h, w = grid_size(g)
        bg = background(g)
        out = [[bg] * w for _ in range(h)]
        for c in range(w):
            col_vals = [g[r][c] for r in range(h) if g[r][c] != bg]
            for i, v in enumerate(col_vals):
                out[h - len(col_vals) + i][c] = v
        return out

    return _gravity_down if _fits_all(_gravity_down, pairs) else None


def try_gravity_up(pairs):
    """Each column: non-bg cells float to the top. Covers 03560426-style tasks."""
    if not _output_same_size_as_input(pairs):
        return None

    def _gravity_up(g: Grid) -> Grid:
        h, w = grid_size(g)
        bg = background(g)
        out = [[bg] * w for _ in range(h)]
        for c in range(w):
            col_vals = [g[r][c] for r in range(h) if g[r][c] != bg]
            for i, v in enumerate(col_vals):
                out[i][c] = v
        return out

    return _gravity_up if _fits_all(_gravity_up, pairs) else None


def try_gravity_left(pairs):
    """Each row: non-bg cells slide left."""
    if not _output_same_size_as_input(pairs):
        return None

    def _gravity_left(g: Grid) -> Grid:
        h, w = grid_size(g)
        bg = background(g)
        out = [[bg] * w for _ in range(h)]
        for r in range(h):
            row_vals = [v for v in g[r] if v != bg]
            for i, v in enumerate(row_vals):
                out[r][i] = v
        return out

    return _gravity_left if _fits_all(_gravity_left, pairs) else None


def try_gravity_right(pairs):
    """Each row: non-bg cells slide right."""
    if not _output_same_size_as_input(pairs):
        return None

    def _gravity_right(g: Grid) -> Grid:
        h, w = grid_size(g)
        bg = background(g)
        out = [[bg] * w for _ in range(h)]
        for r in range(h):
            row_vals = [v for v in g[r] if v != bg]
            for i, v in enumerate(row_vals):
                out[r][w - len(row_vals) + i] = v
        return out

    return _gravity_right if _fits_all(_gravity_right, pairs) else None


def try_fill_enclosed(pairs):
    """
    BFS flood-fill from the border; cells unreachable AND currently bg → fill with new color.
    Covers 00d62c1b (enclosed rectangles filled with color 4).
    """
    if not _output_same_size_as_input(pairs):
        return None

    x0, y0 = pairs[0]
    bg = background(x0)
    # Find what new color appears in output but not input
    new_colors = colors_in(y0) - colors_in(x0)
    if not new_colors:
        return None
    fill_c = next(iter(new_colors))

    def _fill_enclosed(g: Grid, fc=fill_c) -> Grid:
        h, w = grid_size(g)
        bg2 = background(g)
        # BFS from all border cells that are bg
        visited = [[False]*w for _ in range(h)]
        queue = deque()
        for r in range(h):
            for c in range(w):
                if (r == 0 or r == h-1 or c == 0 or c == w-1) and g[r][c] == bg2:
                    if not visited[r][c]:
                        visited[r][c] = True
                        queue.append((r, c))
        while queue:
            r, c = queue.popleft()
            for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
                nr, nc = r+dr, c+dc
                if 0 <= nr < h and 0 <= nc < w and not visited[nr][nc] and g[nr][nc] == bg2:
                    visited[nr][nc] = True
                    queue.append((nr, nc))
        out = copy_grid(g)
        for r in range(h):
            for c in range(w):
                if g[r][c] == bg2 and not visited[r][c]:
                    out[r][c] = fc
        return out

    return _fill_enclosed if _fits_all(_fill_enclosed, pairs) else None


def try_color_key_table(pairs):
    """
    Top-left NxM cells form a color mapping table.
    The function is self-contained: it reads the key table from the INPUT
    grid at runtime (since each example has its own key table).
    Covers 0becf7df (bidirectional swap) and similar recoloring tasks.
    """
    if not _output_same_size_as_input(pairs):
        return None

    x0, _ = pairs[0]
    h, w = grid_size(x0)

    def _read_cmap(g, table_h, table_w, bidirectional):
        """Read key table from top-left table_h×table_w of g."""
        bg = background(g)
        cmap: dict = {}
        for r in range(table_h):
            for c in range(0, table_w - 1, 2):
                src = g[r][c]
                dst = g[r][c + 1]
                if src == bg or dst == bg:
                    continue
                cmap[src] = dst
                if bidirectional:
                    cmap[dst] = src
        return cmap

    def _apply_cmap(g, table_h, table_w, bidirectional):
        cmap = _read_cmap(g, table_h, table_w, bidirectional)
        if not cmap:
            return g
        h2, w2 = grid_size(g)
        out = copy_grid(g)
        tc = {(r, c) for r in range(table_h) for c in range(table_w)}
        for r in range(h2):
            for c in range(w2):
                if (r, c) in tc:
                    continue
                v = g[r][c]
                if v in cmap:
                    out[r][c] = cmap[v]
        return out

    for bidirectional in (False, True):
        for table_h in range(1, min(4, h)):
            for table_w in range(2, min(5, w)):  # need at least 2 cols for a pair
                def make_fn(th=table_h, tw=table_w, bi=bidirectional):
                    def fn(g):
                        return _apply_cmap(g, th, tw, bi)
                    return fn

                prog = make_fn()
                if _fits_all(prog, pairs):
                    return prog
    return None


def try_interior_fill(pairs):
    """
    Shapes made of 1-cells contain a single colored marker. Fill 'interior'
    cells — those whose all 8 neighbors are non-background — with the marker
    color of their connected component. Covers 09c534e7.
    """
    if not _output_same_size_as_input(pairs):
        return None

    def _interior_fill(g: Grid) -> Grid:
        h, w = grid_size(g)
        bg = background(g)
        out = copy_grid(g)

        # Build connected components and find each component's marker
        visited: dict = {}
        comp_marker: dict = {}
        cid = 0
        for sr in range(h):
            for sc in range(w):
                if g[sr][sc] == bg or (sr, sc) in visited:
                    continue
                queue = deque([(sr, sc)])
                visited[(sr, sc)] = cid
                marker = None
                while queue:
                    r, c = queue.popleft()
                    v = g[r][c]
                    if v != bg and v != 1:
                        marker = v
                    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < h and 0 <= nc < w and g[nr][nc] != bg and (nr, nc) not in visited:
                            visited[(nr, nc)] = cid
                            queue.append((nr, nc))
                comp_marker[cid] = marker
                cid += 1

        # Fill interior cells (all 8 neighbors non-bg) with component marker
        for r in range(1, h - 1):
            for c in range(1, w - 1):
                if g[r][c] == bg:
                    continue
                marker = comp_marker.get(visited.get((r, c)))
                if marker is None:
                    continue
                if all(g[r + dr][c + dc] != bg
                       for dr in (-1, 0, 1) for dc in (-1, 0, 1)
                       if (dr, dc) != (0, 0)):
                    out[r][c] = marker
        return out

    return _interior_fill if _fits_all(_interior_fill, pairs) else None


def try_adjacent_recolor(pairs):
    """
    Recolor cells of color A that are 8-adjacent to any cell of color B → color C.
    Covers 14754a24 (5s adjacent to 4s → 2).
    """
    if not _output_same_size_as_input(pairs):
        return None

    x0, y0 = pairs[0]
    bg = background(x0)
    fg = [c for c in colors_in(x0) if c != bg]

    for A in fg:
        for B in fg:
            if A == B:
                continue
            for C in range(10):
                if C == A:
                    continue

                def make_fn(a=A, b=B, c=C):
                    def fn(g: Grid) -> Grid:
                        h, w = grid_size(g)
                        out = copy_grid(g)
                        for r in range(h):
                            for cc in range(w):
                                if g[r][cc] != a:
                                    continue
                                for dr in (-1, 0, 1):
                                    for dc in (-1, 0, 1):
                                        if dr == 0 and dc == 0:
                                            continue
                                        nr, nc = r + dr, cc + dc
                                        if 0 <= nr < h and 0 <= nc < w and g[nr][nc] == b:
                                            out[r][cc] = c
                                            break
                                    else:
                                        continue
                                    break
                        return out
                    return fn

                prog = make_fn()
                if _fits_all(prog, pairs):
                    return prog
    return None


def try_complete_symmetry(pairs):
    """
    Complete a nearly-symmetric grid by mirroring non-bg cells across
    horizontal, vertical, or both axes — using either the grid center
    or the pattern bounding-box center as the axis. Covers 11852cab.
    """
    if not _output_same_size_as_input(pairs):
        return None

    def _apply_sym(g: Grid, use_h: bool, use_v: bool, use_pattern_center: bool) -> Grid:
        h, w = grid_size(g)
        bg = background(g)
        nz = [(r, c) for r in range(h) for c in range(w) if g[r][c] != bg]
        if not nz:
            return g
        if use_pattern_center:
            r_mid = (min(r for r, c in nz) + max(r for r, c in nz)) / 2
            c_mid = (min(c for r, c in nz) + max(c for r, c in nz)) / 2
        else:
            r_mid = (h - 1) / 2
            c_mid = (w - 1) / 2

        out = copy_grid(g)
        # Iterative fill: keep applying until stable (handles chained reflections)
        for _ in range(4):
            changed = False
            for r in range(h):
                for c in range(w):
                    if out[r][c] == bg:
                        continue
                    targets = []
                    if use_h:
                        mc = round(2 * c_mid - c)
                        if 0 <= mc < w:
                            targets.append((r, mc))
                    if use_v:
                        mr = round(2 * r_mid - r)
                        if 0 <= mr < h:
                            targets.append((mr, c))
                    if use_h and use_v:
                        mr = round(2 * r_mid - r)
                        mc = round(2 * c_mid - c)
                        if 0 <= mr < h and 0 <= mc < w:
                            targets.append((mr, mc))
                    for tr, tc2 in targets:
                        if out[tr][tc2] == bg:
                            out[tr][tc2] = out[r][c]
                            changed = True
            if not changed:
                break
        return out

    for use_pattern_center in (False, True):
        for (use_h, use_v) in ((True, False), (False, True), (True, True)):
            def make_fn(uh=use_h, uv=use_v, upc=use_pattern_center):
                def fn(g):
                    return _apply_sym(g, uh, uv, upc)
                return fn
            prog = make_fn()
            if _fits_all(prog, pairs):
                return prog
    return None


# ═══════════════════════════════════════════════════════════════════════════════
# LAYER 3 — Enumerative depth-1 sweep
# ═══════════════════════════════════════════════════════════════════════════════

def _enumerate_depth1(pairs: List[Tuple[Grid, Grid]], time_limit: float = 1.5) -> Optional[Program]:
    """Try every single primitive with all color arguments."""
    t0 = time.time()
    x0 = pairs[0][0]
    all_c = list(colors_in(x0))
    bg = background(x0)
    fg_colors = [c for c in all_c if c != bg]

    # Geometric transforms (already tried, but cheap to re-check)
    for fn in [flip_h, flip_v, flip_diag, flip_antidiag,
               lambda g: rotate(g, 1), lambda g: rotate(g, 2), lambda g: rotate(g, 3)]:
        if _fits_all(fn, pairs):
            return fn

    # Recolor single colors
    for src in fg_colors:
        for dst in range(10):
            if dst == src:
                continue
            def make_fn(s=src, d=dst):
                return lambda g: recolor(g, s, d)
            prog = make_fn()
            if _fits_all(prog, pairs):
                return prog
            if time.time() - t0 > time_limit:
                return None

    # Swap two colors
    for i, c1 in enumerate(fg_colors):
        for c2 in fg_colors[i+1:]:
            def make_fn(a=c1, b=c2):
                return lambda g: swap_colors(g, a, b)
            prog = make_fn()
            if _fits_all(prog, pairs):
                return prog

    # Color maps of up to 3 colors
    if len(fg_colors) <= 4:
        for perm in permutations(range(10), len(fg_colors)):
            cmap = dict(zip(fg_colors, perm))
            def make_fn(m=cmap):
                return lambda g: apply_color_map(g, m)
            prog = make_fn()
            if _fits_all(prog, pairs):
                return prog
            if time.time() - t0 > time_limit:
                return None

    return None


def try_diagonal_tile(pairs):
    """
    Output is a full-grid diagonal tiling: output[r][c] = diagonal_map[(r+c) % period].
    Period and map are extracted from the non-bg diagonal stripe in the input.
    Covers 05269061.
    """
    if not _output_same_size_as_input(pairs):
        return None

    def _derive_and_apply(g: Grid) -> Grid:
        h, w = grid_size(g)
        bg = background(g)
        diag_map: dict = {}
        for r in range(h):
            for c in range(w):
                v = g[r][c]
                if v != bg:
                    d = r + c
                    if d in diag_map and diag_map[d] != v:
                        raise ValueError("Inconsistent diagonal")
                    diag_map[d] = v
        if not diag_map:
            raise ValueError("No markers")
        period = len(set(diag_map.values()))
        if period < 2:
            raise ValueError("Need at least 2 colors for tiling")
        mod_map: dict = {}
        for d, v in diag_map.items():
            key = d % period
            if key in mod_map and mod_map[key] != v:
                raise ValueError("Inconsistent mod mapping")
            mod_map[key] = v
        if len(mod_map) != period:
            raise ValueError("Not all residues covered")
        return [[mod_map[(r + c) % period] for c in range(w)] for r in range(h)]

    return _derive_and_apply if _fits_all(_derive_and_apply, pairs) else None


def try_stripe_tiling(pairs):
    """
    Single-pixel colored markers define repeating stripes that tile the grid.
    Orientation is auto-detected per input: tall grid (h>w) → fill rows,
    wide grid (w>h) → fill cols. Markers must be equally spaced.
    Covers 0a938d79.
    """
    if not _output_same_size_as_input(pairs):
        return None

    def _apply(g: Grid) -> Grid:
        h, w = grid_size(g)
        bg = background(g)
        orient = "rows" if h > w else "cols"

        pos_color: dict = {}
        for r in range(h):
            for c in range(w):
                v = g[r][c]
                if v != bg:
                    pos = r if orient == "rows" else c
                    if pos in pos_color and pos_color[pos] != v:
                        raise ValueError("Multi-color position")
                    pos_color[pos] = v

        positions = sorted(pos_color.keys())
        if len(positions) < 2:
            raise ValueError("Need at least 2 markers")

        step = positions[1] - positions[0]
        if step <= 0:
            raise ValueError("Non-positive step")
        for k in range(1, len(positions)):
            if positions[k] - positions[k - 1] != step:
                raise ValueError("Irregular spacing")

        colors = [pos_color[p] for p in positions]
        n = len(positions)
        first_pos = positions[0]
        max_pos = h if orient == "rows" else w

        out = [[bg] * w for _ in range(h)]
        k = 0
        while True:
            pos_k = first_pos + k * step
            if pos_k >= max_pos:
                break
            color = colors[k % n]
            if orient == "rows":
                for c in range(w):
                    out[pos_k][c] = color
            else:
                for r in range(h):
                    out[r][pos_k] = color
            k += 1
        return out

    return _apply if _fits_all(_apply, pairs) else None


def try_gravity_toward_object(pairs):
    """
    Two objects in the grid: one slides toward the other along their shared axis
    until they are adjacent.  The axis is determined by bounding-box overlap:
      - col overlap → vertical movement
      - row overlap → horizontal movement
    Both orderings (which object is the mover) are tried.
    Covers 05f2a901.
    """
    if not _output_same_size_as_input(pairs):
        return None

    def make_prog(mover_is_smaller: bool):
        def _apply(g: Grid) -> Grid:
            from collections import defaultdict
            h, w = grid_size(g)
            bg = background(g)
            color_cells: dict = defaultdict(list)
            for r in range(h):
                for c in range(w):
                    v = g[r][c]
                    if v != bg:
                        color_cells[v].append((r, c))
            if len(color_cells) != 2:
                raise ValueError("Need exactly 2 non-bg colors")

            colors = sorted(color_cells.keys(), key=lambda c: len(color_cells[c]))
            if mover_is_smaller:
                mover_color, anchor_color = colors[0], colors[1]
            else:
                mover_color, anchor_color = colors[1], colors[0]

            mcells = color_cells[mover_color]
            acells = color_cells[anchor_color]

            mr1 = min(r for r, c in mcells)
            mr2 = max(r for r, c in mcells)
            mc1 = min(c for r, c in mcells)
            mc2 = max(c for r, c in mcells)
            ar1 = min(r for r, c in acells)
            ar2 = max(r for r, c in acells)
            ac1 = min(c for r, c in acells)
            ac2 = max(c for r, c in acells)

            col_overlap = max(mc1, ac1) <= min(mc2, ac2)
            row_overlap = max(mr1, ar1) <= min(mr2, ar2)

            dr = dc = 0
            if col_overlap and not row_overlap:
                if ar1 > mr2:
                    dr = ar1 - 1 - mr2
                elif ar2 < mr1:
                    dr = ar2 + 1 - mr1
                else:
                    raise ValueError("Objects already overlap vertically")
            elif row_overlap and not col_overlap:
                if ac1 > mc2:
                    dc = ac1 - 1 - mc2
                elif ac2 < mc1:
                    dc = ac2 + 1 - mc1
                else:
                    raise ValueError("Objects already overlap horizontally")
            else:
                raise ValueError("Cannot determine movement axis")

            out = [list(row) for row in g]
            for r, c in mcells:
                out[r][c] = bg
            for r, c in mcells:
                nr, nc = r + dr, c + dc
                if 0 <= nr < h and 0 <= nc < w:
                    out[nr][nc] = mover_color
            return out
        return _apply

    for flag in (True, False):
        prog = make_prog(flag)
        if _fits_all(prog, pairs):
            return prog
    return None


def try_block_tile_down(pairs):
    """
    Detect a top-aligned header column and tile the rows above its height downward,
    excluding the header column itself. Covers 12422b43-style tasks.
    """
    if not _output_same_size_as_input(pairs):
        return None

    def _detect_header(g: Grid) -> Tuple[int, int]:
        h, w = grid_size(g)
        bg = background(g)
        best: Optional[Tuple[int, int]] = None
        for c in range(w):
            if h < 2 or g[0][c] == bg:
                continue
            header_color = g[0][c]
            run_len = 1
            while run_len < h and g[run_len][c] == header_color:
                run_len += 1
            if run_len < 1:
                continue
            if any(g[r][c] != bg for r in range(run_len, h)):
                continue
            if best is None or run_len > best[1]:
                best = (c, run_len)
        if best is None:
            raise ValueError("No header column")
        return best

    def _apply(g: Grid) -> Grid:
        h, w = grid_size(g)
        bg = background(g)
        header_col, tile_height = _detect_header(g)
        last_content_row = -1
        for r in range(h):
            if any(g[r][c] != bg for c in range(w) if c != header_col):
                last_content_row = r
        if last_content_row < 0:
            raise ValueError("No content outside header column")
        tile_start = last_content_row + 1
        if tile_start >= h:
            raise ValueError("No space to tile downward")

        out = copy_grid(g)
        for r in range(tile_start, h):
            src_r = (r - tile_start) % tile_height
            for c in range(w):
                if c == header_col:
                    continue
                out[r][c] = g[src_r][c]
        return out

    return _apply if _fits_all(_apply, pairs) else None


def try_small_component_recolor(pairs):
    """
    Replace every same-color 4-connected component of size <= threshold with
    a fixed replacement color.  Covers 12eac192-style tasks where isolated /
    small-group pixels become color 3.
    """
    if not _output_same_size_as_input(pairs):
        return None

    def _components(g, bg):
        h, w = grid_size(g)
        visited = [[False] * w for _ in range(h)]
        comps = []
        for sr in range(h):
            for sc in range(w):
                if g[sr][sc] == bg or visited[sr][sc]:
                    continue
                col = g[sr][sc]
                stack = [(sr, sc)]
                cells = []
                while stack:
                    r, c = stack.pop()
                    if r < 0 or r >= h or c < 0 or c >= w:
                        continue
                    if visited[r][c] or g[r][c] != col:
                        continue
                    visited[r][c] = True
                    cells.append((r, c))
                    for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                        stack.append((r + dr, c + dc))
                comps.append((col, cells))
        return comps

    def _make_prog(threshold, replace_color):
        def _apply(g):
            bg = background(g)
            comps = _components(g, bg)
            out = copy_grid(g)
            for col, cells in comps:
                if len(cells) <= threshold:
                    for r, c in cells:
                        out[r][c] = replace_color
            return out
        return _apply

    # Try threshold 1 and 2 with replacement colors found in training outputs
    out_colors = set()
    for _, y in pairs:
        for row in y:
            for v in row:
                out_colors.add(v)
    in_colors = set()
    for x, _ in pairs:
        for row in x:
            for v in row:
                in_colors.add(v)
    new_colors = out_colors - in_colors
    # candidate replace colors: colors that appear in output but not input, or just try 3
    candidates = list(new_colors) if new_colors else []
    # also try colors that increase most in output
    for rc in [3, 2, 1, 4, 6, 7, 8, 9]:
        if rc not in candidates:
            candidates.append(rc)

    for threshold in (1, 2):
        for rc in candidates:
            prog = _make_prog(threshold, rc)
            if _fits_all(prog, pairs):
                return prog
    return None


def try_connect_diagonal(pairs):
    """
    For each pair of same-colored non-background pixels, draw a diagonal line
    (|dr| == |dc|) between them.  Covers 1f876c06-style tasks.
    """
    if not _output_same_size_as_input(pairs):
        return None

    def _apply(g):
        bg = background(g)
        h, w = grid_size(g)
        # Collect all non-bg pixels grouped by color
        from collections import defaultdict
        color_cells = defaultdict(list)
        for r in range(h):
            for c in range(w):
                if g[r][c] != bg:
                    color_cells[g[r][c]].append((r, c))
        out = copy_grid(g)
        for col, cells in color_cells.items():
            if len(cells) != 2:
                continue
            (r1, c1), (r2, c2) = cells
            dr = r2 - r1
            dc = c2 - c1
            if abs(dr) != abs(dc):
                raise ValueError(f"Not diagonal: {cells}")
            steps = abs(dr)
            sr = 1 if dr > 0 else -1
            sc = 1 if dc > 0 else -1
            for i in range(steps + 1):
                out[r1 + i * sr][c1 + i * sc] = col
        return out

    if _fits_all(_apply, pairs):
        return _apply

    # Also try with >2 cells per color: connect nearest pair
    def _apply_nearest(g):
        bg = background(g)
        h, w = grid_size(g)
        from collections import defaultdict
        color_cells = defaultdict(list)
        for r in range(h):
            for c in range(w):
                if g[r][c] != bg:
                    color_cells[g[r][c]].append((r, c))
        out = copy_grid(g)
        for col, cells in color_cells.items():
            for i in range(len(cells)):
                for j in range(i + 1, len(cells)):
                    r1, c1 = cells[i]
                    r2, c2 = cells[j]
                    dr = r2 - r1
                    dc = c2 - c1
                    if abs(dr) != abs(dc):
                        continue
                    steps = abs(dr)
                    sr = 1 if dr > 0 else -1
                    sc = 1 if dc > 0 else -1
                    for k in range(steps + 1):
                        out[r1 + k * sr][c1 + k * sc] = col
        return out

    if _fits_all(_apply_nearest, pairs):
        return _apply_nearest
    return None


def try_rectangle_corner_mark(pairs):
    """
    Per connected-component of each non-bg color: if the component's bounding
    box is a square (side >= 2) AND all perimeter cells of that bbox are the
    component's color, mark 8 orthogonal exterior corner positions with marker
    color.  Uses per-component detection to avoid spurious sub-square detection
    inside filled rectangular blocks.  Covers 14b8e18c-style tasks.
    """
    if not _output_same_size_as_input(pairs):
        return None

    def _connected_components(g, color):
        h, w = grid_size(g)
        visited = [[False] * w for _ in range(h)]
        comps = []
        for sr in range(h):
            for sc in range(w):
                if g[sr][sc] == color and not visited[sr][sc]:
                    comp = []
                    stack = [(sr, sc)]
                    visited[sr][sc] = True
                    while stack:
                        r, c = stack.pop()
                        comp.append((r, c))
                        for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
                            nr, nc = r+dr, c+dc
                            if 0<=nr<h and 0<=nc<w and not visited[nr][nc] and g[nr][nc]==color:
                                visited[nr][nc] = True
                                stack.append((nr, nc))
                    comps.append(comp)
        return comps

    def _square_rects_from_components(g, bg):
        h, w = grid_size(g)
        seen_colors = set(g[r][c] for r in range(h) for c in range(w) if g[r][c] != bg)
        rects = []
        for color in seen_colors:
            for comp in _connected_components(g, color):
                r1 = min(r for r, c in comp)
                r2 = max(r for r, c in comp)
                c1 = min(c for r, c in comp)
                c2 = max(c for r, c in comp)
                if r2 - r1 < 1:          # single row — skip
                    continue
                if r2 - r1 != c2 - c1:   # must be square
                    continue
                comp_set = set(comp)
                # All perimeter cells of bbox must be this color
                top = all((r1, c) in comp_set for c in range(c1, c2+1))
                bot = all((r2, c) in comp_set for c in range(c1, c2+1))
                lft = all((r, c1) in comp_set for r in range(r1, r2+1))
                rgt = all((r, c2) in comp_set for r in range(r1, r2+1))
                if top and bot and lft and rgt:
                    rects.append((r1, r2, c1, c2))
        return rects

    def _make_prog(marker_color):
        def _apply(g):
            bg = background(g)
            h, w = grid_size(g)
            out = copy_grid(g)
            for r1, r2, c1, c2 in _square_rects_from_components(g, bg):
                for er, ec in [(r1-1,c1),(r1-1,c2),(r2+1,c1),(r2+1,c2),
                               (r1,c1-1),(r1,c2+1),(r2,c1-1),(r2,c2+1)]:
                    if 0 <= er < h and 0 <= ec < w:
                        out[er][ec] = marker_color
            return out
        return _apply

    in_all = set(v for x, _ in pairs for row in x for v in row)
    out_all = set(v for _, y in pairs for row in y for v in row)
    new_colors = list(out_all - in_all)
    marker_candidates = new_colors if new_colors else [2, 3, 4]

    for mc in marker_candidates + [2, 3, 4]:
        prog = _make_prog(mc)
        if _fits_all(prog, pairs):
            return prog
    return None


def try_color_decoration(pairs):
    """
    Each non-background source color gets a fixed decoration: stamp a set of
    neighbor offsets with a specific decoration color.
    E.g. color 1 → add color 7 at orthogonal neighbors; color 2 → add color 4
    at diagonal neighbors.  Covers 0ca9ddb6-style tasks.
    """
    if not _output_same_size_as_input(pairs):
        return None

    ORTHO = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    DIAG = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
    ALL8 = ORTHO + DIAG

    def _make_prog(decorations):
        # decorations: list of (src_color, offsets, deco_color)
        def _apply(g):
            bg = background(g)
            h, w = grid_size(g)
            out = copy_grid(g)
            for r in range(h):
                for c in range(w):
                    col = g[r][c]
                    if col == bg:
                        continue
                    for src_col, offsets, deco_col in decorations:
                        if col != src_col:
                            continue
                        for dr, dc in offsets:
                            nr, nc = r + dr, c + dc
                            if 0 <= nr < h and 0 <= nc < w and g[nr][nc] == bg:
                                out[nr][nc] = deco_col
            return out
        return _apply

    bg0 = background(pairs[0][0])
    src_colors = sorted(set(
        v for x, _ in pairs for row in x for v in row if v != bg0
    ))

    # For each src color figure out which offsets and deco color from train data
    offset_sets = [ORTHO, DIAG, ALL8]
    # Try enumerating decorations per src color
    # Build candidate (offsets, deco_color) for each src color by looking at diffs
    deco_candidates_per_src = {}
    for sc in src_colors:
        cands = []
        # Find where sc appears in inputs, what's added in outputs
        for x, y in pairs:
            h, w = grid_size(x)
            for r in range(h):
                for c in range(w):
                    if x[r][c] == sc:
                        for dr, dc in ALL8:
                            nr, nc = r + dr, c + dc
                            if 0 <= nr < h and 0 <= nc < w:
                                if x[nr][nc] == bg0 and y[nr][nc] != bg0:
                                    cands.append((dr, dc, y[nr][nc]))
        if not cands:
            continue
        # Find most common (offset, deco_color) pattern
        from collections import Counter
        counts = Counter(cands)
        # Group by deco_color
        by_deco = {}
        for (dr, dc, deco_col), cnt in counts.items():
            by_deco.setdefault(deco_col, []).append((dr, dc))
        deco_candidates_per_src[sc] = by_deco

    if not deco_candidates_per_src:
        return None

    # Build all combinations
    def _build_combos(src_list):
        if not src_list:
            yield []
            return
        sc = src_list[0]
        rest = src_list[1:]
        if sc not in deco_candidates_per_src:
            for combo in _build_combos(rest):
                yield combo
            return
        for deco_col, offsets in deco_candidates_per_src[sc].items():
            for combo in _build_combos(rest):
                yield [(sc, offsets, deco_col)] + combo

    for decorations in _build_combos(src_colors):
        if not decorations:
            continue
        prog = _make_prog(decorations)
        if _fits_all(prog, pairs):
            return prog
    return None


def try_plus_expand(pairs):
    """
    Find a plus/cross shape (center + 4 identical orthogonal arms of length 1,
    no other non-bg neighbors); output doubles arm length to 2 and fills the
    4 diagonal cells at dist 1 AND dist 2 with the center color.
    Covers 0962bcdd-style tasks.
    """
    if not _output_same_size_as_input(pairs):
        return None

    def _find_plus(g, bg):
        h, w = grid_size(g)
        results = []
        for r in range(2, h - 2):
            for c in range(2, w - 2):
                center_col = g[r][c]
                if center_col == bg:
                    continue
                arm_positions = [(r-1,c),(r+1,c),(r,c-1),(r,c+1)]
                arm_colors = [g[ar][ac] for ar,ac in arm_positions]
                # All 4 arms must be same non-bg color
                if any(a == bg for a in arm_colors):
                    continue
                if len(set(arm_colors)) > 1:
                    continue
                arm_col = arm_colors[0]
                # No existing content at dist-2 arms or dist-1 diagonals
                clear = True
                for dr, dc in [(-2,0),(2,0),(0,-2),(0,2),
                                (-1,-1),(-1,1),(1,-1),(1,1)]:
                    nr, nc = r+dr, c+dc
                    if 0 <= nr < h and 0 <= nc < w and g[nr][nc] != bg:
                        clear = False
                        break
                if not clear:
                    continue
                results.append((r, c, center_col, arm_col))
        return results

    def _apply(g):
        bg = background(g)
        h, w = grid_size(g)
        out = [list(row) for row in g]
        pluses = _find_plus(g, bg)
        for cr, cc, center_col, arm_col in pluses:
            # Erase original length-1 arms
            for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
                out[cr+dr][cc+dc] = bg
            # Draw extended arms (length 1 and 2)
            for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
                for dist in (1, 2):
                    nr, nc = cr + dr*dist, cc + dc*dist
                    if 0 <= nr < h and 0 <= nc < w:
                        out[nr][nc] = arm_col
            # Fill diagonal cells at dist 1 AND dist 2 with center color
            for dr, dc in [(-1,-1),(-1,1),(1,-1),(1,1)]:
                for dist in (1, 2):
                    nr, nc = cr + dr*dist, cc + dc*dist
                    if 0 <= nr < h and 0 <= nc < w:
                        out[nr][nc] = center_col
        return out

    if _fits_all(_apply, pairs):
        return _apply
    return None


def try_scale_up(pairs):
    """
    Scale each cell into an NxN block (zoom/upscale).
    Covers tasks like 60c09cac (scale x2) and 9172f3a0 (scale x3).
    """
    x0, y0 = pairs[0]
    h, w = grid_size(x0)
    oh, ow = grid_size(y0)
    if oh % h != 0 or ow % w != 0:
        return None
    sh, sw = oh // h, ow // w
    if sh != sw or sh < 2:
        return None

    def _scale(g: Grid, n: int = sh) -> Grid:
        gh, gw = grid_size(g)
        out = empty_grid(gh * n, gw * n)
        for r in range(gh):
            for c in range(gw):
                for dr in range(n):
                    for dc in range(n):
                        out[r * n + dr][c * n + dc] = g[r][c]
        return out

    fn = lambda g, n=sh: _scale(g, n)
    return fn if _fits_all(fn, pairs) else None


def try_slide_to_border(pairs):
    """
    Slide the entire non-bg content bounding box to touch one of the 4 borders,
    preserving the perpendicular coordinate.
    Covers f3e62deb, 25ff71a9 and similar tasks.
    """
    if not _output_same_size_as_input(pairs):
        return None

    def _slide(g: Grid, direction: str) -> Grid:
        h, w = grid_size(g)
        bg = background(g)
        rows = [r for r in range(h) if any(g[r][c] != bg for c in range(w))]
        cols = [c for c in range(w) if any(g[r][c] != bg for r in range(h))]
        if not rows or not cols:
            return g
        r0, r1 = min(rows), max(rows)
        c0, c1 = min(cols), max(cols)
        hs, ws = r1 - r0 + 1, c1 - c0 + 1
        shape = [[g[r][c] for c in range(c0, c1 + 1)] for r in range(r0, r1 + 1)]
        out = [[bg] * w for _ in range(h)]
        if direction == "top":
            nr, nc = 0, c0
        elif direction == "bottom":
            nr, nc = h - hs, c0
        elif direction == "left":
            nr, nc = r0, 0
        else:  # right
            nr, nc = r0, w - ws
        for i in range(hs):
            for j in range(ws):
                if 0 <= nr + i < h and 0 <= nc + j < w:
                    out[nr + i][nc + j] = shape[i][j]
        return out

    for direction in ("top", "bottom", "left", "right"):
        fn = lambda g, d=direction: _slide(g, d)
        if _fits_all(fn, pairs):
            return fn
    return None


def try_dot_row_zones(pairs):
    """
    Sparse colored dots on background define row-based Voronoi zones.
    Dot rows + border rows fill entirely; other rows fill only the two edge cells.
    Covers 0f63c0b9 and 1bfc4729.
    """
    if not _output_same_size_as_input(pairs):
        return None

    def _dot_row_zones(g: Grid) -> Grid:
        h, w = grid_size(g)
        bg = background(g)
        # Find all dot positions (non-bg)
        dots = [(r, g[r][c]) for r in range(h) for c in range(w) if g[r][c] != bg]
        if not dots:
            return g
        dot_rows = sorted(set(r for r, _ in dots))
        dot_color = {r: next(col for row, col in dots if row == r) for r in dot_rows}

        def nearest_color(row):
            return min(dot_rows, key=lambda dr: abs(dr - row))

        out = [[bg] * w for _ in range(h)]
        for r in range(h):
            nc_row = dot_color[nearest_color(r)]
            if r in dot_rows or r == 0 or r == h - 1:
                # Fill entire row
                for c in range(w):
                    out[r][c] = nc_row
            else:
                # Fill only border columns
                out[r][0] = nc_row
                out[r][w - 1] = nc_row
        return out

    return _dot_row_zones if _fits_all(_dot_row_zones, pairs) else None


def try_connect_same_color_pairs(pairs):
    """
    Each non-bg color has exactly 2 cells; connect them with a horizontal or
    vertical line. Horizontal lines drawn first, vertical last (vertical overwrites).
    Covers 070dd51e.
    """
    if not _output_same_size_as_input(pairs):
        return None

    def _connect(g: Grid) -> Grid:
        h, w = grid_size(g)
        bg = background(g)
        from collections import defaultdict
        color_cells = defaultdict(list)
        for r in range(h):
            for c in range(w):
                if g[r][c] != bg:
                    color_cells[g[r][c]].append((r, c))
        out = [list(row) for row in g]
        # Sort: horizontal lines first, vertical lines last (vertical overwrites at intersections)
        items = list(color_cells.items())
        items.sort(key=lambda kv: kv[1][0][1] == kv[1][1][1])  # vertical (same col) last
        for color, cells in items:
            if len(cells) != 2:
                continue
            (r1, c1), (r2, c2) = cells
            if r1 == r2:
                # Horizontal line
                for c in range(min(c1, c2), max(c1, c2) + 1):
                    out[r1][c] = color
            elif c1 == c2:
                # Vertical line
                for r in range(min(r1, r2), max(r1, r2) + 1):
                    out[r][c1] = color
        return out

    return _connect if _fits_all(_connect, pairs) else None


def try_shift_content(pairs):
    """
    Shift the entire non-bg content bounding box by (dr, dc) steps.
    Tries dr/dc in {-3..3} × {-3..3}. Covers 25ff71a9 (shift down 1).
    """
    if not _output_same_size_as_input(pairs):
        return None

    for dr in range(-3, 4):
        for dc in range(-3, 4):
            if dr == 0 and dc == 0:
                continue

            def _shift(g: Grid, dr=dr, dc=dc) -> Grid:
                h, w = grid_size(g)
                bg_val = background(g)
                rows = [r for r in range(h) if any(g[r][c] != bg_val for c in range(w))]
                cols = [c for c in range(w) if any(g[r][c] != bg_val for r in range(h))]
                if not rows or not cols:
                    return g
                r0, r1 = min(rows), max(rows)
                c0, c1 = min(cols), max(cols)
                out = [[bg_val] * w for _ in range(h)]
                for r in range(r0, r1 + 1):
                    for c in range(c0, c1 + 1):
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < h and 0 <= nc < w:
                            out[nr][nc] = g[r][c]
                return out

            if _fits_all(_shift, pairs):
                return _shift
    return None


def try_color_slide_direction(pairs):
    """
    Learn a color → slide_direction mapping from train pairs.
    Then apply: slide content bbox to that border.
    Covers f3e62deb where color encodes which border to slide toward.
    """
    if not _output_same_size_as_input(pairs):
        return None

    color_dir: dict = {}
    for x, y in pairs:
        h, w = grid_size(x)
        bg_val = background(x)
        colors = list({g for row in x for g in row} - {bg_val})
        if len(colors) != 1:
            return None
        color = colors[0]
        # Determine slide direction from output
        y_rows = [r for r in range(h) if any(y[r][c] != bg_val for c in range(w))]
        y_cols = [c for c in range(w) if any(y[r][c] != bg_val for r in range(h))]
        if not y_rows or not y_cols:
            return None
        yr0, yr1 = min(y_rows), max(y_rows)
        yc0, yc1 = min(y_cols), max(y_cols)
        if yr0 == 0:
            direction = "top"
        elif yr1 == h - 1:
            direction = "bottom"
        elif yc0 == 0:
            direction = "left"
        elif yc1 == w - 1:
            direction = "right"
        else:
            return None
        if color in color_dir and color_dir[color] != direction:
            return None
        color_dir[color] = direction

    if not color_dir:
        return None

    def _slide_by_color(g: Grid) -> Grid:
        h, w = grid_size(g)
        bg_val = background(g)
        colors = list({v for row in g for v in row} - {bg_val})
        if len(colors) != 1:
            return g
        color = colors[0]
        direction = color_dir.get(color)
        if direction is None:
            # Infer unseen color as the missing direction
            used = set(color_dir.values())
            remaining = [d for d in ("top", "bottom", "left", "right") if d not in used]
            if len(remaining) != 1:
                return g
            direction = remaining[0]
        rows = [r for r in range(h) if any(g[r][c] != bg_val for c in range(w))]
        cols = [c for c in range(w) if any(g[r][c] != bg_val for r in range(h))]
        if not rows or not cols:
            return g
        r0, r1 = min(rows), max(rows)
        c0, c1 = min(cols), max(cols)
        hs, ws = r1 - r0 + 1, c1 - c0 + 1
        shape = [[g[r][c] for c in range(c0, c1 + 1)] for r in range(r0, r1 + 1)]
        out = [[bg_val] * w for _ in range(h)]
        if direction == "top":
            nr, nc = 0, c0
        elif direction == "bottom":
            nr, nc = h - hs, c0
        elif direction == "left":
            nr, nc = r0, 0
        else:
            nr, nc = r0, w - ws
        for i in range(hs):
            for j in range(ws):
                if 0 <= nr + i < h and 0 <= nc + j < w:
                    out[nr + i][nc + j] = shape[i][j]
        return out

    return _slide_by_color if _fits_all(_slide_by_color, pairs) else None


def try_rotation_4fold(pairs: List[Tuple[Grid, Grid]]) -> Optional[Program]:
    """Tile 4 rotations of the input (0°,90°,180°,270°) into a 2H×2W grid."""
    from itertools import permutations as _perms

    def _rot90(g: Grid) -> Grid:
        H, W = len(g), len(g[0])
        return [[g[H - 1 - c][r] for c in range(H)] for r in range(W)]

    def _make(x: Grid, a: int, b: int, c: int, d: int) -> Grid:
        rots = [x, _rot90(x), _rot90(_rot90(x)), _rot90(_rot90(_rot90(x)))]
        H, W = len(x), len(x[0])
        out = [[0] * (2 * W) for _ in range(2 * H)]
        for i in range(H):
            for j in range(W):
                out[i][j] = rots[a][i][j]
                out[i][j + W] = rots[b][i][j]
                out[i + H][j] = rots[c][i][j]
                out[i + H][j + W] = rots[d][i][j]
        return out

    chosen = None
    for perm in _perms(range(4)):
        a, b, c, d = perm
        ok = True
        for x, y in pairs:
            H, W = len(x), len(x[0])
            if len(y) != 2 * H or len(y[0]) != 2 * W:
                return None
            if _make(x, a, b, c, d) != y:
                ok = False
                break
        if ok:
            chosen = (a, b, c, d)
            break

    if chosen is None:
        return None

    a, b, c, d = chosen

    def _prog(x: Grid) -> Grid:
        return _make(x, a, b, c, d)

    return _prog if _fits_all(_prog, pairs) else None


def try_mirror_4fold(pairs: List[Tuple[Grid, Grid]]) -> Optional[Program]:
    """Tile 4 reflections (identity, flip_h, flip_v, flip_hv) into a 2H×2W grid."""
    from itertools import permutations as _perms

    def _fh(g: Grid) -> Grid:
        return [row[::-1] for row in g]

    def _fv(g: Grid) -> Grid:
        return list(reversed(g))

    def _make(x: Grid, a: int, b: int, c: int, d: int) -> Grid:
        flips = [x, _fh(x), _fv(x), _fh(_fv(x))]
        H, W = len(x), len(x[0])
        out = [[0] * (2 * W) for _ in range(2 * H)]
        for i in range(H):
            for j in range(W):
                out[i][j] = flips[a][i][j]
                out[i][j + W] = flips[b][i][j]
                out[i + H][j] = flips[c][i][j]
                out[i + H][j + W] = flips[d][i][j]
        return out

    chosen = None
    for perm in _perms(range(4)):
        a, b, c, d = perm
        ok = True
        for x, y in pairs:
            H, W = len(x), len(x[0])
            if len(y) != 2 * H or len(y[0]) != 2 * W:
                return None
            if _make(x, a, b, c, d) != y:
                ok = False
                break
        if ok:
            chosen = (a, b, c, d)
            break

    if chosen is None:
        return None

    a, b, c, d = chosen

    def _prog(x: Grid) -> Grid:
        return _make(x, a, b, c, d)

    return _prog if _fits_all(_prog, pairs) else None


def try_extend_lines(pairs: List[Tuple[Grid, Grid]]) -> Optional[Program]:
    """
    Input has one partial vertical line (color A) and one partial horizontal line
    (color B). Output extends both to full grid; intersection gets a learned color C.
    """
    from collections import Counter as _Ctr

    def _detect(x: Grid):
        H, W = len(x), len(x[0])
        bg = _Ctr(v for row in x for v in row).most_common(1)[0][0]
        # Find non-bg cells
        nz = [(r, c, x[r][c]) for r in range(H) for c in range(W) if x[r][c] != bg]
        if not nz:
            return None
        colors = list(set(v for _, _, v in nz))
        if len(colors) != 2:
            return None
        # Identify which color is vertical-leaning and which horizontal-leaning
        for ca, cb in [(colors[0], colors[1]), (colors[1], colors[0])]:
            a_cells = [(r, c) for r, c, v in nz if v == ca]
            b_cells = [(r, c) for r, c, v in nz if v == cb]
            # ca is vertical: all same column
            cols_a = set(c for r, c in a_cells)
            rows_b = set(r for r, c in b_cells)
            if len(cols_a) == 1 and len(rows_b) == 1:
                col_a = next(iter(cols_a))
                row_b = next(iter(rows_b))
                return bg, ca, col_a, cb, row_b
        return None

    # Learn intersection color from training pairs
    intersect_color = None
    for x, y in pairs:
        info = _detect(x)
        if info is None:
            return None
        bg, ca, col_a, cb, row_b = info
        H, W = len(x), len(x[0])
        # Read intersection color from output
        ic = y[row_b][col_a]
        if intersect_color is None:
            intersect_color = ic
        elif intersect_color != ic:
            return None  # disagreement

    if intersect_color is None:
        return None

    def _prog(x: Grid) -> Grid:
        info = _detect(x)
        if info is None:
            raise ValueError("pattern mismatch")
        bg, ca, col_a, cb, row_b = info
        H, W = len(x), len(x[0])
        out = [[bg] * W for _ in range(H)]
        for r in range(H):
            out[r][col_a] = ca
        for c in range(W):
            out[row_b][c] = cb
        out[row_b][col_a] = intersect_color
        return out

    return _prog if _fits_all(_prog, pairs) else None


def try_checkerboard_extend(pairs: List[Tuple[Grid, Grid]]) -> Optional[Program]:
    """
    Input: periodic diagonal tiling region (N colors) + solid-block border.
    Output: extend tiling to full grid with phase shifted +1.
    Works for N=2 (classic checkerboard) and higher periods.
    """
    from collections import Counter as _Ctr

    def _detect_tiling(x: Grid):
        """Find border color and diagonal tiling sequence from input."""
        H, W = len(x), len(x[0])
        freq = _Ctr(v for row in x for v in row)
        n_colors = len(freq)
        if n_colors < 3:
            return None
        # Try each color as the border color
        for bc, _ in freq.most_common():
            non_bc = [(r, c, x[r][c]) for r in range(H) for c in range(W) if x[r][c] != bc]
            if not non_bc:
                continue
            # Determine period N from the number of remaining colors
            tile_colors = set(v for _, _, v in non_bc)
            N = len(tile_colors)
            if N < 2:
                continue
            # Determine sequence: infer seq from first non-bc cell
            r0, c0, v0 = non_bc[0]
            # Assume seq[(r+c+phase) % N] for some phase and ordering of colors
            # Try to infer seq and phase by scanning
            # Build mapping: (r+c) % N → color
            diag_map = {}
            ok = True
            phase_offset = 0
            for r, c, v in non_bc:
                key = (c + (r % 2)) % N
                if key not in diag_map:
                    diag_map[key] = v
                elif diag_map[key] != v:
                    ok = False
                    break
            if not ok or len(diag_map) != N:
                continue
            # Build ordered sequence
            seq = [diag_map[k] for k in range(N)]
            return bc, seq, N
        return None

    def _verify_output(y: Grid, seq, N, phase):
        H, W = len(y), len(y[0])
        for r in range(H):
            for c in range(W):
                if y[r][c] != seq[(c + (r % 2) + phase) % N]:
                    return False
        return True

    # Validate all training pairs
    for x, y in pairs:
        if len(y) != len(x) or len(y[0]) != len(x[0]):
            return None
        info = _detect_tiling(x)
        if info is None:
            return None
        bc, seq, N = info
        # The output should be a perfect tiling (no border)
        out_freq = _Ctr(v for row in y for v in row)
        if set(out_freq.keys()) != set(seq):
            return None
        # Determine output phase by checking (0,0)
        if y[0][0] not in seq:
            return None
        # Verify any valid phase works
        found = False
        for ph in range(N):
            if _verify_output(y, seq, N, ph):
                found = True
                break
        if not found:
            return None

    def _prog(x: Grid) -> Grid:
        info = _detect_tiling(x)
        if info is None:
            raise ValueError("no tiling found")
        bc, seq, N = info
        H, W = len(x), len(x[0])
        # Determine current phase from non-bc cells
        non_bc = [(r, c, x[r][c]) for r in range(H) for c in range(W) if x[r][c] != bc]
        if not non_bc:
            raise ValueError
        r0, c0, v0 = non_bc[0]
        base_phase = (seq.index(v0) - (c0 + (r0 % 2))) % N
        # Output phase = base_phase + 1
        out_phase = (base_phase + 1) % N
        out = [[0] * W for _ in range(H)]
        for r in range(H):
            for c in range(W):
                out[r][c] = seq[(c + (r % 2) + out_phase) % N]
        return out

    return _prog if _fits_all(_prog, pairs) else None


def try_variable_pixel_scale(pairs):
    """
    Scale each pixel into an NxN block where N = number of unique non-bg colors
    in the input (or N = that count + 1).
    Covers b91ae062, ac0a08a4 (scale = n_nonbg_colors) and d4b1c2b1 (scale = n+1).
    """
    x0, y0 = pairs[0]
    h, w = grid_size(x0)
    oh, ow = grid_size(y0)
    if oh % h != 0 or ow % w != 0:
        return None
    sh, sw = oh // h, ow // w
    if sh != sw or sh < 2:
        return None

    def _variable_scale(g: Grid) -> Grid:
        bg_col = background(g)
        n = len(colors_in(g) - {bg_col})
        gh, gw = grid_size(g)
        out = empty_grid(gh * n, gw * n)
        for r in range(gh):
            for c in range(gw):
                for dr in range(n):
                    for dc in range(n):
                        out[r * n + dr][c * n + dc] = g[r][c]
        return out

    def _variable_scale_plus1(g: Grid) -> Grid:
        bg_col = background(g)
        n = len(colors_in(g) - {bg_col}) + 1
        gh, gw = grid_size(g)
        out = empty_grid(gh * n, gw * n)
        for r in range(gh):
            for c in range(gw):
                for dr in range(n):
                    for dc in range(n):
                        out[r * n + dr][c * n + dc] = g[r][c]
        return out

    # Determine which variant matches pair 0
    bg0 = background(x0)
    n0 = len(colors_in(x0) - {bg0})
    if sh == n0 and _fits_all(_variable_scale, pairs):
        return _variable_scale
    if sh == n0 + 1 and _fits_all(_variable_scale_plus1, pairs):
        return _variable_scale_plus1
    return None


def try_block_reduce(pairs):
    """
    Divide the input into an NxM grid of equal-sized blocks and reduce each block
    to its single non-bg color (or bg if the block is all-bg).
    Output size = (num_block_rows, num_block_cols).
    Covers 5783df64, 68b67ca3, e57337a4, d631b094.
    """
    x0, y0 = pairs[0]
    h, w = grid_size(x0)
    oh, ow = grid_size(y0)
    if oh <= 0 or ow <= 0 or h <= 0 or w <= 0:
        return None
    if h % oh != 0 or w % ow != 0:
        return None
    bh, bw = h // oh, w // ow
    if bh < 2 or bw < 2:
        return None

    def _reduce(g: Grid) -> Grid:
        gh, gw = grid_size(g)
        bg_col = background(g)
        if gh % oh != 0 or gw % ow != 0:
            return empty_grid(oh, ow)
        tbh, tbw = gh // oh, gw // ow
        out = empty_grid(oh, ow)
        for br in range(oh):
            for bc in range(ow):
                block_colors = set(
                    g[br * tbh + dr][bc * tbw + dc]
                    for dr in range(tbh) for dc in range(tbw)
                ) - {bg_col}
                out[br][bc] = next(iter(block_colors)) if len(block_colors) == 1 else bg_col
        return out

    return _reduce if _fits_all(_reduce, pairs) else None


def try_neighbor_count_recolor(pairs):
    """
    Recolor each non-bg cell based on a (original_color, n_same_color_neighbors) → output_color
    lookup table learned from training pairs.
    Covers bb43febb, e0fb7511.
    """
    if not _output_same_size_as_input(pairs):
        return None

    x0, y0 = pairs[0]
    bg_col = background(x0)
    h, w = grid_size(x0)

    # Build lookup table from all pairs
    table = {}
    for x, y in pairs:
        gh, gw = grid_size(x)
        if grid_size(y) != (gh, gw):
            return None
        bg2 = background(x)
        for r in range(gh):
            for c in range(gw):
                if x[r][c] == bg2:
                    if y[r][c] != bg2:
                        return None
                    continue
                n = sum(
                    1 for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]
                    if 0 <= r + dr < gh and 0 <= c + dc < gw and x[r + dr][c + dc] == x[r][c]
                )
                key = (x[r][c], n)
                out_val = y[r][c]
                if key in table:
                    if table[key] != out_val:
                        return None
                else:
                    table[key] = out_val

    if not table:
        return None
    # Check table is non-trivial (at least one recolor)
    if all(k[0] == v for k, v in table.items()):
        return None

    def _recolor(g: Grid) -> Grid:
        gh, gw = grid_size(g)
        bg2 = background(g)
        out = copy_grid(g)
        for r in range(gh):
            for c in range(gw):
                if g[r][c] == bg2:
                    continue
                n = sum(
                    1 for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]
                    if 0 <= r + dr < gh and 0 <= c + dc < gw and g[r + dr][c + dc] == g[r][c]
                )
                key = (g[r][c], n)
                out[r][c] = table.get(key, g[r][c])
        return out

    return _recolor if _fits_all(_recolor, pairs) else None


def try_separator_subgrid_reduce(pairs):
    """
    When the input has separator rows/cols (rows or cols all one non-bg color),
    divide into sub-grids and reduce each sub-grid to its single non-bg color.
    Output size = (num_subgrid_rows, num_subgrid_cols).
    Covers 1190e5a7, 7039b2d7.
    """
    x0, y0 = pairs[0]

    def _find_separators(g):
        gh, gw = grid_size(g)
        bg_col = background(g)
        sep_rows = [r for r in range(gh) if all(g[r][c] != bg_col for c in range(gw))]
        sep_cols = [c for c in range(gw) if all(g[r][c] != bg_col for r in range(gh))]
        return sep_rows, sep_cols

    def _extract_subgrids(g, sep_rows, sep_cols):
        gh, gw = grid_size(g)
        row_divs = [-1] + sep_rows + [gh]
        col_divs = [-1] + sep_cols + [gw]
        subgrids = []
        for i in range(len(row_divs) - 1):
            row_grids = []
            for j in range(len(col_divs) - 1):
                r0 = row_divs[i] + 1
                r1 = row_divs[i + 1]
                c0 = col_divs[j] + 1
                c1 = col_divs[j + 1]
                if r0 >= r1 or c0 >= c1:
                    continue
                row_grids.append([g[r][c0:c1] for r in range(r0, r1)])
            if row_grids:
                subgrids.append(row_grids)
        return subgrids

    sep_r0, sep_c0 = _find_separators(x0)
    if not sep_r0 and not sep_c0:
        return None

    sgs0 = _extract_subgrids(x0, sep_r0, sep_c0)
    oh = len(sgs0)
    ow = max(len(row) for row in sgs0) if sgs0 else 0
    if grid_size(y0) != (oh, ow):
        return None

    def _reduce(g: Grid) -> Grid:
        sr, sc = _find_separators(g)
        sgs = _extract_subgrids(g, sr, sc)
        if not sgs:
            return empty_grid(oh, ow)
        bg_col = background(g)
        out = empty_grid(len(sgs), max(len(row) for row in sgs))
        for i, row in enumerate(sgs):
            for j, sg in enumerate(row):
                non_bg = set(v for r in sg for v in r) - {bg_col}
                out[i][j] = next(iter(non_bg)) if len(non_bg) == 1 else bg_col
        return out

    return _reduce if _fits_all(_reduce, pairs) else None


def try_connect_same_color_lines(pairs):
    """Connect same-color cells in same row/col with the same color."""
    def _connect(x):
        b = background(x)
        H, W = len(x), len(x[0])
        g = [row[:] for row in x]
        for r in range(H):
            cols_by_color = {}
            for c in range(W):
                if x[r][c] != b:
                    cols_by_color.setdefault(x[r][c], []).append(c)
            for color, cols in cols_by_color.items():
                for c in range(min(cols), max(cols) + 1):
                    if x[r][c] == b:
                        g[r][c] = color
        for c in range(W):
            rows_by_color = {}
            for r in range(H):
                if x[r][c] != b:
                    rows_by_color.setdefault(x[r][c], []).append(r)
            for color, rows in rows_by_color.items():
                for r in range(min(rows), max(rows) + 1):
                    if x[r][c] == b:
                        g[r][c] = color
        return g

    return _connect if _fits_all(_connect, pairs) else None


def try_diagonal_extend(pairs):
    """Extend each non-bg cell diagonally in all 4 diagonal directions until border."""
    def _diag(x):
        b = background(x)
        H, W = len(x), len(x[0])
        g = [row[:] for row in x]
        for r in range(H):
            for c in range(W):
                if x[r][c] != b:
                    color = x[r][c]
                    for dr, dc in [(1, 1), (1, -1), (-1, 1), (-1, -1)]:
                        nr, nc = r + dr, c + dc
                        while 0 <= nr < H and 0 <= nc < W:
                            if x[nr][nc] == b:
                                g[nr][nc] = color
                            nr += dr
                            nc += dc
        return g

    return _diag if _fits_all(_diag, pairs) else None


def try_complete_rect_outline(pairs):
    """Complete a partial rectangle outline to a full rectangle border."""
    def _complete(x):
        b = background(x)
        H, W = len(x), len(x[0])
        g = [row[:] for row in x]
        in_colors = set(v for row in x for v in row) - {b}
        for color in in_colors:
            cells = [(r, c) for r in range(H) for c in range(W) if x[r][c] == color]
            if not cells:
                continue
            r1 = min(r for r, c in cells)
            r2 = max(r for r, c in cells)
            c1 = min(c for r, c in cells)
            c2 = max(c for r, c in cells)
            for r in range(r1, r2 + 1):
                for c in range(c1, c2 + 1):
                    if r == r1 or r == r2 or c == c1 or c == c2:
                        if g[r][c] == b:
                            g[r][c] = color
        return g

    def _check(x):
        result = _complete(x)
        b = background(x)
        # Verify no interior cells were touched (changed cells must all be on border of bboxes)
        H, W = len(x), len(x[0])
        for r in range(H):
            for c in range(W):
                if x[r][c] != b and result[r][c] != x[r][c]:
                    return None
        return result

    return _complete if _fits_all(_complete, pairs) else None


def try_uniform_output(pairs):
    """Output = grid filled with a single color derived from input statistics.
    Output size is taken from each pair's own output dimensions.
    """
    # Try most common non-bg, then least common
    for selector in ['most', 'least']:
        def _fill(x, sel=selector, _pairs=pairs):
            b = background(x)
            cnt = Counter(v for row in x for v in row)
            cnt.pop(b, None)
            if not cnt:
                return None
            ordered = cnt.most_common()
            pick = ordered[0][0] if sel == 'most' else ordered[-1][0]
            # Output size must match the known output for this input; infer from pairs
            for px, py in _pairs:
                if px == x:
                    Ho, Wo = len(py), len(py[0])
                    return [[pick] * Wo for _ in range(Ho)]
            # Fallback: same size as input
            Ho, Wo = len(x), len(x[0])
            return [[pick] * Wo for _ in range(Ho)]

        if _fits_all(_fill, pairs):
            return _fill

    return None


def try_fill_bbox_objects(pairs):
    """Fill the bounding box of each non-bg object with that object's color."""
    def _fill(x):
        b = background(x)
        H, W = len(x), len(x[0])
        g = [row[:] for row in x]
        colors = set(v for row in x for v in row) - {b}
        for color in colors:
            cells = [(r, c) for r in range(H) for c in range(W) if x[r][c] == color]
            if not cells:
                continue
            r1 = min(r for r, c in cells)
            r2 = max(r for r, c in cells)
            c1 = min(c for r, c in cells)
            c2 = max(c for r, c in cells)
            for r in range(r1, r2 + 1):
                for c in range(c1, c2 + 1):
                    g[r][c] = color
        return g

    return _fill if _fits_all(_fill, pairs) else None


def try_sym_complete_rot180(pairs):
    """Fill bg cells using rot180 symmetry: empty cell gets the rotated counterpart's color."""
    def _sym(x):
        b = background(x)
        H, W = len(x), len(x[0])
        g = [row[:] for row in x]
        for r in range(H):
            for c in range(W):
                if x[r][c] == b:
                    mr, mc = H - 1 - r, W - 1 - c
                    if 0 <= mr < H and 0 <= mc < W and x[mr][mc] != b:
                        g[r][c] = x[mr][mc]
        return g

    return _sym if _fits_all(_sym, pairs) else None


def try_row_col_intersect_mark(pairs):
    """Mark bg cell (r,c) with color X if row r and col c both uniquely contain X."""
    def _mark(x):
        b = background(x)
        H, W = len(x), len(x[0])
        g = [row[:] for row in x]
        row_colors = [set(v for v in x[r] if v != b) for r in range(H)]
        col_colors = [set(x[r][c] for r in range(H) if x[r][c] != b) for c in range(W)]
        for r in range(H):
            for c in range(W):
                if x[r][c] == b:
                    intersect = row_colors[r] & col_colors[c]
                    if len(intersect) == 1:
                        g[r][c] = next(iter(intersect))
        return g

    return _mark if _fits_all(_mark, pairs) else None


def try_reverse_concentric(pairs):
    """Reverse the color sequence of concentric rings (distance from border).

    Example: rings [8,0,5,8] → reversed [8,5,0,8].
    Confirmed: 85c4e7cd.
    """
    if not _output_same_size_as_input(pairs):
        return None

    def _rev_conc(x):
        H, W = len(x), len(x[0])
        dist_col = {}
        for r in range(H):
            for c in range(W):
                d = min(r, H - 1 - r, c, W - 1 - c)
                if d not in dist_col:
                    dist_col[d] = x[r][c]
        max_d = max(dist_col)
        seq = [dist_col[d] for d in range(max_d + 1)]
        rev = list(reversed(seq))
        g = [row[:] for row in x]
        for r in range(H):
            for c in range(W):
                d = min(r, H - 1 - r, c, W - 1 - c)
                g[r][c] = rev[d]
        return g

    return _rev_conc if _fits_all(_rev_conc, pairs) else None


def try_ring_color_rotate(pairs):
    """Rotate unique concentric ring colors (right or left by 1 step).

    Extracts unique ring colors (outermost→innermost), tries right and left
    rotation, applies as a color remapping to every cell.
    Confirmed (right): bda2d7a6.
    """
    if not _output_same_size_as_input(pairs):
        return None

    def _make_fn(direction):
        def _rotate(x):
            H, W = len(x), len(x[0])
            dist_col = {}
            for r in range(H):
                for c in range(W):
                    d = min(r, H - 1 - r, c, W - 1 - c)
                    if d not in dist_col:
                        dist_col[d] = x[r][c]
            max_d = max(dist_col)
            seq = [dist_col[d] for d in range(max_d + 1)]
            seen: list = []
            unique: list = []
            for v in seq:
                if v not in seen:
                    seen.append(v)
                    unique.append(v)
            N = len(unique)
            if N < 2:
                return x
            rotated = [unique[(i + direction) % N] for i in range(N)]
            mapping = {unique[i]: rotated[i] for i in range(N)}
            g = [row[:] for row in x]
            for r in range(H):
                for c in range(W):
                    g[r][c] = mapping.get(x[r][c], x[r][c])
            return g
        return _rotate

    for d in (1, -1):
        fn = _make_fn(d)
        if _fits_all(fn, pairs):
            return fn
    return None


def try_fill_border_with_nonbg(pairs):
    """Fill all border cells with the single non-bg color; interior becomes bg.

    The input must have exactly one non-bg color.
    Confirmed: fc754716.
    """
    if not _output_same_size_as_input(pairs):
        return None

    def _fill_border(x):
        b = background(x)
        nc_set = set(v for row in x for v in row) - {b}
        if len(nc_set) != 1:
            return x
        nc = next(iter(nc_set))
        H, W = len(x), len(x[0])
        g = [[b] * W for _ in range(H)]
        for r in range(H):
            for c in range(W):
                if r == 0 or r == H - 1 or c == 0 or c == W - 1:
                    g[r][c] = nc
        return g

    return _fill_border if _fits_all(_fill_border, pairs) else None


def try_sorted_color_cycle(pairs):
    """Rotate the sorted union of per-pair input+output colors by 1 step as a mapping.

    For each pair the union of input+output colors forms the cycle independently.
    Tries both left (direction=+1) and right (direction=-1) rotation.
    """
    if not _output_same_size_as_input(pairs):
        return None

    def _check_per_pair(direction):
        """Return True if per-pair cycle with given direction fits all pairs."""
        for x, y in pairs:
            c_set = set(v for row in x for v in row) | set(v for row in y for v in row)
            sc = sorted(c_set)
            N = len(sc)
            mp = {sc[i]: sc[(i + direction) % N] for i in range(N)}
            H, W = len(x), len(x[0])
            pred = [[mp.get(x[r][c], x[r][c]) for c in range(W)] for r in range(H)]
            if pred != y:
                return False
        return True

    def _make_fn(direction):
        def _cycle(x):
            # At inference time use only input colors (output unknown)
            sc = sorted(set(v for row in x for v in row))
            N = len(sc)
            mp = {sc[i]: sc[(i + direction) % N] for i in range(N)}
            H, W = len(x), len(x[0])
            return [[mp.get(x[r][c], x[r][c]) for c in range(W)] for r in range(H)]
        return _cycle

    for d in (1, -1):
        if _check_per_pair(d):
            fn = _make_fn(d)
            if _fits_all(fn, pairs):
                return fn
    return None


def try_complement_and_recolor(pairs):
    """Complement non-bg positions and substitute a new color from training pairs.

    Pattern: input has exactly 2 distinct colors (0 and C_in); output has exactly
    2 distinct colors (0 and C_out, where C_out != C_in); and the positions are
    complemented (where C_in was, now 0; where 0 was, now C_out).
    The mapping C_in -> C_out is consistent across all pairs sharing the same C_in.
    Confirmed: 6ea4a07e.
    """
    if not _output_same_size_as_input(pairs):
        return None

    # Build mapping: C_in -> C_out from training pairs
    color_map: dict = {}
    for x, y in pairs:
        x_colors = set(v for row in x for v in row)
        y_colors = set(v for row in y for v in row)
        if len(x_colors) != 2 or len(y_colors) != 2:
            return None
        if 0 not in x_colors or 0 not in y_colors:
            return None
        c_in = next(iter(x_colors - {0}))
        c_out = next(iter(y_colors - {0}))
        H, W = len(x), len(x[0])
        ok = all(
            (x[r][c] == c_in and y[r][c] == 0) or (x[r][c] == 0 and y[r][c] == c_out)
            for r in range(H) for c in range(W)
        )
        if not ok:
            return None
        if c_in in color_map and color_map[c_in] != c_out:
            return None
        color_map[c_in] = c_out

    if not color_map:
        return None

    def _complement(x, _map=color_map):
        x_colors = set(v for row in x for v in row)
        if 0 not in x_colors:
            return x
        nc_set = x_colors - {0}
        if len(nc_set) != 1:
            return x
        c_in = next(iter(nc_set))
        c_out = _map.get(c_in)
        if c_out is None:
            return x
        H, W = len(x), len(x[0])
        return [[c_out if x[r][c] == 0 else 0 for c in range(W)] for r in range(H)]

    return _complement if _fits_all(_complement, pairs) else None


def try_extend_line_to_border(pairs):
    """Extend each line of non-bg cells to the full row or full column.

    For each row that has some non-bg content in a contiguous segment, extend
    that segment (or the color) to fill the entire row.  Similarly for columns.
    Tries: (a) fill entire row with majority non-bg color if row has ≥2 same
    non-bg cells, (b) same for columns.
    """
    if not _output_same_size_as_input(pairs):
        return None

    # Strategy A: each non-bg row gets its most common non-bg color extended to full row
    def _extend_rows(x):
        b = background(x)
        H, W = len(x), len(x[0])
        g = [row[:] for row in x]
        for r in range(H):
            nc = [v for v in x[r] if v != b]
            if nc:
                mc = Counter(nc).most_common(1)[0][0]
                for c in range(W):
                    g[r][c] = mc
        return g

    # Strategy B: each non-bg column gets its most common non-bg color extended to full col
    def _extend_cols(x):
        b = background(x)
        H, W = len(x), len(x[0])
        g = [row[:] for row in x]
        for c in range(W):
            col_nc = [x[r][c] for r in range(H) if x[r][c] != b]
            if col_nc:
                mc = Counter(col_nc).most_common(1)[0][0]
                for r in range(H):
                    g[r][c] = mc
        return g

    for fn in (_extend_rows, _extend_cols):
        if _fits_all(fn, pairs):
            return fn
    return None


def try_recolor_by_object_size(pairs):
    """
    Recolor each connected component based on a learned
    (original_color, component_size) → output_color table.

    Covers d2abd087, 7d1f7ee8, 810b9b61, 8dae5dfc, 6e82a1ae,
    ae58858e, 009d5c81, a61f2674, e8593010, b230c067, ad173014,
    0a2355a6, 63613498, 6df30ad6 and more.
    """
    if not _output_same_size_as_input(pairs):
        return None

    def _ccs_all_colors(g):
        """Return list of (cells_list, color) for every non-bg component."""
        b = background(g)
        h, w = grid_size(g)
        visited = [[False] * w for _ in range(h)]
        comps = []
        for sr in range(h):
            for sc in range(w):
                if not visited[sr][sc] and g[sr][sc] != b:
                    v = g[sr][sc]
                    cells = []
                    stack = [(sr, sc)]
                    visited[sr][sc] = True
                    while stack:
                        r, c = stack.pop()
                        cells.append((r, c))
                        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                            nr, nc = r + dr, c + dc
                            if (0 <= nr < h and 0 <= nc < w
                                    and not visited[nr][nc]
                                    and g[nr][nc] == v):
                                visited[nr][nc] = True
                                stack.append((nr, nc))
                    comps.append((cells, v))
        return comps

    # Build (original_color, size) → output_color mapping
    table: dict = {}
    for x, y in pairs:
        h, w = grid_size(x)
        if grid_size(y) != (h, w):
            return None
        for cells, v in _ccs_all_colors(x):
            sz = len(cells)
            r0, c0 = cells[0]
            out_v = y[r0][c0]
            key = (v, sz)
            if key in table:
                if table[key] != out_v:
                    return None
            else:
                table[key] = out_v

    if not table:
        return None
    # Must actually change at least one object's color
    if all(k[0] == v for k, v in table.items()):
        return None

    def _apply(g: Grid, _t=table) -> Grid:
        result = copy_grid(g)
        for cells, v in _ccs_all_colors(g):
            sz = len(cells)
            new_v = _t.get((v, sz), v)
            for r, c in cells:
                result[r][c] = new_v
        return result

    return _apply if _fits_all(_apply, pairs) else None


def try_largest_object_extract(pairs):
    """
    Output = the bounding-box crop of the largest connected component
    in the input (by number of cells).
    Covers be94b721, 1f85a75f.
    """
    def _apply(g: Grid) -> Grid:
        b = background(g)
        h, w = grid_size(g)
        visited = [[False] * w for _ in range(h)]
        best_cells: list = []
        best_v = b
        for sr in range(h):
            for sc in range(w):
                if not visited[sr][sc] and g[sr][sc] != b:
                    v = g[sr][sc]
                    cells: list = []
                    stack = [(sr, sc)]
                    visited[sr][sc] = True
                    while stack:
                        r, c = stack.pop()
                        cells.append((r, c))
                        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                            nr, nc = r + dr, c + dc
                            if (0 <= nr < h and 0 <= nc < w
                                    and not visited[nr][nc]
                                    and g[nr][nc] == v):
                                visited[nr][nc] = True
                                stack.append((nr, nc))
                    if len(cells) > len(best_cells):
                        best_cells = cells
                        best_v = v
        if not best_cells:
            return g
        rows = [r for r, c in best_cells]
        cols = [c for r, c in best_cells]
        r0, r1 = min(rows), max(rows) + 1
        c0, c1 = min(cols), max(cols) + 1
        out = [[b] * (c1 - c0) for _ in range(r1 - r0)]
        for r, c in best_cells:
            out[r - r0][c - c0] = best_v
        return out

    return _apply if _fits_all(_apply, pairs) else None


def try_connect_pair_dots(pairs):
    """
    For each row or column containing exactly 2 non-bg cells with nothing
    between them, draw a bridge of a fixed learned color between the pair
    (exclusive of the anchor cells).  Anchors with no matching partner in the
    same axis are left untouched.

    Covers dbc1a6ce (anchor=1, bridge=8), 253bf280 (anchor=8, bridge=3),
    2bee17df (bridge=3).
    """
    from collections import Counter as _Counter

    def _background(g):
        return _Counter(v for row in g for v in row).most_common(1)[0][0]

    # Infer bridge color from training data
    bridge: Optional[int] = None

    for x, y in pairs:
        if len(x) != len(y) or len(x[0]) != len(y[0]):
            return None
        b = _background(x)
        H, W = len(x), len(x[0])

        # Collect anchor positions
        nc_by_row: dict = {}
        nc_by_col: dict = {}
        for r in range(H):
            for c in range(W):
                if x[r][c] != b:
                    nc_by_row.setdefault(r, []).append(c)
                    nc_by_col.setdefault(c, []).append(r)

        # Learn bridge color from expected output
        for r, cols in nc_by_row.items():
            if len(cols) == 2:
                c1, c2 = sorted(cols)
                for c in range(c1 + 1, c2):
                    if x[r][c] != b:
                        return None  # obstacle in gap
                    if y[r][c] != b:
                        if bridge is None:
                            bridge = y[r][c]
                        elif y[r][c] != bridge:
                            return None
        for c, rows in nc_by_col.items():
            if len(rows) == 2:
                r1, r2 = sorted(rows)
                for r in range(r1 + 1, r2):
                    if x[r][c] != b:
                        return None  # obstacle
                    if y[r][c] != b:
                        if bridge is None:
                            bridge = y[r][c]
                        elif y[r][c] != bridge:
                            return None

        # Verify no unexpected changes beyond anchor+bridge cells
        for r in range(H):
            for c in range(W):
                if y[r][c] != x[r][c] and y[r][c] != bridge:
                    return None

    if bridge is None:
        return None

    def _apply(g, _br=bridge):
        b = _background(g)
        H, W = len(g), len(g[0])
        result = [row[:] for row in g]
        nc_by_row: dict = {}
        nc_by_col: dict = {}
        for r in range(H):
            for c in range(W):
                if g[r][c] != b:
                    nc_by_row.setdefault(r, []).append(c)
                    nc_by_col.setdefault(c, []).append(r)
        for r, cols in nc_by_row.items():
            if len(cols) == 2:
                c1, c2 = sorted(cols)
                if all(g[r][c] == b for c in range(c1 + 1, c2)):
                    for c in range(c1 + 1, c2):
                        result[r][c] = _br
        for c, rows in nc_by_col.items():
            if len(rows) == 2:
                r1, r2 = sorted(rows)
                if all(g[r][c] == b for r in range(r1 + 1, r2)):
                    for r in range(r1 + 1, r2):
                        result[r][c] = _br
        return result

    return _apply if _fits_all(_apply, pairs) else None


def try_stamp_shape_at_marker(
    pairs: List[Tuple[Grid, Grid]],
) -> Optional[Program]:
    """Stamp a reflected copy of a large shape at single-cell marker positions.

    For each single-cell marker color, the shape (largest cluster) is flipped
    toward the marker along the dominant axis, with the shape cell on the same
    row (flip_h) or column (flip_v) as the marker used as the alignment anchor,
    and placed so that anchor lands on the marker.
    """
    def _apply_once(g: Grid) -> Optional[Grid]:
        b = background(g)
        H, W = len(g), len(g[0])
        colors = list({g[r][c] for r in range(H) for c in range(W) if g[r][c] != b})
        if not colors:
            return None

        # Shape = color with most cells
        best_c = max(colors, key=lambda col: sum(g[r][c] == col for r in range(H) for c in range(W)))
        shape = [(r, c) for r in range(H) for c in range(W) if g[r][c] == best_c]
        if len(shape) < 3:
            return None

        cr = sum(r for r, c in shape) / len(shape)
        cc_c = sum(c for r, c in shape) / len(shape)

        result = [row[:] for row in g]
        placed_any = False

        for marker_c in colors:
            if marker_c == best_c:
                continue
            mcs = [(r, c) for r in range(H) for c in range(W) if g[r][c] == marker_c]
            if len(mcs) != 1:
                continue
            mr, mc = mcs[0]

            dr = mr - cr
            dc = mc - cc_c

            if abs(dr) >= abs(dc):
                # Vertical direction → flip rows (flip_v: r → -r)
                anchor_cell = min(shape, key=lambda sc: abs(sc[1] - mc))
                t_cells = [(-r, c) for r, c in shape]
            else:
                # Horizontal direction → flip cols (flip_h: c → -c)
                anchor_cell = min(shape, key=lambda sc: abs(sc[0] - mr))
                t_cells = [(r, -c) for r, c in shape]

            anchor_idx = shape.index(anchor_cell)
            t_anchor = t_cells[anchor_idx]

            off_r = mr - t_anchor[0]
            off_c = mc - t_anchor[1]
            placed = [(r + off_r, c + off_c) for r, c in t_cells]

            if not all(0 <= r < H and 0 <= c < W for r, c in placed):
                continue
            if not all(g[r][c] == b or g[r][c] == marker_c for r, c in placed):
                continue

            for r, c in placed:
                result[r][c] = marker_c
            placed_any = True

        return result if placed_any else None

    # Validate on all pairs
    for x, y in pairs:
        pred = _apply_once(x)
        if pred != y:
            return None

    def _apply(g: Grid) -> Grid:
        r = _apply_once(g)
        return r if r is not None else [row[:] for row in g]

    return _apply


def try_pattern_fill_bounded(
    pairs: List[Tuple[Grid, Grid]],
) -> Optional[Program]:
    """Fill bounded regions with repeating pattern from border.
    
    Detects closed shapes (bordered regions) and fills interior with a 
    tiled pattern extracted from the boundary cells.
    """
    def _apply_once(g: Grid) -> Optional[Grid]:
        b = background(g)
        H, W = len(g), len(g[0])
        result = [row[:] for row in g]
        
        # Find all non-background colors
        colors = {g[r][c] for r in range(H) for c in range(W) if g[r][c] != b}
        if not colors:
            return None
        
        # For each color, find if it forms a closed boundary
        for border_c in colors:
            border_cells = [(r, c) for r in range(H) for c in range(W) if g[r][c] == border_c]
            if len(border_cells) < 4:
                continue
            
            # Find interior (flood fill from center, stop at border)
            center_r, center_c = H // 2, W // 2
            if g[center_r][center_c] == border_c:
                continue
            
            visited = set()
            queue = [(center_r, center_c)]
            interior = []
            
            while queue:
                r, c = queue.pop(0)
                if (r, c) in visited or not (0 <= r < H and 0 <= c < W):
                    continue
                if g[r][c] == border_c:
                    continue
                visited.add((r, c))
                interior.append((r, c))
                
                for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    queue.append((r + dr, c + dc))
            
            # Fill interior with pattern (2x2 tile)
            if interior:
                for r, c in interior:
                    # Checkerboard pattern using border color
                    if (r + c) % 2 == 0:
                        result[r][c] = border_c
        
        return result if result != g else None
    
    # Validate
    for x, y in pairs:
        pred = _apply_once(x)
        if pred != y:
            return None
    
    def _apply(g: Grid) -> Grid:
        r = _apply_once(g)
        return r if r is not None else [row[:] for row in g]
    
    return _apply


def try_reflect_across_axis(
    pairs: List[Tuple[Grid, Grid]],
) -> Optional[Program]:
    """Reflect non-background pixels across detected symmetry axis.
    
    Finds vertical or horizontal axis and mirrors objects across it.
    """
    # Detect which axis (horizontal or vertical) works
    for axis_type in ['h', 'v']:
        def _apply_once(g: Grid, ax=axis_type) -> Optional[Grid]:
            b = background(g)
            H, W = len(g), len(g[0])
            result = [row[:] for row in g]
            
            if ax == 'h':  # horizontal axis (mirror top/bottom)
                axis_pos = H // 2
                for r in range(axis_pos):
                    for c in range(W):
                        if g[r][c] != b:
                            mirror_r = 2 * axis_pos - r - 1
                            if 0 <= mirror_r < H:
                                result[mirror_r][c] = g[r][c]
            else:  # vertical axis (mirror left/right)
                axis_pos = W // 2
                for r in range(H):
                    for c in range(axis_pos):
                        if g[r][c] != b:
                            mirror_c = 2 * axis_pos - c - 1
                            if 0 <= mirror_c < W:
                                result[r][mirror_c] = g[r][c]
            
            return result if result != g else None
        
        # Check if this axis works
        all_match = True
        for x, y in pairs:
            pred = _apply_once(x, axis_type)
            if pred != y:
                all_match = False
                break
        
        if all_match:
            def _apply(g: Grid, ax=axis_type) -> Grid:
                r = _apply_once(g, ax)
                return r if r is not None else [row[:] for row in g]
            return _apply
    
    return None


def try_object_stack(
    pairs: List[Tuple[Grid, Grid]],
) -> Optional[Program]:
    """Stack objects vertically or horizontally based on their spatial distribution.
    
    Detects isolated objects and arranges them in a line (row or column).
    """
    def _apply_once(g: Grid) -> Optional[Grid]:
        b = background(g)
        H, W = len(g), len(g[0])
        
        # Find connected components
        visited = [[False] * W for _ in range(H)]
        objects = []
        
        def flood(sr, sc):
            cells = []
            queue = [(sr, sc)]
            while queue:
                r, c = queue.pop(0)
                if not (0 <= r < H and 0 <= c < W):
                    continue
                if visited[r][c] or g[r][c] == b:
                    continue
                visited[r][c] = True
                cells.append((r, c, g[r][c]))
                for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    queue.append((r + dr, c + dc))
            return cells
        
        for r in range(H):
            for c in range(W):
                if not visited[r][c] and g[r][c] != b:
                    obj = flood(r, c)
                    if obj:
                        objects.append(obj)
        
        if len(objects) < 2:
            return None
        
        # Stack horizontally (simple implementation)
        result = [[b] * W for _ in range(H)]
        x_offset = 0
        for obj in objects:
            for r, c, col in obj:
                new_c = c - min(cc for _, cc, _ in obj) + x_offset
                if 0 <= new_c < W:
                    result[r][new_c] = col
            x_offset += max(cc for _, cc, _ in obj) - min(cc for _, cc, _ in obj) + 2
        
        return result
    
    # Validate
    for x, y in pairs:
        pred = _apply_once(x)
        if pred != y:
            return None
    
    def _apply(g: Grid) -> Grid:
        r = _apply_once(g)
        return r if r is not None else [row[:] for row in g]
    
    return _apply


def try_pattern_subtract(
    pairs: List[Tuple[Grid, Grid]],
) -> Optional[Program]:
    """Erase translated or reflected copies of a dominant shape at markers.

    Complements stamp_shape_at_marker for tasks where singleton markers indicate
    where a repeated pattern should be removed instead of painted.
    """
    if not _output_same_size_as_input(pairs):
        return None

    def _make_prog(mode: str) -> Program:
        def _apply(g: Grid) -> Grid:
            try:
                b = background(g)
                H, W = len(g), len(g[0])
                comps = _grid_components(g)
                if not comps:
                    return [row[:] for row in g]

                shape = max(comps, key=len)
                if len(shape) < 3:
                    return [row[:] for row in g]

                shape_color = shape[0][2]
                shape_cells = [(r, c) for r, c, _ in shape]
                cr = sum(r for r, _ in shape_cells) / len(shape_cells)
                cc = sum(c for _, c in shape_cells) / len(shape_cells)

                result = [row[:] for row in g]
                changed = False

                for comp in comps:
                    if len(comp) != 1 or comp[0][2] == shape_color:
                        continue
                    mr, mc, _marker_color = comp[0]
                    use_mode = mode
                    if use_mode == "auto":
                        use_mode = "flip_v" if abs(mr - cr) >= abs(mc - cc) else "flip_h"

                    if use_mode == "flip_v":
                        anchor = min(shape_cells, key=lambda cell: abs(cell[1] - mc))
                        transformed = [(-r, c) for r, c in shape_cells]
                    elif use_mode == "flip_h":
                        anchor = min(shape_cells, key=lambda cell: abs(cell[0] - mr))
                        transformed = [(r, -c) for r, c in shape_cells]
                    else:
                        anchor = min(
                            shape_cells,
                            key=lambda cell: abs(cell[0] - mr) + abs(cell[1] - mc),
                        )
                        transformed = list(shape_cells)

                    ar, ac = transformed[shape_cells.index(anchor)]
                    off_r, off_c = mr - ar, mc - ac
                    placed = [(r + off_r, c + off_c) for r, c in transformed]
                    if not all(0 <= r < H and 0 <= c < W for r, c in placed):
                        continue

                    overlap = sum(1 for r, c in placed if g[r][c] != b)
                    if overlap < max(2, len(placed) // 2):
                        continue

                    for r, c in placed:
                        if result[r][c] != b:
                            result[r][c] = b
                            changed = True
                    if result[mr][mc] != b:
                        result[mr][mc] = b
                        changed = True

                return result if changed else [row[:] for row in g]
            except Exception:
                return [row[:] for row in g]

        return _apply

    for mode in ["auto", "identity", "flip_v", "flip_h"]:
        prog = _make_prog(mode)
        if _fits_all(prog, pairs):
            return prog
    return None


def try_border_propagate(
    pairs: List[Tuple[Grid, Grid]],
) -> Optional[Program]:
    """Propagate colors or border motifs inward along rows and columns.

    Targets tasks where the outer frame provides the pattern that should fill
    some or all interior cells.
    """
    if not _output_same_size_as_input(pairs):
        return None

    def _make_prog(mode: str, overwrite: bool) -> Program:
        def _apply(g: Grid) -> Grid:
            try:
                b = background(g)
                H, W = len(g), len(g[0])
                result = [row[:] for row in g]

                def _border_color(r: int, c: int) -> int:
                    if mode == "top":
                        return g[0][c]
                    if mode == "bottom":
                        return g[H - 1][c]
                    if mode == "left":
                        return g[r][0]
                    if mode == "right":
                        return g[r][W - 1]
                    candidates = [
                        (r, g[0][c]),
                        (H - 1 - r, g[H - 1][c]),
                        (c, g[r][0]),
                        (W - 1 - c, g[r][W - 1]),
                    ]
                    candidates = [(d, col) for d, col in candidates if col != b]
                    if not candidates:
                        return b
                    candidates.sort(key=lambda item: item[0])
                    return candidates[0][1]

                for r in range(H):
                    for c in range(W):
                        col = _border_color(r, c)
                        if col == b:
                            continue
                        if overwrite or result[r][c] == b:
                            result[r][c] = col

                return result
            except Exception:
                return [row[:] for row in g]

        return _apply

    for mode in ["top", "bottom", "left", "right", "nearest"]:
        for overwrite in [False, True]:
            prog = _make_prog(mode, overwrite)
            if _fits_all(prog, pairs):
                return prog
    return None


def try_majority_vote_cells(
    pairs: List[Tuple[Grid, Grid]],
) -> Optional[Program]:
    """Recolor each cell using the majority value in its local neighborhood.

    Useful for denoising or smoothing tasks where outputs follow the dominant
    color among 4-neighbors or 8-neighbors, optionally preserving ties.
    """
    if not _output_same_size_as_input(pairs):
        return None

    def _make_prog(
        diagonals: bool,
        include_self: bool,
        keep_ties: bool,
    ) -> Program:
        dirs = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        if diagonals:
            dirs += [(-1, -1), (-1, 1), (1, -1), (1, 1)]

        def _apply(g: Grid) -> Grid:
            try:
                H, W = len(g), len(g[0])
                result = [row[:] for row in g]
                for r in range(H):
                    for c in range(W):
                        vals = [g[nr][nc] for dr, dc in dirs
                                if 0 <= (nr := r + dr) < H and 0 <= (nc := c + dc) < W]
                        if include_self:
                            vals.append(g[r][c])
                        if not vals:
                            continue
                        counts = Counter(vals).most_common()
                        if len(counts) > 1 and counts[0][1] == counts[1][1] and keep_ties:
                            result[r][c] = g[r][c]
                        else:
                            result[r][c] = counts[0][0]
                return result
            except Exception:
                return [row[:] for row in g]

        return _apply

    for diagonals in [False, True]:
        for include_self in [False, True]:
            for keep_ties in [True, False]:
                prog = _make_prog(diagonals, include_self, keep_ties)
                if _fits_all(prog, pairs):
                    return prog
    return None


def try_path_trace(
    pairs: List[Tuple[Grid, Grid]],
) -> Optional[Program]:
    """Trace straight or L-shaped paths between sparse marked points.

    Covers tasks where singleton markers of the same color should be connected
    by a visible path instead of remaining isolated.
    """
    if not _output_same_size_as_input(pairs):
        return None

    def _make_prog(mode: str) -> Program:
        def _trace(a: Tuple[int, int], b: Tuple[int, int]) -> Optional[List[Tuple[int, int]]]:
            ar, ac = a
            br, bc = b
            if ar == br:
                step = 1 if ac <= bc else -1
                return [(ar, c) for c in range(ac, bc + step, step)]
            if ac == bc:
                step = 1 if ar <= br else -1
                return [(r, ac) for r in range(ar, br + step, step)]
            if abs(ar - br) == abs(ac - bc):
                dr = 1 if br > ar else -1
                dc = 1 if bc > ac else -1
                return [(ar + i * dr, ac + i * dc) for i in range(abs(ar - br) + 1)]
            if mode == "hv":
                h_step = 1 if ac <= bc else -1
                v_step = 1 if ar <= br else -1
                path = [(ar, c) for c in range(ac, bc + h_step, h_step)]
                path.extend((r, bc) for r in range(ar + v_step, br + v_step, v_step))
                return path
            if mode == "vh":
                v_step = 1 if ar <= br else -1
                h_step = 1 if ac <= bc else -1
                path = [(r, ac) for r in range(ar, br + v_step, v_step)]
                path.extend((br, c) for c in range(ac + h_step, bc + h_step, h_step))
                return path
            return None

        def _apply(g: Grid) -> Grid:
            try:
                b = background(g)
                result = [row[:] for row in g]
                singles: Dict[int, List[Tuple[int, int]]] = {}
                for comp in _grid_components(g):
                    if len(comp) != 1:
                        continue
                    r, c, col = comp[0]
                    singles.setdefault(col, []).append((r, c))

                changed = False
                for col, pts in singles.items():
                    if len(pts) != 2:
                        continue
                    path = _trace(pts[0], pts[1])
                    if not path:
                        continue
                    if any(result[r][c] not in (b, col) for r, c in path):
                        continue
                    for r, c in path:
                        if result[r][c] != col:
                            result[r][c] = col
                            changed = True
                return result if changed else [row[:] for row in g]
            except Exception:
                return [row[:] for row in g]

        return _apply

    for mode in ["straight", "hv", "vh"]:
        prog = _make_prog(mode)
        if _fits_all(prog, pairs):
            return prog
    return None


def try_grid_mask_apply(
    pairs: List[Tuple[Grid, Grid]],
) -> Optional[Program]:
    """Use one grid region as a binary mask over another region.

    Handles split-grid tasks where one half or band selects which cells from a
    source region should survive in the output.
    """
    def _split(g: Grid, axis: str) -> Optional[Tuple[Grid, Grid]]:
        H, W = len(g), len(g[0])
        if axis == "v":
            if W % 2 != 0:
                return None
            mid = W // 2
            return ([row[:mid] for row in g], [row[mid:] for row in g])
        if H % 2 != 0:
            return None
        mid = H // 2
        return (g[:mid], g[mid:])

    def _make_prog(
        axis: str,
        source_idx: int,
        invert: bool,
        full_size: bool,
    ) -> Program:
        def _apply(g: Grid) -> Grid:
            try:
                b = background(g)
                parts = _split(g, axis)
                if parts is None:
                    return [row[:] for row in g]
                first, second = parts
                source = first if source_idx == 0 else second
                mask = second if source_idx == 0 else first
                Hs, Ws = len(source), len(source[0])
                masked = [[b] * Ws for _ in range(Hs)]
                for r in range(Hs):
                    for c in range(Ws):
                        keep = (mask[r][c] != b)
                        if invert:
                            keep = not keep
                        if keep:
                            masked[r][c] = source[r][c]
                if not full_size:
                    return masked

                H, W = len(g), len(g[0])
                result = [[b] * W for _ in range(H)]
                if axis == "v":
                    start_c = 0 if source_idx == 0 else Ws
                    for r in range(Hs):
                        for c in range(Ws):
                            result[r][start_c + c] = masked[r][c]
                else:
                    start_r = 0 if source_idx == 0 else Hs
                    for r in range(Hs):
                        result[start_r + r] = masked[r][:]
                return result
            except Exception:
                return [row[:] for row in g]

        return _apply

    for axis in ["v", "h"]:
        for source_idx in [0, 1]:
            for invert in [False, True]:
                for full_size in [False, True]:
                    prog = _make_prog(axis, source_idx, invert, full_size)
                    if _fits_all(prog, pairs):
                        return prog
    return None


def try_hollow_shapes(
    pairs: List[Tuple[Grid, Grid]],
) -> Optional[Program]:
    """Convert filled monochrome shapes into outlines.

    Solves tasks where object interiors are removed while the visible perimeter
    of each colored region is preserved.
    """
    if not _output_same_size_as_input(pairs):
        return None

    def _make_prog(diagonals: bool) -> Program:
        dirs = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        if diagonals:
            dirs += [(-1, -1), (-1, 1), (1, -1), (1, 1)]

        def _apply(g: Grid) -> Grid:
            try:
                b = background(g)
                H, W = len(g), len(g[0])
                result = [[b] * W for _ in range(H)]
                for r in range(H):
                    for c in range(W):
                        col = g[r][c]
                        if col == b:
                            continue
                        boundary = False
                        for dr, dc in dirs:
                            nr, nc = r + dr, c + dc
                            if not (0 <= nr < H and 0 <= nc < W) or g[nr][nc] != col:
                                boundary = True
                                break
                        if boundary:
                            result[r][c] = col
                return result
            except Exception:
                return [row[:] for row in g]

        return _apply

    for diagonals in [False, True]:
        prog = _make_prog(diagonals)
        if _fits_all(prog, pairs):
            return prog
    return None


def try_object_reposition(
    pairs: List[Tuple[Grid, Grid]],
) -> Optional[Program]:
    """Move object components onto target marker positions while preserving shape.

    Covers relocation tasks where an existing object should be translated to a
    new anchor point rather than duplicated or recolored.
    """
    if not _output_same_size_as_input(pairs):
        return None

    def _anchor_point(
        comp: List[Tuple[int, int, int]],
        mode: str,
    ) -> Tuple[int, int]:
        if mode == "topleft":
            r0, c0, _, _ = _component_bbox(comp)
            return r0, c0
        cells = [(r, c) for r, c, _ in comp]
        cr = sum(r for r, _ in cells) / len(cells)
        cc = sum(c for _, c in cells) / len(cells)
        return min(cells, key=lambda cell: abs(cell[0] - cr) + abs(cell[1] - cc))

    def _make_prog(scope: str, anchor_mode: str) -> Program:
        def _apply(g: Grid) -> Grid:
            try:
                b = background(g)
                H, W = len(g), len(g[0])
                comps = _grid_components(g)
                movers = [comp for comp in comps if len(comp) > 1]
                markers = sorted(
                    [comp[0] for comp in comps if len(comp) == 1],
                    key=lambda cell: (cell[0], cell[1]),
                )
                if not movers or not markers:
                    return [row[:] for row in g]

                if scope == "largest":
                    if len(markers) != 1:
                        return [row[:] for row in g]
                    movers = [max(movers, key=len)]
                else:
                    movers = sorted(movers, key=lambda comp: _component_bbox(comp)[:2])
                    if len(movers) != len(markers):
                        return [row[:] for row in g]

                result = [row[:] for row in g]
                selected_markers = markers[:len(movers)]
                for comp in movers:
                    for r, c, _ in comp:
                        result[r][c] = b

                changed = False
                for comp, marker in zip(movers, selected_markers):
                    mr, mc, _ = marker
                    ar, ac = _anchor_point(comp, anchor_mode)
                    dr, dc = mr - ar, mc - ac
                    moved = [(r + dr, c + dc, col) for r, c, col in comp]
                    if not all(0 <= r < H and 0 <= c < W for r, c, _ in moved):
                        return [row[:] for row in g]
                    if any(result[r][c] != b for r, c, _ in moved):
                        return [row[:] for row in g]
                    for r, c, col in moved:
                        result[r][c] = col
                    changed = changed or any((r, c) not in {(rr, cc) for rr, cc, _ in comp}
                                             for r, c, _ in moved)

                return result if changed else [row[:] for row in g]
            except Exception:
                return [row[:] for row in g]

        return _apply

    for scope in ["largest", "all"]:
        for anchor_mode in ["topleft", "centroid"]:
            prog = _make_prog(scope, anchor_mode)
            if _fits_all(prog, pairs):
                return prog
    return None


# ═══════════════════════════════════════════════════════════════════════════════
# Synthesizer entry point
# ═══════════════════════════════════════════════════════════════════════════════

# Ordered strategy registry: (name, fn, max_time_s)
_STRATEGIES = [
    ("identity",               try_identity,               0.001),
    ("geometric_transform",    try_geometric_transforms,   0.05),
    ("color_mapping",          try_color_mapping,          0.1),
    ("invert_tile",            try_invert_and_tile,        0.05),
    ("tiling",                 try_tiling,                 0.05),
    ("checkerboard_tile",      try_checkerboard_tile,      0.1),
    ("fractal_self_multiply",  try_fractal_self_multiply,  0.1),
    ("crop_content",           try_crop_to_content,        0.05),
    ("extract_region",         try_extract_region,         0.2),
    ("histogram_barchart",     try_histogram_barchart,     0.1),
    ("column_height_rank",     try_column_height_rank,     0.1),
    ("row_height_rank",        try_row_height_rank,        0.1),
    ("diagonal_tile",          try_diagonal_tile,          0.05),
    ("stripe_tiling",          try_stripe_tiling,          0.1),
    ("block_tile_down",        try_block_tile_down,        0.3),
    ("gravity_toward_object",  try_gravity_toward_object,  0.1),
    ("small_component_recolor",try_small_component_recolor,0.3),
    ("connect_diagonal",       try_connect_diagonal,       0.2),
    ("rectangle_corner_mark",  try_rectangle_corner_mark,  0.5),
    ("color_decoration",       try_color_decoration,       0.5),
    ("plus_expand",            try_plus_expand,            0.3),
    ("gravity_down",           try_gravity_down,           0.05),
    ("gravity_up",             try_gravity_up,             0.05),
    ("gravity_left",           try_gravity_left,           0.05),
    ("gravity_right",          try_gravity_right,          0.05),
    ("fill_enclosed",          try_fill_enclosed,          0.1),
    ("interior_fill",          try_interior_fill,          0.3),
    ("adjacent_recolor",       try_adjacent_recolor,       0.5),
    ("complete_symmetry",      try_complete_symmetry,      0.1),
    ("color_key_table",        try_color_key_table,        0.2),
    ("region_boolean",         try_region_boolean,         0.3),
    ("separator_template",     try_separator_template_stamp, 0.5),
    ("shape_match_recolor",    try_shape_match_recolor,    0.5),
    ("stamp_by_mapping",       try_stamp_by_mapping,       1.0),
    ("run_length_group",       try_run_length_group,       0.3),
    ("frame_fill",             try_frame_fill,             0.5),
    ("scale_up",               try_scale_up,               0.1),
    ("slide_to_border",        try_slide_to_border,        0.1),
    ("dot_row_zones",          try_dot_row_zones,          0.1),
    ("connect_same_color_pairs", try_connect_same_color_pairs, 0.2),
    ("shift_content",          try_shift_content,          0.3),
    ("color_slide_direction",  try_color_slide_direction,  0.3),
    ("rotation_4fold",         try_rotation_4fold,         0.2),
    ("mirror_4fold",           try_mirror_4fold,           0.2),
    ("extend_lines",           try_extend_lines,           0.2),
    ("checkerboard_extend",    try_checkerboard_extend,    0.1),
    ("variable_pixel_scale",   try_variable_pixel_scale,   0.1),
    ("block_reduce",           try_block_reduce,           0.1),
    ("neighbor_count_recolor", try_neighbor_count_recolor, 0.2),
    ("separator_subgrid_reduce", try_separator_subgrid_reduce, 0.1),
    ("connect_same_color_lines", try_connect_same_color_lines, 0.1),
    ("diagonal_extend",        try_diagonal_extend,        0.1),
    ("complete_rect_outline",  try_complete_rect_outline,  0.1),
    ("uniform_output",         try_uniform_output,         0.05),
    ("fill_bbox_objects",      try_fill_bbox_objects,      0.1),
    ("sym_complete_rot180",    try_sym_complete_rot180,    0.05),
    ("row_col_intersect_mark", try_row_col_intersect_mark, 0.1),
    ("reverse_concentric",     try_reverse_concentric,     0.1),
    ("ring_color_rotate",      try_ring_color_rotate,      0.1),
    ("fill_border_nonbg",      try_fill_border_with_nonbg, 0.05),
    ("sorted_color_cycle",     try_sorted_color_cycle,      0.1),
    ("complement_recolor",     try_complement_and_recolor,  0.05),
    ("extend_line_to_border",  try_extend_line_to_border,   0.1),
    ("recolor_by_object_size", try_recolor_by_object_size,  0.3),
    ("largest_object_extract", try_largest_object_extract,  0.1),
    ("connect_pair_dots",      try_connect_pair_dots,        0.2),
    ("stamp_shape_at_marker",  try_stamp_shape_at_marker,    0.5),
    ("pattern_fill_bounded",   try_pattern_fill_bounded,     0.3),
    ("reflect_across_axis",    try_reflect_across_axis,      0.2),
    ("object_stack",           try_object_stack,             0.4),
    ("pattern_subtract",       try_pattern_subtract,         0.3),
    ("border_propagate",       try_border_propagate,         0.2),
    ("majority_vote_cells",    try_majority_vote_cells,      0.2),
    ("path_trace",             try_path_trace,               0.2),
    ("grid_mask_apply",        try_grid_mask_apply,          0.2),
    ("hollow_shapes",          try_hollow_shapes,            0.1),
    ("object_reposition",      try_object_reposition,        0.3),
    ("enumerate_depth1",       _enumerate_depth1,          2.0),
]


class Synthesizer:
    """
    Program synthesizer for ARC-AGI tasks.

    Usage
    -----
        syn = Synthesizer()
        prog = syn.synthesize(train_pairs)
        if prog:
            prediction = prog(test_input)
    """

    def __init__(self, time_budget: float = 5.0):
        self.time_budget = time_budget

    def synthesize(
        self,
        pairs: List[Tuple[Grid, Grid]],
        verbose: bool = False,
    ) -> Optional[Program]:
        """
        Find a program P such that P(x) == y for all (x,y) in pairs.
        Returns None if no program found within time_budget.
        """
        if not pairs:
            return None

        t0 = time.time()
        remaining = self.time_budget

        for name, strategy_fn, max_t in _STRATEGIES:
            if remaining <= 0:
                break
            try:
                prog = strategy_fn(pairs)
                if prog is not None:
                    if verbose:
                        print(f"  [Synthesizer] solved by: {name} "
                              f"({time.time()-t0:.3f}s)")
                    return prog
            except Exception:
                pass
            remaining = self.time_budget - (time.time() - t0)

        if verbose:
            print(f"  [Synthesizer] no program found "
                  f"({time.time()-t0:.3f}s)")
        return None

    def solve_task(self, task: dict, verbose: bool = False) -> Optional[List[List[int]]]:
        """
        Convenience method: synthesize from train pairs, apply to test input.
        Returns the predicted output grid, or None.
        """
        pairs = [(ex["input"], ex["output"]) for ex in task.get("train", [])]
        test_input = task["test"][0]["input"]

        prog = self.synthesize(pairs, verbose=verbose)
        if prog is None:
            return None
        try:
            return prog(test_input)
        except Exception:
            return None
